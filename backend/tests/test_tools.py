import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

import pytest

from services.retrieval_service import RetrievedChunk
from services.tools import DocumentMetadataTool, RAGRetrievalTool


class FakeRetriever:
    """Stands in for RetrievalService — RAGRetrievalTool only ever calls
    .retrieve() on it, so that's the only method this fake implements.
    Returns a canned list[RetrievedChunk] set at construction time,
    completely bypassing embedding and vector search: this is what lets
    this file test RAGRetrievalTool's OWN logic (citation resolution,
    context formatting, empty-results handling) in total isolation from
    whether retrieval itself works — that's tests/test_retrieval_service.py
    and tests/test_vector_store.py's job, not this file's.
    """

    def __init__(self, chunks: list[RetrievedChunk] | None = None, raises: Exception | None = None):
        self._chunks = chunks if chunks is not None else []
        self._raises = raises
        self.last_call: dict | None = None

    def retrieve(self, *, query: str, owner_id: uuid.UUID, top_k: int) -> list[RetrievedChunk]:
        self.last_call = {"query": query, "owner_id": owner_id, "top_k": top_k}
        if self._raises is not None:
            raise self._raises
        return self._chunks


@dataclass
class _FakeDocument:
    id: uuid.UUID
    filename: str
    status: str = "ready"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class FakeDocumentRepository:
    """Only get_by_id() (used by RAGRetrievalTool) and list_by_owner()
    (used by DocumentMetadataTool) — the two methods either tool actually
    calls, matching the same narrow-Protocol-shaped fake pattern used
    throughout this suite (see services/ai_metrics_service.py's
    AIMetricsRecorder for the same reasoning written out in full).
    """

    def __init__(self, documents: list[_FakeDocument] | None = None):
        self._by_id = {doc.id: doc for doc in (documents or [])}

    async def get_by_id(self, document_id: uuid.UUID) -> _FakeDocument | None:
        return self._by_id.get(document_id)

    async def list_by_owner(self, owner_id: uuid.UUID) -> list[_FakeDocument]:
        return list(self._by_id.values())


def _chunk(document_id, chunk_index=0, page_number=None, text="chunk text", similarity_score=0.9):
    return RetrievedChunk(
        document_id=document_id, chunk_index=chunk_index, page_number=page_number,
        text=text, similarity_score=similarity_score,
    )


# --- RAGRetrievalTool: happy path ---


def test_rag_tool_returns_citations_resolved_from_the_document_repository():
    document_id = uuid.uuid4()
    documents = FakeDocumentRepository([_FakeDocument(id=document_id, filename="runbook.pdf")])
    retriever = FakeRetriever(chunks=[_chunk(document_id, text="the outage lasted 3 hours")])
    tool = RAGRetrievalTool(retrieval_service=retriever, document_repository=documents, top_k=5)

    result = asyncio.run(tool.run(query="what happened?", owner_id=uuid.uuid4()))

    assert result.success is True
    assert "the outage lasted 3 hours" in result.output_text
    assert len(result.citations) == 1
    assert result.citations[0].document_name == "runbook.pdf"


def test_rag_tool_populates_retrieval_metadata_for_ai_metrics():
    document_id = uuid.uuid4()
    documents = FakeDocumentRepository([_FakeDocument(id=document_id, filename="a.txt")])
    retriever = FakeRetriever(
        chunks=[_chunk(document_id, similarity_score=0.8), _chunk(document_id, chunk_index=1, similarity_score=0.6)]
    )
    tool = RAGRetrievalTool(retrieval_service=retriever, document_repository=documents, top_k=5)

    result = asyncio.run(tool.run(query="anything", owner_id=uuid.uuid4()))

    assert result.retrieval_metadata.chunk_count == 2
    assert result.retrieval_metadata.confidence_scores == [0.8, 0.6]


def test_rag_tool_passes_top_k_through_to_the_retriever():
    documents = FakeDocumentRepository()
    retriever = FakeRetriever(chunks=[])
    tool = RAGRetrievalTool(retrieval_service=retriever, document_repository=documents, top_k=7)

    asyncio.run(tool.run(query="anything", owner_id=uuid.uuid4()))

    assert retriever.last_call["top_k"] == 7


# --- RAGRetrievalTool: empty retrieval results ---


def test_rag_tool_handles_zero_retrieved_chunks_gracefully():
    documents = FakeDocumentRepository()
    retriever = FakeRetriever(chunks=[])
    tool = RAGRetrievalTool(retrieval_service=retriever, document_repository=documents, top_k=5)

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


def test_rag_tool_falls_back_to_placeholder_name_for_a_deleted_document():
    # The chunk's document_id points at a document that no longer exists
    # in the repository — a real scenario: a document deleted AFTER its
    # chunks were embedded but BEFORE the vector store's own chunks were
    # cleaned up (or a race between the two). Citation resolution must
    # degrade gracefully, not crash the whole chat request.
    orphaned_document_id = uuid.uuid4()
    documents = FakeDocumentRepository([])  # empty — nothing resolves
    retriever = FakeRetriever(chunks=[_chunk(orphaned_document_id, text="orphaned chunk")])
    tool = RAGRetrievalTool(retrieval_service=retriever, document_repository=documents, top_k=5)

    result = asyncio.run(tool.run(query="anything", owner_id=uuid.uuid4()))

    assert result.citations[0].document_name == "(deleted document)"
    assert "(deleted document)" in result.output_text


# --- RAGRetrievalTool: error handling ---


def test_rag_tool_propagates_retriever_errors():
    documents = FakeDocumentRepository()
    retriever = FakeRetriever(raises=RuntimeError("vector store unavailable"))
    tool = RAGRetrievalTool(retrieval_service=retriever, document_repository=documents, top_k=5)

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
    documents = FakeDocumentRepository(
        [_FakeDocument(id=uuid.uuid4(), filename="a.txt"), _FakeDocument(id=uuid.uuid4(), filename="b.txt")]
    )
    tool = DocumentMetadataTool(document_repository=documents)

    result = asyncio.run(tool.run(query="how many documents do I have?", owner_id=uuid.uuid4()))

    assert result.success is True
    assert "2 document(s)" in result.output_text
    assert "a.txt" in result.output_text
    assert "b.txt" in result.output_text
    # No chunk-level citations exist for a metadata answer — nothing was
    # semantically retrieved.
    assert result.citations == []
    assert result.retrieval_metadata is None


def test_document_metadata_tool_handles_zero_documents():
    tool = DocumentMetadataTool(document_repository=FakeDocumentRepository([]))

    result = asyncio.run(tool.run(query="how many documents do I have?", owner_id=uuid.uuid4()))

    assert result.success is True
    assert "not uploaded any documents yet" in result.output_text
