import uuid

from services.context_service import ContextService
from services.reranking_service import RankedChunk


def _chunk(
    *,
    document_id: uuid.UUID,
    chunk_index: int,
    text: str,
    filename: str | None = "notes.txt",
    page_number: int | None = None,
    combined_score: float = 0.5,
) -> RankedChunk:
    return RankedChunk(
        document_id=document_id,
        chunk_index=chunk_index,
        page_number=page_number,
        text=text,
        filename=filename,
        vector_score=combined_score,
        keyword_score=None,
        combined_score=combined_score,
    )


def test_assemble_returns_a_placeholder_when_no_chunks_are_given():
    service = ContextService()

    result = service.assemble([], max_context_tokens=1000)

    assert "No relevant context" in result.text
    assert result.source_document_ids == []
    assert result.chunk_ids == []


def test_assemble_includes_filename_and_page_in_the_label():
    document_id = uuid.uuid4()
    chunk = _chunk(
        document_id=document_id, chunk_index=0, text="the pipeline stalled",
        filename="postmortem.pdf", page_number=3,
    )
    service = ContextService()

    result = service.assemble([chunk], max_context_tokens=1000)

    assert "[Source 1: postmortem.pdf, page 3]" in result.text
    assert "the pipeline stalled" in result.text


def test_assemble_records_source_documents_and_chunk_ids():
    document_id = uuid.uuid4()
    chunk = _chunk(document_id=document_id, chunk_index=2, text="hello")
    service = ContextService()

    result = service.assemble([chunk], max_context_tokens=1000)

    assert result.source_document_ids == [document_id]
    assert result.chunk_ids == [(document_id, 2)]


def test_assemble_preserves_chunk_index_order_within_a_document_even_if_reranked_out_of_order():
    document_id = uuid.uuid4()
    # Reranking put chunk_index=2 ahead of chunk_index=0 (higher score) —
    # ContextService must still emit them in chunk_index order within
    # this one document, not reranked order.
    later_chunk = _chunk(
        document_id=document_id, chunk_index=2, text="later paragraph", combined_score=0.9
    )
    earlier_chunk = _chunk(
        document_id=document_id, chunk_index=0, text="earlier paragraph", combined_score=0.4
    )
    service = ContextService()

    result = service.assemble([later_chunk, earlier_chunk], max_context_tokens=1000)

    earlier_position = result.text.index("earlier paragraph")
    later_position = result.text.index("later paragraph")
    assert earlier_position < later_position
    assert result.chunk_ids == [(document_id, 0), (document_id, 2)]


def test_assemble_preserves_document_order_from_the_ranked_list():
    document_a = uuid.uuid4()
    document_b = uuid.uuid4()
    # document_b's chunk appears FIRST in the ranked input (it scored
    # higher) — document_b's content should appear first in the context.
    chunk_b = _chunk(document_id=document_b, chunk_index=0, text="from document b")
    chunk_a = _chunk(document_id=document_a, chunk_index=0, text="from document a")
    service = ContextService()

    result = service.assemble([chunk_b, chunk_a], max_context_tokens=1000)

    assert result.text.index("from document b") < result.text.index("from document a")
    assert result.source_document_ids == [document_b, document_a]


def test_assemble_deduplicates_identical_paragraphs_across_chunks():
    document_id = uuid.uuid4()
    shared_paragraph = "This exact paragraph appears in both chunks."
    chunk_one = _chunk(
        document_id=document_id, chunk_index=0,
        text=f"{shared_paragraph}\n\nUnique to chunk one.",
    )
    chunk_two = _chunk(
        document_id=document_id, chunk_index=1,
        text=f"{shared_paragraph}\n\nUnique to chunk two.",
    )
    service = ContextService()

    result = service.assemble([chunk_one, chunk_two], max_context_tokens=1000)

    assert result.text.count(shared_paragraph) == 1
    assert "Unique to chunk one." in result.text
    assert "Unique to chunk two." in result.text


def test_assemble_respects_the_max_context_tokens_budget():
    document_id = uuid.uuid4()
    first_chunk = _chunk(document_id=document_id, chunk_index=0, text="one two three four five")
    second_chunk = _chunk(document_id=document_id, chunk_index=1, text="six seven eight nine ten")
    service = ContextService()

    # Budget only large enough for the first chunk (5 tokens) — the
    # second chunk (another 5 tokens) would exceed it, so it must be
    # dropped whole, never truncated mid-chunk.
    result = service.assemble([first_chunk, second_chunk], max_context_tokens=5)

    assert "one two three four five" in result.text
    assert "six seven eight nine ten" not in result.text
    assert result.chunk_ids == [(document_id, 0)]


def test_assemble_always_includes_at_least_the_first_chunk_even_over_budget():
    document_id = uuid.uuid4()
    chunk = _chunk(document_id=document_id, chunk_index=0, text="one two three four five")
    service = ContextService()

    result = service.assemble([chunk], max_context_tokens=1)

    assert "one two three four five" in result.text


def test_assemble_omits_filename_label_when_filename_is_missing():
    document_id = uuid.uuid4()
    chunk = _chunk(document_id=document_id, chunk_index=0, text="hello", filename=None)
    service = ContextService()

    result = service.assemble([chunk], max_context_tokens=1000)

    assert "[Source 1]" in result.text
    assert ":" not in result.text.split("]")[0]
