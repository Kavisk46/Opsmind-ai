import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest

from services.citation_service import CitationService
from services.context_service import ContextService
from services.query_service import QueryService
from services.reranking_service import RankedChunk
from services.retrieval_service import HybridRetrievalTiming
from services.tools import DocumentMetadataTool, RAGRetrievalTool

_ZERO_TIMING = HybridRetrievalTiming(
    embedding_seconds=0, vector_search_seconds=0, keyword_search_seconds=0, reranking_seconds=0
)


class FakeHybridRetriever:
    """Stands in for RetrievalService — RAGRetrievalTool only ever calls
    .retrieve_hybrid() on it (the hybrid engine, wired in this phase),
    so that's the only method this fake implements. Returns a canned
    list[RankedChunk] set at construction time, completely bypassing
    embedding/vector/keyword search: this is what lets this file test
    RAGRetrievalTool's OWN logic (context assembly, citation building,
    empty-results handling) in total isolation from whether retrieval
    itself works — that's tests/test_retrieval_hybrid.py's job, not this
    file's. query_service/context_service/citation_service themselves
    are NOT faked here — they're pure, stateless, and already covered by
    their own dedicated test files, so using the real classes here tests
    RAGRetrievalTool's actual wiring, not a stand-in for it.
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


@dataclass
class _FakeDocument:
    id: uuid.UUID
    filename: str
    status: str = "ready"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class FakeDocumentRepository:
    """Only get_by_id() (used by RAGRetrievalTool) and list_by_workspace()
    (used by DocumentMetadataTool) — the two methods either tool actually
    calls, matching the same narrow-Protocol-shaped fake pattern used
    throughout this suite (see services/ai_metrics_service.py's
    AIMetricsRecorder for the same reasoning written out in full).
    """

    def __init__(self, documents: list[_FakeDocument] | None = None):
        self._by_id = {doc.id: doc for doc in (documents or [])}

    async def get_by_id(self, document_id: uuid.UUID) -> _FakeDocument | None:
        return self._by_id.get(document_id)

    async def list_by_workspace(self, workspace_id: uuid.UUID) -> list[_FakeDocument]:
        return list(self._by_id.values())


@dataclass
class _FakeUser:
    id: uuid.UUID
    default_workspace_id: uuid.UUID | None


class FakeUserRepository:
    """DocumentMetadataTool's only dependency besides DocumentRepository —
    resolves the caller's default_workspace_id (see services/tools.py's
    docstring on why the tool needs this bridge in Stage 1 of the
    multi-workspace rollout).
    """

    def __init__(self, users: list[_FakeUser] | None = None):
        self._by_id = {user.id: user for user in (users or [])}

    async def get_by_id(self, user_id: uuid.UUID) -> _FakeUser | None:
        return self._by_id.get(user_id)


def _ranked_chunk(
    document_id, chunk_index=0, page_number=None, text="chunk text",
    filename="runbook.pdf", combined_score=0.9,
) -> RankedChunk:
    return RankedChunk(
        document_id=document_id, chunk_index=chunk_index, page_number=page_number,
        text=text, filename=filename, vector_score=combined_score, keyword_score=None,
        combined_score=combined_score,
    )


def _make_rag_tool(retriever, *, top_k=5, max_returned_chunks=10, max_context_tokens=2000):
    # query_service/context_service/citation_service are the REAL,
    # stateless classes (see FakeHybridRetriever's own docstring on why)
    # — only the retriever itself is faked.
    return RAGRetrievalTool(
        retrieval_service=retriever,
        query_service=QueryService(),
        context_service=ContextService(),
        citation_service=CitationService(),
        top_k=top_k,
        max_returned_chunks=max_returned_chunks,
        max_context_tokens=max_context_tokens,
    )


# --- RAGRetrievalTool: happy path ---


def test_rag_tool_returns_citations_from_the_already_resolved_chunks():
    document_id = uuid.uuid4()
    retriever = FakeHybridRetriever(
        chunks=[_ranked_chunk(document_id, text="the outage lasted 3 hours", filename="runbook.pdf")]
    )
    tool = _make_rag_tool(retriever)

    result = asyncio.run(tool.run(query="what happened?", owner_id=uuid.uuid4()))

    assert result.success is True
    assert "the outage lasted 3 hours" in result.output_text
    assert len(result.citations) == 1
    assert result.citations[0].document_name == "runbook.pdf"


def test_rag_tool_populates_retrieval_metadata_for_ai_metrics():
    document_id = uuid.uuid4()
    retriever = FakeHybridRetriever(
        chunks=[
            _ranked_chunk(document_id, combined_score=0.8),
            _ranked_chunk(document_id, chunk_index=1, combined_score=0.6),
        ]
    )
    tool = _make_rag_tool(retriever)

    result = asyncio.run(tool.run(query="anything", owner_id=uuid.uuid4()))

    assert result.retrieval_metadata.chunk_count == 2
    assert result.retrieval_metadata.confidence_scores == [0.8, 0.6]


def test_rag_tool_passes_top_k_and_max_returned_chunks_through_to_the_retriever():
    retriever = FakeHybridRetriever(chunks=[])
    tool = _make_rag_tool(retriever, top_k=7, max_returned_chunks=3)

    asyncio.run(tool.run(query="anything", owner_id=uuid.uuid4()))

    assert retriever.last_call["top_k"] == 7
    assert retriever.last_call["max_returned_chunks"] == 3


def test_rag_tool_normalizes_the_query_before_retrieving():
    # QueryService.process() is the real class here, not a fake — this
    # proves the tool actually calls it, not just that QueryService works
    # in isolation (that's tests/test_query_service.py's job).
    retriever = FakeHybridRetriever(chunks=[])
    tool = _make_rag_tool(retriever)

    asyncio.run(tool.run(query="  what   happened?  ", owner_id=uuid.uuid4()))

    assert retriever.last_call["query"] == "what happened?"


# --- RAGRetrievalTool: empty retrieval results ---


def test_rag_tool_handles_zero_retrieved_chunks_gracefully():
    retriever = FakeHybridRetriever(chunks=[])
    tool = _make_rag_tool(retriever)

    result = asyncio.run(tool.run(query="anything", owner_id=uuid.uuid4()))

    # success=True is deliberate here — RETRIEVAL succeeded (it searched
    # and correctly found nothing); it's a different situation from
    # retrieval FAILING (see the error-handling test below). This is
    # exactly the "no context provided" signal AIOrchestrator's
    # generation-eval instrumentation (Phase T-AI-observability) relies
    # on: chunk_count == 0 with success == True.
    assert result.success is True
    assert result.citations == []
    assert result.retrieval_metadata.chunk_count == 0
    assert "No relevant context" in result.output_text


# --- RAGRetrievalTool: fallback behavior ---


def test_rag_tool_surfaces_a_deleted_document_placeholder_from_the_retriever():
    # Filename resolution (including the "(deleted document)" fallback)
    # now happens INSIDE RetrievalService.retrieve_hybrid() — see
    # tests/test_retrieval_hybrid.py's own test for THAT behavior. This
    # test only proves RAGRetrievalTool faithfully surfaces whatever
    # filename it was already given, without re-deriving it itself.
    orphaned_document_id = uuid.uuid4()
    retriever = FakeHybridRetriever(
        chunks=[_ranked_chunk(orphaned_document_id, text="orphaned chunk", filename="(deleted document)")]
    )
    tool = _make_rag_tool(retriever)

    result = asyncio.run(tool.run(query="anything", owner_id=uuid.uuid4()))

    assert result.citations[0].document_name == "(deleted document)"
    assert "(deleted document)" in result.output_text


# --- RAGRetrievalTool: error handling ---


def test_rag_tool_propagates_retriever_errors():
    retriever = FakeHybridRetriever(raises=RuntimeError("vector store unavailable"))
    tool = _make_rag_tool(retriever)

    # RAGRetrievalTool has no try/except of its own — AIOrchestrator is
    # what catches tool failures and produces the honest fallback answer
    # (see tests/test_orchestrator.py's
    # test_orchestrator_falls_back_gracefully_when_tool_raises). This
    # test locks in that the tool itself does NOT swallow the error
    # before the orchestrator ever gets a chance to.
    with pytest.raises(RuntimeError, match="vector store unavailable"):
        asyncio.run(tool.run(query="anything", owner_id=uuid.uuid4()))


# --- DocumentMetadataTool ---


def test_document_metadata_tool_summarizes_owned_documents():
    owner_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    documents = FakeDocumentRepository(
        [_FakeDocument(id=uuid.uuid4(), filename="a.txt"), _FakeDocument(id=uuid.uuid4(), filename="b.txt")]
    )
    users = FakeUserRepository([_FakeUser(id=owner_id, default_workspace_id=workspace_id)])
    tool = DocumentMetadataTool(document_repository=documents, user_repository=users)

    result = asyncio.run(tool.run(query="how many documents do I have?", owner_id=owner_id))

    assert result.success is True
    assert "2 document(s)" in result.output_text
    assert "a.txt" in result.output_text
    assert "b.txt" in result.output_text
    # No chunk-level citations exist for a metadata answer — nothing was
    # semantically retrieved.
    assert result.citations == []
    assert result.retrieval_metadata is None


def test_document_metadata_tool_handles_zero_documents():
    owner_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    users = FakeUserRepository([_FakeUser(id=owner_id, default_workspace_id=workspace_id)])
    tool = DocumentMetadataTool(document_repository=FakeDocumentRepository([]), user_repository=users)

    result = asyncio.run(tool.run(query="how many documents do I have?", owner_id=owner_id))

    assert result.success is True
    assert "not uploaded any documents yet" in result.output_text


def test_document_metadata_tool_handles_user_with_no_default_workspace():
    # A user with no default_workspace_id (theoretically possible before
    # ensure_personal_workspace runs, or if it's ever cleared) shouldn't
    # crash the tool — it should just report no documents, same as a real
    # empty workspace would.
    owner_id = uuid.uuid4()
    users = FakeUserRepository([_FakeUser(id=owner_id, default_workspace_id=None)])
    tool = DocumentMetadataTool(document_repository=FakeDocumentRepository([]), user_repository=users)

    result = asyncio.run(tool.run(query="how many documents do I have?", owner_id=owner_id))

    assert result.success is True
    assert "not uploaded any documents yet" in result.output_text
