import uuid
from dataclasses import dataclass
from typing import Protocol


@dataclass
class FusedCandidate:
    """One deduplicated chunk after vector+keyword fusion (see
    RetrievalService.retrieve_hybrid) — `vector_score`/`keyword_score` are
    each `None` when that candidate came from only one of the two search
    legs, never a fabricated 0.0 (0.0 would falsely claim "searched and
    scored zero," when the truth is "never searched by this leg at all").
    `filename` is `None` here for the same reason `VectorMatch` has no
    filename at all: a vector-only match hasn't had it resolved yet at
    this point in the pipeline.
    """

    document_id: uuid.UUID
    chunk_index: int
    page_number: int | None
    text: str
    filename: str | None
    vector_score: float | None
    keyword_score: float | None


@dataclass
class RankedChunk:
    """A FusedCandidate plus the score reranking actually produced.
    Deliberately a separate, flat dataclass rather than FusedCandidate
    plus a bolted-on field — every caller downstream of reranking
    (ContextService, CitationService, the API response schema) only ever
    needs to think in terms of "a ranked chunk," never in terms of the
    two-sources-being-fused detail that produced it.
    """

    document_id: uuid.UUID
    chunk_index: int
    page_number: int | None
    text: str
    filename: str | None
    vector_score: float | None
    keyword_score: float | None
    combined_score: float


class Reranker(Protocol):
    """The shape any reranking strategy must provide — same Protocol-
    based DI pattern as core/storage.py's Storage and core/embeddings.py's
    EmbeddingModel. WeightedReranker (below) is today's implementation; a
    future cross-encoder, Cohere Rerank, or BGE reranker satisfies this
    same Protocol and can be swapped in via dependency injection (see
    api/dependencies.py) with no change to RetrievalService, which only
    ever depends on this Protocol, never on WeightedReranker by name.
    """

    def rerank(self, candidates: list[FusedCandidate]) -> list[RankedChunk]: ...


class WeightedReranker:
    """Today's Reranker: a plain weighted sum of vector similarity and
    keyword relevance, sorted descending. `vector_weight`/`keyword_weight`
    are explicit constructor arguments (see core/config.py's
    retrieval_vector_weight/retrieval_keyword_weight), not hardcoded here
    — the same "config, not a literal" discipline every other tunable
    value in this codebase already follows.
    """

    def __init__(self, *, vector_weight: float, keyword_weight: float):
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight

    def rerank(self, candidates: list[FusedCandidate]) -> list[RankedChunk]:
        ranked = [
            RankedChunk(
                document_id=candidate.document_id,
                chunk_index=candidate.chunk_index,
                page_number=candidate.page_number,
                text=candidate.text,
                filename=candidate.filename,
                vector_score=candidate.vector_score,
                keyword_score=candidate.keyword_score,
                # None (never searched by that leg) contributes 0 to the
                # sum — a missing signal, not a bad score, which is
                # exactly the distinction FusedCandidate's docstring
                # explains for why these are Optional in the first place.
                combined_score=(
                    self.vector_weight * (candidate.vector_score or 0.0)
                    + self.keyword_weight * (candidate.keyword_score or 0.0)
                ),
            )
            for candidate in candidates
        ]
        ranked.sort(key=lambda chunk: chunk.combined_score, reverse=True)
        return ranked
