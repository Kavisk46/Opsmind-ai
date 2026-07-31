import uuid

from services.reranking_service import FusedCandidate, RankedChunk, WeightedReranker


def _candidate(
    *,
    document_id: uuid.UUID | None = None,
    chunk_index: int = 0,
    text: str = "some text",
    filename: str | None = "notes.txt",
    vector_score: float | None = None,
    keyword_score: float | None = None,
    page_number: int | None = None,
) -> FusedCandidate:
    return FusedCandidate(
        document_id=document_id or uuid.uuid4(),
        chunk_index=chunk_index,
        page_number=page_number,
        text=text,
        filename=filename,
        vector_score=vector_score,
        keyword_score=keyword_score,
    )


def test_rerank_combines_vector_and_keyword_scores_by_weight():
    reranker = WeightedReranker(vector_weight=0.7, keyword_weight=0.3)
    candidate = _candidate(vector_score=0.8, keyword_score=0.5)

    ranked = reranker.rerank([candidate])

    assert isinstance(ranked[0], RankedChunk)
    assert ranked[0].combined_score == 0.7 * 0.8 + 0.3 * 0.5


def test_rerank_treats_a_missing_score_as_zero_not_none():
    # A candidate found by only ONE search leg should still be scoreable
    # — a missing score means "never searched by this leg," not "scored
    # badly," but it must still contribute 0 to the weighted sum so
    # ranking is well-defined for every candidate, mixed sources or not.
    reranker = WeightedReranker(vector_weight=0.7, keyword_weight=0.3)
    vector_only = _candidate(vector_score=0.9, keyword_score=None)
    keyword_only = _candidate(vector_score=None, keyword_score=0.9)

    ranked_vector_only = reranker.rerank([vector_only])
    ranked_keyword_only = reranker.rerank([keyword_only])

    assert ranked_vector_only[0].combined_score == 0.7 * 0.9
    assert ranked_keyword_only[0].combined_score == 0.3 * 0.9


def test_rerank_sorts_descending_by_combined_score():
    reranker = WeightedReranker(vector_weight=0.5, keyword_weight=0.5)
    low = _candidate(chunk_index=0, vector_score=0.1, keyword_score=0.1)
    high = _candidate(chunk_index=1, vector_score=0.9, keyword_score=0.9)
    mid = _candidate(chunk_index=2, vector_score=0.5, keyword_score=0.5)

    ranked = reranker.rerank([low, high, mid])

    assert [chunk.chunk_index for chunk in ranked] == [1, 2, 0]


def test_rerank_preserves_every_field_from_the_candidate():
    document_id = uuid.uuid4()
    candidate = _candidate(
        document_id=document_id,
        chunk_index=3,
        text="hello world",
        filename="report.pdf",
        page_number=2,
        vector_score=0.6,
        keyword_score=0.4,
    )
    reranker = WeightedReranker(vector_weight=0.5, keyword_weight=0.5)

    ranked = reranker.rerank([candidate])

    chunk = ranked[0]
    assert chunk.document_id == document_id
    assert chunk.chunk_index == 3
    assert chunk.text == "hello world"
    assert chunk.filename == "report.pdf"
    assert chunk.page_number == 2
    assert chunk.vector_score == 0.6
    assert chunk.keyword_score == 0.4


def test_rerank_of_empty_list_returns_empty_list():
    reranker = WeightedReranker(vector_weight=0.7, keyword_weight=0.3)
    assert reranker.rerank([]) == []
