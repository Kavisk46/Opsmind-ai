import time
import uuid
from dataclasses import dataclass, field

from services.citation_service import Citation, CitationService
from services.context_service import ContextService
from services.llm.protocol import LLMProvider
from services.planner import Planner
from services.prompt_builder import PromptBuilder
from services.retrieval_service import RetrievalService


class EmptyQuestionError(Exception):
    """Raised for a blank/whitespace-only question — same reasoning as
    ChatService's identically-named exception (services/chat_service.py):
    never worth planning, retrieving, or calling the LLM for.
    """


@dataclass
class AskResult:
    """What AskService.ask() hands back — a plain, inert data holder
    (same role OrchestratorResult plays for the existing /chat path;
    see services/orchestrator.py), constructed directly rather than
    through a separate "response parser" step, since every field here is
    already structured data (an LLMResponse, a list[Citation], a
    measured duration) with nothing left to actually parse out of raw
    text.
    """

    answer: str
    citations: list[Citation] = field(default_factory=list)
    # Mean combined_score (services/reranking_service.py's vector+keyword
    # fusion score) of whichever chunks actually made it into the
    # assembled context — an honest signal already available from
    # retrieval, not a fabricated number. 0.0 when no chunks were used
    # (nothing retrieved, or everything got budget-trimmed away).
    confidence: float = 0.0
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    latency_ms: float = 0.0


class AskService:
    """A stateless, single-turn question-answering pipeline: Planner ->
    Retriever -> Context Builder -> Prompt Builder -> LLM -> Citations.
    Deliberately NOT conversation-aware — no Conversation/Message row is
    ever created or read here, unlike ChatService (services/
    chat_service.py), which this class does not replace, wrap, or
    modify. Two genuinely different capabilities coexist on purpose:
    multi-turn chat with persisted history (ChatService, POST /chat) and
    one-shot question answering with no persistence at all (this class,
    POST /chat/ask).

    Reuses the same retrieval/context/prompt/citation building blocks
    the existing chat path already uses (RetrievalService.
    retrieve_hybrid, ContextService, PromptBuilder, CitationService) —
    this class's only genuinely new work is Planner (deciding how to
    retrieve) and assembling the final AskResult (deciding what the
    caller gets back), never a second implementation of retrieval,
    context assembly, or prompting.
    """

    def __init__(
        self,
        planner: Planner,
        retrieval_service: RetrievalService,
        context_service: ContextService,
        prompt_builder: PromptBuilder,
        citation_service: CitationService,
        llm: LLMProvider,
        *,
        max_context_tokens: int,
        max_returned_chunks: int,
    ):
        self.planner = planner
        self.retrieval_service = retrieval_service
        self.context_service = context_service
        self.prompt_builder = prompt_builder
        self.citation_service = citation_service
        self.llm = llm
        self.max_context_tokens = max_context_tokens
        self.max_returned_chunks = max_returned_chunks

    async def ask(self, *, question: str, owner_id: uuid.UUID) -> AskResult:
        if not question.strip():
            raise EmptyQuestionError()

        start_time = time.perf_counter()

        plan = self.planner.plan(question)

        ranked_chunks, _timing = await self.retrieval_service.retrieve_hybrid(
            query=plan.rewritten_query,
            owner_id=owner_id,
            top_k=plan.top_k,
            max_returned_chunks=self.max_returned_chunks,
        )

        assembled_context = self.context_service.assemble(
            ranked_chunks, max_context_tokens=self.max_context_tokens
        )

        prompt = self.prompt_builder.build(
            question=question, context_text=assembled_context.text
        )
        llm_response = await self.llm.generate(prompt)

        # Only the chunks that actually survived context assembly (some
        # retrieved chunks may have been dropped by the token budget or
        # as duplicate paragraphs — see ContextService.assemble) are
        # cited or counted toward confidence; citing a chunk the model
        # never actually saw would misrepresent what grounded the answer.
        used_chunk_keys = set(assembled_context.chunk_ids)
        used_chunks = [
            chunk
            for chunk in ranked_chunks
            if (chunk.document_id, chunk.chunk_index) in used_chunk_keys
        ]
        citations = self.citation_service.build_citations(used_chunks)
        confidence = (
            round(sum(chunk.combined_score for chunk in used_chunks) / len(used_chunks), 4)
            if used_chunks
            else 0.0
        )

        return AskResult(
            answer=llm_response.text,
            citations=citations,
            confidence=confidence,
            prompt_tokens=llm_response.prompt_tokens,
            completion_tokens=llm_response.completion_tokens,
            latency_ms=(time.perf_counter() - start_time) * 1000,
        )
