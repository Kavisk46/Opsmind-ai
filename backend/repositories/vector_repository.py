import uuid
from dataclasses import dataclass

from core.vector_store import VectorStore


@dataclass
class VectorMatch:
    """One chunk that matched a vector search — mirrors ChunkRepository's
    KeywordMatch shape (document_id/chunk_index/text/score) so both can be
    fused into one candidate list without a caller needing to special-case
    either source (see RetrievalService.retrieve_hybrid). `filename` isn't
    here (unlike KeywordMatch): ChromaDB's metadata never stored it —
    only document_id/owner_id/chunk_index/page_number (see
    core/vector_store.py) — so a vector-only match's filename is resolved
    separately, after fusion, only for chunks that actually survive
    reranking.
    """

    document_id: uuid.UUID
    chunk_index: int
    page_number: int | None
    text: str
    score: float


class VectorRepository:
    """Repository-pattern wrapper around VectorStore.query() — the
    "Retrieve top K vectors, filter by owner_id, return chunk/score/
    metadata" piece this phase's architecture calls for as its own class.
    VectorStore itself (core/vector_store.py) stays exactly as it was;
    this is a thin adapter over it, the same relationship RAGRetrievalTool
    already has to RetrievalService — not a replacement, and not where
    ChromaDB-specific details (collection name, cosine distance, the
    page-number sentinel) live. Those stay encapsulated in VectorStore,
    exactly where they already were.
    """

    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store

    def search(
        self, *, query_embedding: list[float], owner_id: uuid.UUID, top_k: int
    ) -> list[VectorMatch]:
        raw_results = self.vector_store.query(
            query_embedding=query_embedding, owner_id=str(owner_id), top_k=top_k
        )
        return [
            VectorMatch(
                document_id=uuid.UUID(result["document_id"]),
                chunk_index=result["chunk_index"],
                page_number=result["page_number"],
                text=result["text"],
                score=result["similarity_score"],
            )
            for result in raw_results
        ]
