import uuid
from dataclasses import dataclass

from services.reranking_service import RankedChunk


@dataclass
class Citation:
    """A citation ready to render in the UI — filename/page/chunk_index/
    document_id per retrieved chunk, per this phase's own requirement.
    Deliberately a separate shape from tools.py's existing `Citation`
    dataclass (chat's citation, resolved inline inside RAGRetrievalTool,
    coupled to that tool's document-lookup + prompt-formatting code) —
    this one is a plain, decoupled data transform over an already-
    resolved RankedChunk, reusable anywhere retrieval results need to be
    cited, independent of how (or whether) they get formatted into a
    prompt.
    """

    document_id: uuid.UUID
    filename: str
    chunk_index: int
    page_number: int | None


class CitationService:
    """Turns retrieved, reranked chunks into citations. No I/O, no
    database access — by the time a RankedChunk reaches here,
    RetrievalService has already resolved every chunk's filename (see its
    retrieve_hybrid docstring), so this is pure data transformation, unit-
    testable with no repository or fixture involved.
    """

    def build_citations(self, chunks: list[RankedChunk]) -> list[Citation]:
        return [
            Citation(
                document_id=chunk.document_id,
                filename=chunk.filename or "(unknown document)",
                chunk_index=chunk.chunk_index,
                page_number=chunk.page_number,
            )
            for chunk in chunks
        ]
