import uuid

import pytest

from services.retrieval_service import RetrievalService, RetrievedChunk


class FakeEmbeddingModel:
    """A minimal, purpose-built fake — distinct from conftest.py's
    FakeEmbeddingModel, which exists to make the `client` fixture's whole
    FastAPI app work end-to-end for ~110 integration tests. This one has
    exactly one job: prove RetrievalService calls .embed() correctly,
    so it only needs to remember what it was asked to embed and return
    something fixed in response. Defined here, not in conftest.py, for
    the same reason test_conversation_service.py's FakeConversationStore/
    FakeMessageStore live in that file rather than conftest.py — a fake
    built for one pure-unit-test file's needs doesn't belong in shared
    fixture infrastructure the whole suite loads.
    """

    def __init__(self):
        self.last_texts: list[str] | None = None

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.last_texts = texts
        return [[0.1, 0.2, 0.3] for _ in texts]


class FakeVectorStore:
    """Stands in for a real ChromaDB-backed VectorStore (core/vector_store.py).
    RetrievalService only ever calls .query() on its vector_store — never
    add_chunks()/delete_by_document()/count() — so that's the only method
    this fake implements; adding the other three now would be building for
    a need this test file doesn't have yet.

    Results are canned at construction time (so a test controls exactly
    what "the vector store found"), and every call's arguments are
    recorded on `last_call` (so a test can assert RetrievalService passed
    the right query_embedding/owner_id/top_k through) — no real ChromaDB
    index, no disk I/O, anywhere in this file.
    """

    def __init__(self, results: list[dict] | None = None, raises: Exception | None = None):
        self._results = results if results is not None else []
        self._raises = raises
        self.last_call: dict | None = None

    def query(self, *, query_embedding, owner_id, top_k):
        self.last_call = {
            "query_embedding": query_embedding,
            "owner_id": owner_id,
            "top_k": top_k,
        }
        if self._raises is not None:
            raise self._raises
        return self._results


def _chunk_result(
    *,
    document_id: uuid.UUID | None = None,
    chunk_index: int = 0,
    page_number: int | None = None,
    text: str = "some text",
    similarity_score: float = 0.9,
) -> dict:
    # Matches the exact dict shape VectorStore.query() really returns
    # (core/vector_store.py) — document_id as a str, everything else as
    # plain JSON-safe values — so this fake is a faithful stand-in, not
    # just something that happens to satisfy this one test file.
    return {
        "document_id": str(document_id or uuid.uuid4()),
        "chunk_index": chunk_index,
        "page_number": page_number,
        "text": text,
        "similarity_score": similarity_score,
    }


# --- happy path ---


def test_retrieve_returns_chunks_from_vector_store():
    # Arrange
    document_id = uuid.uuid4()
    vector_store = FakeVectorStore(
        results=[
            _chunk_result(
                document_id=document_id, text="the pipeline stalled", similarity_score=0.87
            )
        ]
    )
    service = RetrievalService(embedding_model=FakeEmbeddingModel(), vector_store=vector_store)

    # Act
    chunks = service.retrieve(query="what happened?", owner_id=uuid.uuid4(), top_k=5)

    # Assert
    assert len(chunks) == 1
    assert isinstance(chunks[0], RetrievedChunk)
    assert chunks[0].document_id == document_id
    assert chunks[0].text == "the pipeline stalled"
    assert chunks[0].similarity_score == 0.87


def test_retrieve_embeds_the_query_text_as_a_single_item_batch():
    # Arrange
    embedding_model = FakeEmbeddingModel()
    service = RetrievalService(embedding_model=embedding_model, vector_store=FakeVectorStore())

    # Act
    service.retrieve(query="what happened?", owner_id=uuid.uuid4(), top_k=5)

    # Assert
    assert embedding_model.last_texts == ["what happened?"]


def test_retrieve_passes_the_embedded_query_vector_to_vector_store():
    # Arrange
    vector_store = FakeVectorStore()
    service = RetrievalService(embedding_model=FakeEmbeddingModel(), vector_store=vector_store)

    # Act
    service.retrieve(query="anything", owner_id=uuid.uuid4(), top_k=5)

    # Assert
    assert vector_store.last_call["query_embedding"] == [0.1, 0.2, 0.3]


def test_retrieve_passes_owner_id_and_top_k_through_to_vector_store():
    # Arrange
    owner_id = uuid.uuid4()
    vector_store = FakeVectorStore()
    service = RetrievalService(embedding_model=FakeEmbeddingModel(), vector_store=vector_store)

    # Act
    service.retrieve(query="anything", owner_id=owner_id, top_k=3)

    # Assert
    assert vector_store.last_call["owner_id"] == str(owner_id)
    assert vector_store.last_call["top_k"] == 3


def test_retrieve_returns_multiple_chunks_in_the_order_the_vector_store_returned_them():
    # Arrange
    results = [
        _chunk_result(chunk_index=0, text="first", similarity_score=0.9),
        _chunk_result(chunk_index=1, text="second", similarity_score=0.8),
    ]
    service = RetrievalService(
        embedding_model=FakeEmbeddingModel(), vector_store=FakeVectorStore(results=results)
    )

    # Act
    chunks = service.retrieve(query="anything", owner_id=uuid.uuid4(), top_k=5)

    # Assert
    assert [c.text for c in chunks] == ["first", "second"]


def test_retrieve_returns_empty_list_when_vector_store_finds_nothing():
    # Arrange
    service = RetrievalService(
        embedding_model=FakeEmbeddingModel(), vector_store=FakeVectorStore(results=[])
    )

    # Act
    chunks = service.retrieve(query="anything", owner_id=uuid.uuid4(), top_k=5)

    # Assert
    assert chunks == []


# --- failure path ---


def test_retrieve_propagates_vector_store_errors():
    # Arrange
    vector_store = FakeVectorStore(raises=RuntimeError("chroma index corrupted"))
    service = RetrievalService(embedding_model=FakeEmbeddingModel(), vector_store=vector_store)

    # Act / Assert
    # RetrievalService has no try/except around vector_store.query() — a
    # deliberate absence, not an oversight (see Step 4's explanation
    # below). This test locks that behavior in: a future change that
    # accidentally swallows this error and returns [] instead would fail
    # this test, which is exactly the point.
    with pytest.raises(RuntimeError, match="chroma index corrupted"):
        service.retrieve(query="anything", owner_id=uuid.uuid4(), top_k=5)
