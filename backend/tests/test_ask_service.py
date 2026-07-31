import asyncio
import uuid

import pytest

from services.ask_service import AskService, EmptyQuestionError
from services.citation_service import CitationService
from services.context_service import ContextService
from services.llm.protocol import LLMResponse
from services.planner import Planner
from services.prompt_builder import PromptBuilder
from services.reranking_service import RankedChunk
from services.retrieval_service import HybridRetrievalTiming

_ZERO_TIMING = HybridRetrievalTiming(
    embedding_seconds=0, vector_search_seconds=0, keyword_search_seconds=0, reranking_seconds=0
)


class FakeRetrievalService:
    """Stands in for RetrievalService — AskService only ever calls
    .retrieve_hybrid() on it, so that's the only method this fake
    implements, same pattern as test_tools.py's FakeHybridRetriever.
    """

    def __init__(self, chunks: list[RankedChunk] | None = None, raises: Exception | None = None):
        self._chunks = chunks if chunks is not None else []
        self._raises = raises
        self.last_call: dict | None = None

    async def retrieve_hybrid(
        self, *, query: str, owner_id: uuid.UUID, top_k: int, max_returned_chunks: int
    ) -> tuple[list[RankedChunk], HybridRetrievalTiming]:
        self.last_call = {
            "query": query, "owner_id": owner_id, "top_k": top_k,
            "max_returned_chunks": max_returned_chunks,
        }
        if self._raises is not None:
            raise self._raises
        return self._chunks, _ZERO_TIMING


class FakeLLM:
    def __init__(self, text: str = "a fake answer", raises: Exception | None = None):
        self._text = text
        self._raises = raises
        self.last_prompt: str | None = None

    async def generate(self, prompt: str) -> LLMResponse:
        self.last_prompt = prompt
        if self._raises is not None:
            raise self._raises
        return LLMResponse(text=self._text, prompt_tokens=10, completion_tokens=5)


def _ranked_chunk(
    document_id=None, chunk_index=0, page_number=None, text="chunk text",
    filename="runbook.pdf", combined_score=0.9,
) -> RankedChunk:
    return RankedChunk(
        document_id=document_id or uuid.uuid4(), chunk_index=chunk_index, page_number=page_number,
        text=text, filename=filename, vector_score=combined_score, keyword_score=None,
        combined_score=combined_score,
    )


def _make_service(chunks=None, llm=None, retrieval=None):
    return AskService(
        Planner(),
        retrieval or FakeRetrievalService(chunks=chunks),
        ContextService(),
        PromptBuilder(chat_prompt_version="ask_v1"),
        CitationService(),
        llm or FakeLLM(),
        max_context_tokens=2000,
        max_returned_chunks=10,
    )


# --- validation ---


def test_ask_rejects_an_empty_question():
    service = _make_service()
    with pytest.raises(EmptyQuestionError):
        asyncio.run(service.ask(question="   ", owner_id=uuid.uuid4()))


# --- happy path ---


def test_ask_returns_the_llm_answer():
    service = _make_service(
        chunks=[_ranked_chunk(text="the pipeline stalled")],
        llm=FakeLLM(text="here is the answer"),
    )

    result = asyncio.run(service.ask(question="What happened?", owner_id=uuid.uuid4()))

    assert result.answer == "here is the answer"


def test_ask_passes_the_planners_rewritten_query_and_top_k_to_retrieval():
    retrieval = FakeRetrievalService(chunks=[])
    service = _make_service(retrieval=retrieval)

    asyncio.run(service.ask(question="What is SOC2?", owner_id=uuid.uuid4()))

    assert retrieval.last_call["query"] == "SOC2"
    assert retrieval.last_call["top_k"] == 5


def test_ask_uses_the_higher_top_k_for_an_incident_question():
    retrieval = FakeRetrievalService(chunks=[])
    service = _make_service(retrieval=retrieval)

    asyncio.run(
        service.ask(question="What happened during incident 52?", owner_id=uuid.uuid4())
    )

    assert retrieval.last_call["query"] == "incident 52"
    assert retrieval.last_call["top_k"] == 8


def test_ask_passes_owner_id_through_to_retrieval():
    owner_id = uuid.uuid4()
    retrieval = FakeRetrievalService(chunks=[])
    service = _make_service(retrieval=retrieval)

    asyncio.run(service.ask(question="What is SOC2?", owner_id=owner_id))

    assert retrieval.last_call["owner_id"] == owner_id


# --- citations ---


def test_ask_includes_citations_for_chunks_used_in_context():
    document_id = uuid.uuid4()
    chunk = _ranked_chunk(
        document_id=document_id, text="the pipeline stalled", filename="runbook.pdf",
        page_number=3,
    )
    service = _make_service(chunks=[chunk])

    result = asyncio.run(service.ask(question="What happened?", owner_id=uuid.uuid4()))

    assert len(result.citations) == 1
    assert result.citations[0].document_id == document_id
    assert result.citations[0].filename == "runbook.pdf"
    assert result.citations[0].page_number == 3


def test_ask_returns_no_citations_when_nothing_was_retrieved():
    service = _make_service(chunks=[])

    result = asyncio.run(service.ask(question="What is SOC2?", owner_id=uuid.uuid4()))

    assert result.citations == []


# --- confidence ---


def test_ask_computes_confidence_as_the_mean_combined_score_of_used_chunks():
    chunks = [
        _ranked_chunk(text="first chunk text", combined_score=0.8),
        _ranked_chunk(chunk_index=1, text="second chunk text", combined_score=0.6),
    ]
    service = _make_service(chunks=chunks)

    result = asyncio.run(service.ask(question="What happened?", owner_id=uuid.uuid4()))

    assert result.confidence == pytest.approx(0.7)


def test_ask_confidence_is_zero_when_nothing_retrieved():
    service = _make_service(chunks=[])

    result = asyncio.run(service.ask(question="What is SOC2?", owner_id=uuid.uuid4()))

    assert result.confidence == 0.0


# --- token usage / latency ---


def test_ask_populates_token_usage_from_the_llm_response():
    service = _make_service(chunks=[_ranked_chunk()], llm=FakeLLM())

    result = asyncio.run(service.ask(question="What happened?", owner_id=uuid.uuid4()))

    assert result.prompt_tokens == 10
    assert result.completion_tokens == 5


def test_ask_measures_a_non_negative_latency():
    service = _make_service(chunks=[_ranked_chunk()])

    result = asyncio.run(service.ask(question="What happened?", owner_id=uuid.uuid4()))

    assert result.latency_ms >= 0.0


# --- prompt assembly ---


def test_ask_sends_the_question_and_retrieved_text_to_the_llm():
    llm = FakeLLM()
    service = _make_service(chunks=[_ranked_chunk(text="the pipeline stalled")], llm=llm)

    asyncio.run(service.ask(question="What happened?", owner_id=uuid.uuid4()))

    assert "What happened?" in llm.last_prompt
    assert "the pipeline stalled" in llm.last_prompt
    assert "I don't have enough information" in llm.last_prompt


# --- error propagation ---


def test_ask_propagates_llm_errors():
    service = _make_service(
        chunks=[_ranked_chunk()], llm=FakeLLM(raises=RuntimeError("provider down"))
    )

    with pytest.raises(RuntimeError, match="provider down"):
        asyncio.run(service.ask(question="What happened?", owner_id=uuid.uuid4()))


def test_ask_propagates_retrieval_errors():
    retrieval = FakeRetrievalService(raises=RuntimeError("vector store unavailable"))
    service = _make_service(retrieval=retrieval)

    with pytest.raises(RuntimeError, match="vector store unavailable"):
        asyncio.run(service.ask(question="What happened?", owner_id=uuid.uuid4()))
