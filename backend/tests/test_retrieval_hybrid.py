import uuid
from types import SimpleNamespace

import pytest

from repositories.chunk_repository import KeywordMatch
from services.reranking_service import RankedChunk, WeightedReranker
from services.retrieval_service import RetrievalService


class FakeEmbeddingModel:
    def __init__(self):
        self.last_texts: list[str] | None = None

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.last_texts = texts
        return [[0.1, 0.2, 0.3] for _ in texts]


class FakeVectorStore:
    def __init__(self, results: list[dict] | None = None):
        self._results = results if results is not None else []
        self.last_call: dict | None = None

    def query(self, *, query_embedding, owner_id, top_k):
        self.last_call = {
            "query_embedding": query_embedding,
            "owner_id": owner_id,
            "top_k": top_k,
        }
        return self._results


class FakeChunkRepository:
    def __init__(self, results: list[KeywordMatch] | None = None):
        self._results = results if results is not None else []
        self.last_call: dict | None = None

    async def search_by_text(self, *, owner_id, terms, mode, limit):
        self.last_call = {"owner_id": owner_id, "terms": terms, "mode": mode, "limit": limit}
        return self._results


class FakeDocumentRepository:
    def __init__(self, filenames: dict[uuid.UUID, str] | None = None):
        self._filenames = filenames or {}
        self.get_by_id_calls: list[uuid.UUID] = []

    async def get_by_id(self, document_id):
        self.get_by_id_calls.append(document_id)
        filename = self._filenames.get(document_id)
        return SimpleNamespace(filename=filename) if filename else None


def _vector_result(
    *,
    document_id: uuid.UUID,
    chunk_index: int = 0,
    page_number: int | None = None,
    text: str = "vector text",
    similarity_score: float = 0.9,
) -> dict:
    return {
        "document_id": str(document_id),
        "chunk_index": chunk_index,
        "page_number": page_number,
        "text": text,
        "similarity_score": similarity_score,
    }


def _keyword_match(
    *, document_id: uuid.UUID, chunk_index: int = 0, text: str = "keyword text",
    filename: str = "notes.txt", keyword_score: float = 0.8,
) -> KeywordMatch:
    return KeywordMatch(
        document_id=document_id, chunk_index=chunk_index, text=text,
        filename=filename, keyword_score=keyword_score,
    )


def _make_service(
    *, vector_store=None, chunk_repository=None, document_repository=None, embedding_model=None,
):
    # No return type annotation, deliberately — matches this test suite's
    # existing convention (see test_retrieval_service.py's own fakes):
    # an annotated function's body IS type-checked by mypy, and the fakes
    # here (FakeVectorStore/FakeChunkRepository/FakeDocumentRepository)
    # are structural stand-ins, not real subtypes of VectorStore/
    # ChunkRepository/DocumentRepository — exactly the mismatch every
    # other fake in this suite already avoids by staying unannotated.
    return RetrievalService(
        embedding_model=embedding_model or FakeEmbeddingModel(),
        vector_store=vector_store or FakeVectorStore(),
        chunk_repository=chunk_repository if chunk_repository is not None else FakeChunkRepository(),
        document_repository=document_repository
        if document_repository is not None
        else FakeDocumentRepository(),
        reranker=WeightedReranker(vector_weight=0.7, keyword_weight=0.3),
    )


# --- construction guard ---


def test_retrieve_hybrid_raises_if_constructed_without_hybrid_dependencies():
    service = RetrievalService(embedding_model=FakeEmbeddingModel(), vector_store=FakeVectorStore())

    with pytest.raises(RuntimeError):
        import asyncio

        asyncio.run(
            service.retrieve_hybrid(
                query="anything", owner_id=uuid.uuid4(), top_k=5, max_returned_chunks=10
            )
        )


# --- fusion / deduplication ---


def test_retrieve_hybrid_deduplicates_a_chunk_found_by_both_legs():
    import asyncio

    document_id = uuid.uuid4()
    vector_store = FakeVectorStore(
        results=[_vector_result(document_id=document_id, chunk_index=0, text="shared chunk")]
    )
    chunk_repository = FakeChunkRepository(
        results=[_keyword_match(document_id=document_id, chunk_index=0, text="shared chunk")]
    )
    service = _make_service(vector_store=vector_store, chunk_repository=chunk_repository)

    chunks, _ = asyncio.run(
        service.retrieve_hybrid(
            query="shared chunk", owner_id=uuid.uuid4(), top_k=5, max_returned_chunks=10
        )
    )

    # ONE entry, not two — the whole point of fusing by (document_id, chunk_index).
    assert len(chunks) == 1
    assert chunks[0].vector_score is not None
    assert chunks[0].keyword_score is not None


def test_retrieve_hybrid_keeps_vector_only_and_keyword_only_chunks_separate():
    import asyncio

    vector_only_id = uuid.uuid4()
    keyword_only_id = uuid.uuid4()
    vector_store = FakeVectorStore(
        results=[_vector_result(document_id=vector_only_id, chunk_index=0)]
    )
    chunk_repository = FakeChunkRepository(
        results=[_keyword_match(document_id=keyword_only_id, chunk_index=0)]
    )
    document_repository = FakeDocumentRepository({vector_only_id: "vector-doc.txt"})
    service = _make_service(
        vector_store=vector_store,
        chunk_repository=chunk_repository,
        document_repository=document_repository,
    )

    chunks, _ = asyncio.run(
        service.retrieve_hybrid(
            query="anything", owner_id=uuid.uuid4(), top_k=5, max_returned_chunks=10
        )
    )

    assert {c.document_id for c in chunks} == {vector_only_id, keyword_only_id}
    vector_chunk = next(c for c in chunks if c.document_id == vector_only_id)
    keyword_chunk = next(c for c in chunks if c.document_id == keyword_only_id)
    assert vector_chunk.keyword_score is None
    assert keyword_chunk.vector_score is None


def test_retrieve_hybrid_preserves_page_number_from_vector_leg_when_both_match():
    import asyncio

    document_id = uuid.uuid4()
    vector_store = FakeVectorStore(
        results=[_vector_result(document_id=document_id, chunk_index=0, page_number=7)]
    )
    chunk_repository = FakeChunkRepository(
        results=[_keyword_match(document_id=document_id, chunk_index=0)]
    )
    service = _make_service(vector_store=vector_store, chunk_repository=chunk_repository)

    chunks, _ = asyncio.run(
        service.retrieve_hybrid(
            query="anything", owner_id=uuid.uuid4(), top_k=5, max_returned_chunks=10
        )
    )

    assert chunks[0].page_number == 7


# --- filename resolution ---


def test_retrieve_hybrid_resolves_filename_for_vector_only_chunks():
    import asyncio

    document_id = uuid.uuid4()
    vector_store = FakeVectorStore(results=[_vector_result(document_id=document_id)])
    document_repository = FakeDocumentRepository({document_id: "resolved.txt"})
    service = _make_service(vector_store=vector_store, document_repository=document_repository)

    chunks, _ = asyncio.run(
        service.retrieve_hybrid(
            query="anything", owner_id=uuid.uuid4(), top_k=5, max_returned_chunks=10
        )
    )

    assert chunks[0].filename == "resolved.txt"
    assert document_repository.get_by_id_calls == [document_id]


def test_retrieve_hybrid_does_not_look_up_filename_for_keyword_only_chunks():
    import asyncio

    document_id = uuid.uuid4()
    chunk_repository = FakeChunkRepository(
        results=[_keyword_match(document_id=document_id, filename="already-known.txt")]
    )
    document_repository = FakeDocumentRepository()
    service = _make_service(chunk_repository=chunk_repository, document_repository=document_repository)

    chunks, _ = asyncio.run(
        service.retrieve_hybrid(
            query="anything", owner_id=uuid.uuid4(), top_k=5, max_returned_chunks=10
        )
    )

    assert chunks[0].filename == "already-known.txt"
    assert document_repository.get_by_id_calls == []


def test_retrieve_hybrid_falls_back_to_deleted_document_label_when_lookup_fails():
    import asyncio

    document_id = uuid.uuid4()
    vector_store = FakeVectorStore(results=[_vector_result(document_id=document_id)])
    service = _make_service(vector_store=vector_store, document_repository=FakeDocumentRepository())

    chunks, _ = asyncio.run(
        service.retrieve_hybrid(
            query="anything", owner_id=uuid.uuid4(), top_k=5, max_returned_chunks=10
        )
    )

    assert chunks[0].filename == "(deleted document)"


# --- ranking / trimming ---


def test_retrieve_hybrid_returns_chunks_ranked_by_combined_score():
    import asyncio

    low_id, high_id = uuid.uuid4(), uuid.uuid4()
    vector_store = FakeVectorStore(
        results=[
            _vector_result(document_id=low_id, chunk_index=0, similarity_score=0.1),
            _vector_result(document_id=high_id, chunk_index=0, similarity_score=0.9),
        ]
    )
    service = _make_service(vector_store=vector_store)

    chunks, _ = asyncio.run(
        service.retrieve_hybrid(
            query="anything", owner_id=uuid.uuid4(), top_k=5, max_returned_chunks=10
        )
    )

    assert [c.document_id for c in chunks] == [high_id, low_id]
    assert all(isinstance(c, RankedChunk) for c in chunks)


def test_retrieve_hybrid_trims_to_max_returned_chunks():
    import asyncio

    results = [_vector_result(document_id=uuid.uuid4(), chunk_index=0) for _ in range(5)]
    vector_store = FakeVectorStore(results=results)
    service = _make_service(vector_store=vector_store)

    chunks, _ = asyncio.run(
        service.retrieve_hybrid(
            query="anything", owner_id=uuid.uuid4(), top_k=5, max_returned_chunks=2
        )
    )

    assert len(chunks) == 2


# --- owner isolation / no-results / empty query ---


def test_retrieve_hybrid_passes_owner_id_to_both_search_legs():
    import asyncio

    owner_id = uuid.uuid4()
    vector_store = FakeVectorStore()
    chunk_repository = FakeChunkRepository()
    service = _make_service(vector_store=vector_store, chunk_repository=chunk_repository)

    asyncio.run(
        service.retrieve_hybrid(query="anything", owner_id=owner_id, top_k=5, max_returned_chunks=10)
    )

    assert vector_store.last_call["owner_id"] == str(owner_id)
    assert chunk_repository.last_call["owner_id"] == owner_id


def test_retrieve_hybrid_returns_empty_list_when_neither_leg_finds_anything():
    import asyncio

    service = _make_service()

    chunks, _ = asyncio.run(
        service.retrieve_hybrid(query="anything", owner_id=uuid.uuid4(), top_k=5, max_returned_chunks=10)
    )

    assert chunks == []


def test_retrieve_hybrid_skips_the_keyword_leg_entirely_for_an_empty_query():
    import asyncio

    chunk_repository = FakeChunkRepository()
    service = _make_service(chunk_repository=chunk_repository)

    asyncio.run(
        service.retrieve_hybrid(query="", owner_id=uuid.uuid4(), top_k=5, max_returned_chunks=10)
    )

    assert chunk_repository.last_call is None


def test_retrieve_hybrid_handles_a_large_query_without_error():
    import asyncio

    large_query = "word " * 2000
    service = _make_service()

    chunks, timing = asyncio.run(
        service.retrieve_hybrid(
            query=large_query, owner_id=uuid.uuid4(), top_k=5, max_returned_chunks=10
        )
    )

    assert chunks == []
    assert timing.embedding_seconds >= 0


# --- timing ---


def test_retrieve_hybrid_returns_non_negative_timing_for_every_stage():
    import asyncio

    service = _make_service()

    _, timing = asyncio.run(
        service.retrieve_hybrid(query="anything", owner_id=uuid.uuid4(), top_k=5, max_returned_chunks=10)
    )

    assert timing.embedding_seconds >= 0
    assert timing.vector_search_seconds >= 0
    assert timing.keyword_search_seconds >= 0
    assert timing.reranking_seconds >= 0
