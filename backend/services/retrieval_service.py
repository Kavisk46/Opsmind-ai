import time
import uuid
from dataclasses import dataclass

from core.embeddings import EmbeddingModel
from core.vector_store import VectorStore
from repositories.chunk_repository import ChunkRepository
from repositories.document_repository import DocumentRepository
from repositories.vector_repository import VectorRepository
from services.reranking_service import FusedCandidate, RankedChunk, Reranker


@dataclass
class RetrievedChunk:
    """One chunk retrieval found relevant, plus enough metadata for a
    citation. Deliberately a plain dataclass, not a Pydantic schema —
    this is an internal, service-to-service data shape, never serialized
    directly to an HTTP response (ChatService/the chat route translate it
    into schemas/chat.py's CitationResponse for that).
    """

    document_id: uuid.UUID
    chunk_index: int
    page_number: int | None
    text: str
    similarity_score: float
    filename: str | None = None


@dataclass
class HybridRetrievalTiming:
    """Per-stage timing for one retrieve_hybrid() call — this phase's own
    observability requirement (embedding time, vector search time,
    keyword search time, hybrid ranking time), returned rather than only
    logged so a caller (the /retrieval/search route) can include it in
    its own consolidated log line without this service needing to know
    anything about logging itself.
    """

    embedding_seconds: float
    vector_search_seconds: float
    keyword_search_seconds: float
    reranking_seconds: float


class RetrievalService:
    """Embeds a query and searches ChromaDB for the most semantically
    similar chunks. Deliberately knows nothing about prompts or LLMs —
    ChatService composes this with PromptBuilder and an LLM, but this
    class is independently testable and independently reusable (a future
    "search my documents" feature, with no chat involved at all, could
    use this exact class unmodified).

    retrieve() (chat's existing entry point) is UNCHANGED from before the
    Retrieval Engine phase — vector-only, no keyword search, no
    reranking. retrieve_hybrid() below is new, additive functionality for
    the standalone /retrieval/search endpoint; chat keeps using retrieve()
    exactly as it always has. See this phase's Change Summary for why
    that split is deliberate, not an oversight.

    chunk_repository/document_repository/reranker are OPTIONAL,
    defaulting to None — retrieve() needs none of them, and this keeps
    every existing test/call site that only ever calls retrieve()
    constructing this class exactly as it did before this phase (see
    tests/test_retrieval_service.py's existing tests, none of which
    supply these three). retrieve_hybrid() raises immediately if any are
    missing, rather than every caller of plain retrieve() being forced to
    supply hybrid-only dependencies it will never use.
    """

    def __init__(
        self,
        embedding_model: EmbeddingModel,
        vector_store: VectorStore,
        chunk_repository: ChunkRepository | None = None,
        document_repository: DocumentRepository | None = None,
        reranker: Reranker | None = None,
    ):
        self.embedding_model = embedding_model
        self.vector_store = vector_store
        self.vector_repository = VectorRepository(vector_store)
        self.chunk_repository = chunk_repository
        self.document_repository = document_repository
        self.reranker = reranker

    def retrieve(
        self, *, query: str, owner_id: uuid.UUID, top_k: int
    ) -> list[RetrievedChunk]:
        # embed() takes a list and returns a list (batching multiple
        # chunks at once during ingestion is what it's optimized for) —
        # a single query is just a batch of one, hence the [0].
        query_embedding = self.embedding_model.embed([query])[0]

        raw_results = self.vector_store.query(
            query_embedding=query_embedding,
            owner_id=str(owner_id),
            top_k=top_k,
        )

        return [
            RetrievedChunk(
                document_id=uuid.UUID(result["document_id"]),
                chunk_index=result["chunk_index"],
                page_number=result["page_number"],
                text=result["text"],
                similarity_score=result["similarity_score"],
                # .get(), not result["filename"] — VectorStore.query()
                # always includes this key now, but the fakes in
                # tests/test_retrieval_service.py predate it and don't.
                filename=result.get("filename"),
            )
            for result in raw_results
        ]

    async def retrieve_hybrid(
        self,
        *,
        query: str,
        owner_id: uuid.UUID,
        top_k: int,
        max_returned_chunks: int,
    ) -> tuple[list[RankedChunk], HybridRetrievalTiming]:
        """Vector search + keyword search, fused, deduplicated, reranked,
        and trimmed to `max_returned_chunks`. Returns chunks with every
        filename already resolved — callers (ContextService,
        CitationService, the API route) never need their own database
        access to display a citation.
        """
        if self.chunk_repository is None or self.document_repository is None or self.reranker is None:
            raise RuntimeError(
                "retrieve_hybrid() requires chunk_repository, document_repository, "
                "and reranker to be supplied at construction time."
            )
        # Reassigned to local names, not just referenced as self.attr for
        # the rest of this method — mypy's None-narrowing from the guard
        # above isn't reliably preserved across the `await` points below
        # when read back off `self`.
        chunk_repository = self.chunk_repository
        document_repository = self.document_repository
        reranker = self.reranker

        embedding_start = time.perf_counter()
        query_embedding = self.embedding_model.embed([query])[0]
        embedding_seconds = time.perf_counter() - embedding_start

        vector_search_start = time.perf_counter()
        vector_matches = self.vector_repository.search(
            query_embedding=query_embedding, owner_id=owner_id, top_k=top_k
        )
        vector_search_seconds = time.perf_counter() - vector_search_start

        keyword_search_start = time.perf_counter()
        terms = query.split()
        keyword_matches = (
            await chunk_repository.search_by_text(
                owner_id=owner_id, terms=terms, mode="or", limit=top_k
            )
            if terms
            else []
        )
        keyword_search_seconds = time.perf_counter() - keyword_search_start

        # Fuse + deduplicate by (document_id, chunk_index). Vector matches
        # are folded in FIRST so page_number (which only the vector leg
        # ever has — see FusedCandidate's docstring) is preserved when the
        # same chunk also matches on keywords; the keyword leg then only
        # fills in whatever the vector leg didn't already provide
        # (keyword_score, and filename if this chunk wasn't found by
        # vector search at all).
        fused: dict[tuple[uuid.UUID, int], FusedCandidate] = {}
        for vector_match in vector_matches:
            key = (vector_match.document_id, vector_match.chunk_index)
            fused[key] = FusedCandidate(
                document_id=vector_match.document_id,
                chunk_index=vector_match.chunk_index,
                page_number=vector_match.page_number,
                text=vector_match.text,
                filename=None,
                vector_score=vector_match.score,
                keyword_score=None,
            )
        for keyword_match in keyword_matches:
            key = (keyword_match.document_id, keyword_match.chunk_index)
            existing = fused.get(key)
            if existing is None:
                fused[key] = FusedCandidate(
                    document_id=keyword_match.document_id,
                    chunk_index=keyword_match.chunk_index,
                    page_number=None,
                    text=keyword_match.text,
                    filename=keyword_match.filename,
                    vector_score=None,
                    keyword_score=keyword_match.keyword_score,
                )
            else:
                existing.keyword_score = keyword_match.keyword_score
                if existing.filename is None:
                    existing.filename = keyword_match.filename

        reranking_start = time.perf_counter()
        ranked = reranker.rerank(list(fused.values()))
        reranking_seconds = time.perf_counter() - reranking_start

        ranked = ranked[:max_returned_chunks]

        # Resolve filename only for the final, already-trimmed list — the
        # same bounded N+1 pattern RAGRetrievalTool already uses (see
        # services/tools.py), applied here to whichever chunks in the
        # final list came from vector search alone (keyword matches
        # already carry filename via ChunkRepository's join).
        for chunk in ranked:
            if chunk.filename is None:
                document = await document_repository.get_by_id(chunk.document_id)
                chunk.filename = document.filename if document else "(deleted document)"

        timing = HybridRetrievalTiming(
            embedding_seconds=embedding_seconds,
            vector_search_seconds=vector_search_seconds,
            keyword_search_seconds=keyword_search_seconds,
            reranking_seconds=reranking_seconds,
        )
        return ranked, timing
