import asyncio
import uuid

import pytest

from services.llm.protocol import LLMResponse
from services.orchestrator import AIOrchestrator
from services.tool_registry import ToolRegistry, UnknownToolError
from services.tools import RetrievalMetadata, ToolResult


class _StubTool:
    """A minimal Tool implementation for testing the orchestrator/registry
    in complete isolation — no database, no vector store, no real LLM.
    """

    def __init__(self, name: str, result: ToolResult | None = None, raises: Exception | None = None):
        self.name = name
        self._result = result
        self._raises = raises
        self.called_with: tuple[str, uuid.UUID] | None = None

    async def run(self, *, query: str, owner_id: uuid.UUID) -> ToolResult:
        self.called_with = (query, owner_id)
        if self._raises is not None:
            raise self._raises
        return self._result


class _StubLLM:
    def __init__(self, *, raises: Exception | None = None):
        self.last_prompt: str | None = None
        self._raises = raises

    @property
    def is_loaded(self) -> bool:
        return True

    async def generate(self, prompt: str) -> LLMResponse:
        self.last_prompt = prompt
        if self._raises is not None:
            raise self._raises
        return LLMResponse(text="stub answer", prompt_tokens=10, completion_tokens=5)

    async def generate_stream(self, prompt: str):
        self.last_prompt = prompt
        yield "streamed "
        yield "stub answer"


class _StubPromptBuilder:
    def build(self, *, question, context_text, history=None) -> str:
        return f"Q={question}|CTX={context_text}"


class _SpyMetricsService:
    """A plain in-memory spy satisfying AIMetricsRecorder (see
    services/ai_metrics_service.py) — records exactly what it was called
    with, so a test can assert the orchestrator instrumented a request
    correctly without depending on AIMetricsService's real Prometheus/
    logging/aggregation internals. Same DI-for-testability reasoning as
    ConversationService's fake repositories in
    tests/test_conversation_service.py.
    """

    def __init__(self):
        self.llm_calls: list[dict] = []
        self.retrieval_calls: list[dict] = []
        self.generation_eval_calls: list[dict] = []

    def record_llm_request(self, **kwargs) -> None:
        self.llm_calls.append(kwargs)

    def record_retrieval(self, **kwargs) -> None:
        self.retrieval_calls.append(kwargs)

    def record_generation_eval(self, **kwargs) -> None:
        self.generation_eval_calls.append(kwargs)


def _make_orchestrator(registry, prompt_builder, llm, metrics_service=None):
    return AIOrchestrator(
        registry,
        prompt_builder,
        llm,
        metrics_service if metrics_service is not None else _SpyMetricsService(),
        provider_name="test-provider",
        model_name="test-model",
    )


# --- Tool selection (routing) ---


def test_route_sends_document_count_question_to_metadata_tool():
    orchestrator = _make_orchestrator(ToolRegistry(), _StubPromptBuilder(), _StubLLM())
    assert orchestrator._route("How many documents have I uploaded?") == "document_metadata"


def test_route_sends_list_documents_question_to_metadata_tool():
    orchestrator = _make_orchestrator(ToolRegistry(), _StubPromptBuilder(), _StubLLM())
    assert orchestrator._route("List my documents") == "document_metadata"


def test_route_sends_knowledge_question_to_rag_retrieval():
    orchestrator = _make_orchestrator(ToolRegistry(), _StubPromptBuilder(), _StubLLM())
    assert (
        orchestrator._route("What does the postmortem say about the outage?")
        == "rag_retrieval"
    )


def test_route_is_case_insensitive():
    orchestrator = _make_orchestrator(ToolRegistry(), _StubPromptBuilder(), _StubLLM())
    assert orchestrator._route("HOW MANY DOCUMENTS do I have?") == "document_metadata"


# --- Tool registry ---


def test_tool_registry_get_unknown_tool_raises():
    registry = ToolRegistry()
    with pytest.raises(UnknownToolError):
        registry.get("nonexistent")


def test_tool_registry_names_lists_every_registered_tool():
    registry = ToolRegistry()
    registry.register(_StubTool("a"))
    registry.register(_StubTool("b"))
    assert set(registry.names()) == {"a", "b"}


def test_tool_registry_get_returns_the_registered_instance():
    registry = ToolRegistry()
    tool = _StubTool("a")
    registry.register(tool)
    assert registry.get("a") is tool


# --- Orchestrator behavior ---


def test_orchestrator_executes_routed_tool_and_builds_prompt_from_its_output():
    registry = ToolRegistry()
    tool = _StubTool(
        "rag_retrieval",
        result=ToolResult(tool_name="rag_retrieval", success=True, output_text="some context"),
    )
    registry.register(tool)
    llm = _StubLLM()
    orchestrator = _make_orchestrator(registry, _StubPromptBuilder(), llm)

    result = asyncio.run(
        orchestrator.handle(question="What does the doc say?", owner_id=uuid.uuid4())
    )

    assert result.tool_used == "rag_retrieval"
    assert result.answer == "stub answer"
    assert tool.called_with[0] == "What does the doc say?"
    assert "some context" in llm.last_prompt


def test_orchestrator_falls_back_gracefully_when_tool_raises():
    registry = ToolRegistry()
    tool = _StubTool("rag_retrieval", raises=RuntimeError("boom"))
    registry.register(tool)
    llm = _StubLLM()
    orchestrator = _make_orchestrator(registry, _StubPromptBuilder(), llm)

    result = asyncio.run(orchestrator.handle(question="anything", owner_id=uuid.uuid4()))

    assert result.tool_used == "rag_retrieval"
    assert "couldn't retrieve" in result.answer.lower()
    # The LLM is deliberately never called on a tool failure — a fixed,
    # honest fallback message beats risking a fluent-but-wrong answer
    # built from nothing real.
    assert llm.last_prompt is None


# --- AI metrics instrumentation (this phase) ---


def test_handle_records_llm_request_metrics():
    registry = ToolRegistry()
    tool = _StubTool(
        "rag_retrieval",
        result=ToolResult(tool_name="rag_retrieval", success=True, output_text="some context"),
    )
    registry.register(tool)
    spy = _SpyMetricsService()
    orchestrator = _make_orchestrator(registry, _StubPromptBuilder(), _StubLLM(), spy)

    asyncio.run(
        orchestrator.handle(question="What does the doc say?", owner_id=uuid.uuid4())
    )

    assert len(spy.llm_calls) == 1
    call = spy.llm_calls[0]
    assert call["provider"] == "test-provider"
    assert call["model"] == "test-model"
    assert call["prompt_tokens"] == 10
    assert call["completion_tokens"] == 5
    assert call["success"] is True
    assert call["latency_seconds"] >= 0


def test_handle_records_llm_failure_metrics_and_still_raises():
    registry = ToolRegistry()
    tool = _StubTool(
        "rag_retrieval",
        result=ToolResult(tool_name="rag_retrieval", success=True, output_text="some context"),
    )
    registry.register(tool)
    spy = _SpyMetricsService()
    llm = _StubLLM(raises=RuntimeError("provider down"))
    orchestrator = _make_orchestrator(registry, _StubPromptBuilder(), llm, spy)

    with pytest.raises(RuntimeError):
        asyncio.run(orchestrator.handle(question="anything", owner_id=uuid.uuid4()))

    assert len(spy.llm_calls) == 1
    assert spy.llm_calls[0]["success"] is False
    assert spy.llm_calls[0]["error"] == "provider down"


def test_handle_records_retrieval_metrics_when_tool_provides_metadata():
    registry = ToolRegistry()
    tool = _StubTool(
        "rag_retrieval",
        result=ToolResult(
            tool_name="rag_retrieval",
            success=True,
            output_text="some context",
            retrieval_metadata=RetrievalMetadata(chunk_count=3, confidence_scores=[0.9, 0.8, 0.7]),
        ),
    )
    registry.register(tool)
    spy = _SpyMetricsService()
    orchestrator = _make_orchestrator(registry, _StubPromptBuilder(), _StubLLM(), spy)

    asyncio.run(orchestrator.handle(question="anything", owner_id=uuid.uuid4()))

    assert len(spy.retrieval_calls) == 1
    call = spy.retrieval_calls[0]
    assert call["chunk_count"] == 3
    assert call["confidence_scores"] == [0.9, 0.8, 0.7]


def test_handle_does_not_record_retrieval_metrics_without_metadata():
    registry = ToolRegistry()
    tool = _StubTool(
        "document_metadata",
        result=ToolResult(tool_name="document_metadata", success=True, output_text="2 docs"),
    )
    registry.register(tool)
    spy = _SpyMetricsService()
    orchestrator = _make_orchestrator(registry, _StubPromptBuilder(), _StubLLM(), spy)

    asyncio.run(orchestrator.handle(question="how many documents", owner_id=uuid.uuid4()))

    assert spy.retrieval_calls == []


def test_handle_records_generation_eval_with_citation_count():
    from services.tools import Citation

    registry = ToolRegistry()
    tool = _StubTool(
        "rag_retrieval",
        result=ToolResult(
            tool_name="rag_retrieval",
            success=True,
            output_text="some context",
            citations=[
                Citation(document_id=uuid.uuid4(), document_name="a.txt", chunk_index=0, page_number=None)
            ],
            retrieval_metadata=RetrievalMetadata(chunk_count=1, confidence_scores=[0.9]),
        ),
    )
    registry.register(tool)
    spy = _SpyMetricsService()
    orchestrator = _make_orchestrator(registry, _StubPromptBuilder(), _StubLLM(), spy)

    asyncio.run(orchestrator.handle(question="anything", owner_id=uuid.uuid4()))

    assert len(spy.generation_eval_calls) == 1
    call = spy.generation_eval_calls[0]
    assert call["citation_count"] == 1
    assert call["context_provided"] is True
    assert call["answer_length_chars"] == len("stub answer")


def test_handle_generation_eval_flags_zero_chunk_retrieval_as_no_context():
    registry = ToolRegistry()
    tool = _StubTool(
        "rag_retrieval",
        result=ToolResult(
            tool_name="rag_retrieval",
            success=True,
            output_text="No relevant context available.",
            retrieval_metadata=RetrievalMetadata(chunk_count=0, confidence_scores=[]),
        ),
    )
    registry.register(tool)
    spy = _SpyMetricsService()
    orchestrator = _make_orchestrator(registry, _StubPromptBuilder(), _StubLLM(), spy)

    asyncio.run(orchestrator.handle(question="anything", owner_id=uuid.uuid4()))

    assert spy.generation_eval_calls[0]["context_provided"] is False


# --- Streaming ---


def test_handle_stream_executes_tool_and_streams_llm_output():
    registry = ToolRegistry()
    tool = _StubTool(
        "rag_retrieval",
        result=ToolResult(tool_name="rag_retrieval", success=True, output_text="some context"),
    )
    registry.register(tool)
    llm = _StubLLM()
    orchestrator = _make_orchestrator(registry, _StubPromptBuilder(), llm)

    async def _run():
        tool_used, citations, token_stream = await orchestrator.handle_stream(
            question="What does the doc say?", owner_id=uuid.uuid4()
        )
        chunks = [chunk async for chunk in token_stream]
        return tool_used, citations, chunks

    tool_used, citations, chunks = asyncio.run(_run())

    assert tool_used == "rag_retrieval"
    assert chunks == ["streamed ", "stub answer"]
    assert "some context" in llm.last_prompt


def test_handle_stream_falls_back_gracefully_when_tool_raises():
    registry = ToolRegistry()
    tool = _StubTool("rag_retrieval", raises=RuntimeError("boom"))
    registry.register(tool)
    llm = _StubLLM()
    orchestrator = _make_orchestrator(registry, _StubPromptBuilder(), llm)

    async def _run():
        tool_used, citations, token_stream = await orchestrator.handle_stream(
            question="anything", owner_id=uuid.uuid4()
        )
        chunks = [chunk async for chunk in token_stream]
        return tool_used, citations, chunks

    tool_used, citations, chunks = asyncio.run(_run())

    assert tool_used == "rag_retrieval"
    assert citations == []
    assert "couldn't retrieve" in "".join(chunks).lower()
    # Same guarantee as the non-streaming fallback: the LLM is never
    # called at all when the tool fails.
    assert llm.last_prompt is None


def test_handle_stream_records_retrieval_metrics_eagerly():
    registry = ToolRegistry()
    tool = _StubTool(
        "rag_retrieval",
        result=ToolResult(
            tool_name="rag_retrieval",
            success=True,
            output_text="some context",
            retrieval_metadata=RetrievalMetadata(chunk_count=2, confidence_scores=[0.5, 0.6]),
        ),
    )
    registry.register(tool)
    spy = _SpyMetricsService()
    orchestrator = _make_orchestrator(registry, _StubPromptBuilder(), _StubLLM(), spy)

    async def _run():
        _tool_used, _citations, token_stream = await orchestrator.handle_stream(
            question="anything", owner_id=uuid.uuid4()
        )
        return [chunk async for chunk in token_stream]

    asyncio.run(_run())

    assert len(spy.retrieval_calls) == 1
    assert spy.retrieval_calls[0]["chunk_count"] == 2
