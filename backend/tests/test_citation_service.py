import uuid

from services.citation_service import Citation, CitationService
from services.reranking_service import RankedChunk


def _chunk(
    *,
    document_id: uuid.UUID | None = None,
    chunk_index: int = 0,
    filename: str | None = "notes.txt",
    page_number: int | None = None,
) -> RankedChunk:
    return RankedChunk(
        document_id=document_id or uuid.uuid4(),
        chunk_index=chunk_index,
        page_number=page_number,
        text="irrelevant to citations",
        filename=filename,
        vector_score=0.5,
        keyword_score=None,
        combined_score=0.5,
    )


def test_build_citations_maps_every_field():
    document_id = uuid.uuid4()
    chunk = _chunk(document_id=document_id, chunk_index=4, filename="report.pdf", page_number=2)
    service = CitationService()

    citations = service.build_citations([chunk])

    assert citations == [
        Citation(document_id=document_id, filename="report.pdf", chunk_index=4, page_number=2)
    ]


def test_build_citations_preserves_input_order():
    first = _chunk(chunk_index=0)
    second = _chunk(chunk_index=1)
    service = CitationService()

    citations = service.build_citations([first, second])

    assert [c.chunk_index for c in citations] == [0, 1]


def test_build_citations_handles_missing_filename():
    chunk = _chunk(filename=None)
    service = CitationService()

    citations = service.build_citations([chunk])

    assert citations[0].filename == "(unknown document)"


def test_build_citations_of_empty_list_returns_empty_list():
    service = CitationService()
    assert service.build_citations([]) == []
