import uuid

from repositories.vector_repository import VectorMatch, VectorRepository


class FakeVectorStore:
    """Same minimal-fake philosophy as test_retrieval_service.py's own
    FakeVectorStore — VectorRepository only ever calls .query(), so
    that's the only method faked here.
    """

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


def _result(
    *,
    document_id: uuid.UUID | None = None,
    chunk_index: int = 0,
    page_number: int | None = None,
    text: str = "some text",
    similarity_score: float = 0.9,
) -> dict:
    return {
        "document_id": str(document_id or uuid.uuid4()),
        "chunk_index": chunk_index,
        "page_number": page_number,
        "text": text,
        "similarity_score": similarity_score,
    }


def test_search_maps_vector_store_results_to_vector_match():
    document_id = uuid.uuid4()
    vector_store = FakeVectorStore(
        results=[_result(document_id=document_id, text="hello", similarity_score=0.75)]
    )
    repository = VectorRepository(vector_store)

    matches = repository.search(query_embedding=[0.1, 0.2], owner_id=uuid.uuid4(), top_k=5)

    assert len(matches) == 1
    assert isinstance(matches[0], VectorMatch)
    assert matches[0].document_id == document_id
    assert matches[0].text == "hello"
    assert matches[0].score == 0.75


def test_search_passes_owner_id_as_a_string_and_top_k_through():
    owner_id = uuid.uuid4()
    vector_store = FakeVectorStore()
    repository = VectorRepository(vector_store)

    repository.search(query_embedding=[0.1], owner_id=owner_id, top_k=7)

    assert vector_store.last_call["owner_id"] == str(owner_id)
    assert vector_store.last_call["top_k"] == 7


def test_search_passes_the_query_embedding_through_unchanged():
    vector_store = FakeVectorStore()
    repository = VectorRepository(vector_store)

    repository.search(query_embedding=[0.5, 0.25, 0.1], owner_id=uuid.uuid4(), top_k=5)

    assert vector_store.last_call["query_embedding"] == [0.5, 0.25, 0.1]


def test_search_returns_empty_list_when_vector_store_finds_nothing():
    repository = VectorRepository(FakeVectorStore(results=[]))

    matches = repository.search(query_embedding=[0.1], owner_id=uuid.uuid4(), top_k=5)

    assert matches == []


def test_search_preserves_page_number_when_present():
    vector_store = FakeVectorStore(results=[_result(page_number=3)])
    repository = VectorRepository(vector_store)

    matches = repository.search(query_embedding=[0.1], owner_id=uuid.uuid4(), top_k=5)

    assert matches[0].page_number == 3
