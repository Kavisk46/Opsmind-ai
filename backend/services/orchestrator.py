import time
import uuid
from dataclasses import dataclass, field
from typing import AsyncIterator

from core.logging import logger
from services.ai_metrics_service import AIMetricsRecorder
from services.llm.protocol import LLMProvider
from services.prompt_builder import PromptBuilder
from services.tool_registry import ToolRegistry
from services.tools import Citation


async def _single_chunk_stream(text: str) -> AsyncIterator[str]:
    """Wraps a plain string as a one-item async stream — used for the
    graceful-fallback message in handle_stream() below, so a tool
    failure still produces something `async for` can consume, matching
    the shape every real provider's generate_stream() returns.
    """
    yield text

# Keyword-based routing, not an LLM call — deliberate, for three reasons:
# (1) deterministic and fully unit-testable with no model involved;
# (2) zero added latency/cost versus asking the LLM to classify first;
# (3) this project's model (a small, local instruct model) has no
# reliable structured function-calling support to lean on anyway. A real
# production system with a stronger model, or genuinely ambiguous
# routing needs, might use an LLM-based classifier instead — that's a
# reasonable upgrade, not a correction, once "keyword doesn't cover this
# case" actually happens.
_METADATA_KEYWORDS = (
    "how many document",
    "how many file",
    "list my document",
    "list documents",
    "which documents",
    "what documents",
    "document count",
    "when did i upload",
    "documents have i uploaded",
)


@dataclass
class OrchestratorResult:
    answer: str
    citations: list[Citation] = field(default_factory=list)
    tool_used: str = ""


class AIOrchestrator:
    """Routes a question to exactly ONE tool, executes it, builds a
    prompt from its output, and calls the LLM — a fixed three-step
    pipeline (route -> execute -> generate), never a loop where the model
    decides its own next action. That fixed shape is what makes this an
    orchestrator, not an autonomous agent.
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        prompt_builder: PromptBuilder,
        llm: LLMProvider,
        metrics_service: AIMetricsRecorder,
        *,
        provider_name: str,
        model_name: str,
    ):
        self.tool_registry = tool_registry
        self.prompt_builder = prompt_builder
        self.llm = llm
        self.metrics_service = metrics_service
        # Passed in as plain strings rather than read off `llm` itself —
        # LLMProvider (services/llm/protocol.py) deliberately exposes no
        # "what provider/model is this" property, only generate()/
        # generate_stream()/is_loaded. The caller building this
        # orchestrator (api/dependencies.py) already knows both from
        # Settings at the exact moment it constructs `llm` via the
        # factory (services/llm/factory.py) — passing them alongside
        # avoids adding a new required property to every LLMProvider
        # implementation just for logging/metrics labels.
        self.provider_name = provider_name
        self.model_name = model_name

    async def handle(
        self,
        *,
        question: str,
        owner_id: uuid.UUID,
        history: list[tuple[str, str]] | None = None,
        conversation_id: uuid.UUID | None = None,
    ) -> OrchestratorResult:
        tool_name = self._route(question)
        tool = self.tool_registry.get(tool_name)

        start_time = time.perf_counter()
        try:
            result = await tool.run(query=question, owner_id=owner_id)
        except Exception as error:
            duration_seconds = time.perf_counter() - start_time
            logger.error(
                "tool=%s success=False duration=%.3fs error=%s",
                tool_name,
                duration_seconds,
                error,
            )
            # A graceful, deterministic fallback — no LLM call at all.
            # Calling the LLM anyway with "the tool failed" as context
            # risks it inventing a plausible-sounding answer despite
            # having nothing real to work from; a fixed, honest message
            # is safer than a fluent one that might be wrong.
            return OrchestratorResult(
                answer="I couldn't retrieve the information needed to answer that right now.",
                tool_used=tool_name,
            )

        duration_seconds = time.perf_counter() - start_time
        logger.info(
            "tool=%s success=%s duration=%.3fs", tool_name, result.success, duration_seconds
        )
        if result.retrieval_metadata is not None:
            # Only tools that actually retrieve (RAGRetrievalTool) ever
            # set this — reusing `duration_seconds` (already measured for
            # the log line above) as the retrieval latency, rather than
            # timing it a second time, is exactly what keeps this
            # instrumentation from cluttering the method with extra
            # timers.
            self.metrics_service.record_retrieval(
                tool_name=tool_name,
                chunk_count=result.retrieval_metadata.chunk_count,
                latency_seconds=duration_seconds,
                confidence_scores=result.retrieval_metadata.confidence_scores,
                conversation_id=conversation_id,
            )

        prompt = self.prompt_builder.build(
            question=question, context_text=result.output_text, history=history
        )
        # generate() is async now (Step 2's ask) — genuinely awaited I/O
        # for network-based providers (OpenAI/Anthropic), and offloaded
        # CPU-bound work via asyncio.to_thread for the local provider
        # (see LocalTransformersProvider) — either way, this orchestrator
        # doesn't need to know or care which.
        llm_start_time = time.perf_counter()
        try:
            llm_response = await self.llm.generate(prompt)
        except Exception as error:
            llm_duration_seconds = time.perf_counter() - llm_start_time
            self.metrics_service.record_llm_request(
                provider=self.provider_name,
                model=self.model_name,
                prompt_tokens=None,
                completion_tokens=None,
                latency_seconds=llm_duration_seconds,
                success=False,
                conversation_id=conversation_id,
                error=str(error),
            )
            # Re-raised unchanged — this instrumentation only observes
            # the call, it never changes how LLM failures propagate (the
            # route above still turns this into a 500, exactly as before
            # this phase).
            raise

        llm_duration_seconds = time.perf_counter() - llm_start_time
        self.metrics_service.record_llm_request(
            provider=self.provider_name,
            model=self.model_name,
            prompt_tokens=llm_response.prompt_tokens,
            completion_tokens=llm_response.completion_tokens,
            latency_seconds=llm_duration_seconds,
            success=True,
            conversation_id=conversation_id,
        )

        # "Was there real grounding context" — zero retrieved chunks
        # counts as no context even though rag_retrieval still returns
        # success=True (it successfully ran a search that just found
        # nothing); document_metadata has no chunks at all, but its
        # success reflects a real, non-hallucinated DB answer. See
        # services/ai_metrics_service.py's docstring on why this (not a
        # full hallucination detector) is this project's realistic scope.
        context_provided = (
            result.retrieval_metadata.chunk_count > 0
            if result.retrieval_metadata is not None
            else result.success
        )
        self.metrics_service.record_generation_eval(
            tool_used=tool_name,
            citation_count=len(result.citations),
            context_provided=context_provided,
            answer_length_chars=len(llm_response.text),
            conversation_id=conversation_id,
        )

        return OrchestratorResult(
            answer=llm_response.text, citations=result.citations, tool_used=tool_name
        )

    async def handle_stream(
        self,
        *,
        question: str,
        owner_id: uuid.UUID,
        history: list[tuple[str, str]] | None = None,
        conversation_id: uuid.UUID | None = None,
    ) -> tuple[str, list[Citation], AsyncIterator[str]]:
        """Same routing + tool execution as handle() — run eagerly,
        to completion, before any streaming begins, because tool
        execution (a bounded ChromaDB/Postgres query) is fast and has a
        single definite result; only LLM GENERATION actually benefits
        from streaming. Returns (tool_used, citations, token_stream)
        rather than one OrchestratorResult, since the answer text doesn't
        exist as a single value yet — the caller consumes token_stream to
        get it incrementally.

        Retrieval evaluation is recorded here exactly like handle() does,
        since retrieval still runs eagerly before streaming starts. LLM-
        level metrics (latency/tokens/cost) and generation eval are
        deliberately NOT recorded for this path: real per-token latency
        and the final answer text only exist once the caller has fully
        consumed token_stream, which happens in api/routes/chat.py, one
        layer above this method and after it has already returned — the
        same reason that route, not this method or ChatService, persists
        the assistant's message for a streamed reply. Wiring metrics
        through that generator is a real, deliberate scope cut for this
        phase, not an oversight — see this phase's code review.
        """
        tool_name = self._route(question)
        tool = self.tool_registry.get(tool_name)

        start_time = time.perf_counter()
        try:
            result = await tool.run(query=question, owner_id=owner_id)
        except Exception as error:
            duration_seconds = time.perf_counter() - start_time
            logger.error(
                "tool=%s success=False duration=%.3fs error=%s",
                tool_name,
                duration_seconds,
                error,
            )
            fallback = "I couldn't retrieve the information needed to answer that right now."
            return tool_name, [], _single_chunk_stream(fallback)

        duration_seconds = time.perf_counter() - start_time
        logger.info(
            "tool=%s success=%s duration=%.3fs", tool_name, result.success, duration_seconds
        )
        if result.retrieval_metadata is not None:
            self.metrics_service.record_retrieval(
                tool_name=tool_name,
                chunk_count=result.retrieval_metadata.chunk_count,
                latency_seconds=duration_seconds,
                confidence_scores=result.retrieval_metadata.confidence_scores,
                conversation_id=conversation_id,
            )

        prompt = self.prompt_builder.build(
            question=question, context_text=result.output_text, history=history
        )
        # Calling generate_stream() does no work yet — it returns an
        # async generator immediately; the actual LLM call only starts
        # once the caller begins iterating it with `async for`.
        token_stream = self.llm.generate_stream(prompt)
        return tool_name, result.citations, token_stream

    def _route(self, question: str) -> str:
        lowered = question.lower()
        if any(keyword in lowered for keyword in _METADATA_KEYWORDS):
            return "document_metadata"
        return "rag_retrieval"
