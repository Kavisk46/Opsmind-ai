import uuid
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import delete, or_, select

from models.document import Document
from models.document_chunk import DocumentChunk
from repositories.base import BaseRepository

# A candidate pool wider than any single caller's `limit` — narrowed
# further (and SCORED) in Python afterward, per search_by_text's own
# docstring. Bounds worst-case query cost for a very common search term
# without needing real full-text-search ranking (tsvector/pg_trgm) to
# still return something reasonable. Not user-configurable: this is an
# internal implementation detail of how candidates get gathered, not a
# retrieval-quality knob like TOP_K/MAX_RETURNED_CHUNKS.
_CANDIDATE_POOL_SIZE = 200

# Each term contributes TWO clauses to the OR'd candidate filter (text
# ILIKE, filename ILIKE) — an unbounded query (a user pasting a whole
# paragraph, or a pathological request) would otherwise build an
# arbitrarily deep SQL expression tree. Verified directly: SQLite raises
# "Expression tree is too large (maximum depth 1000)" well before 1000
# terms (each contributing 2 clauses); this cap keeps candidate-gathering
# to a handful of the query's own words — plenty for a keyword-relevance
# signal — regardless of how long the original query string is.
_MAX_SEARCH_TERMS = 20


@dataclass
class KeywordMatch:
    """One chunk that matched a keyword search — mirrors VectorRepository's
    VectorMatch shape (document_id/chunk_index/text/score) plus `filename`,
    which keyword search gets for free from its join to `documents` (a
    vector-only match doesn't have this and must resolve it separately —
    see RetrievalService.retrieve_hybrid).
    """

    document_id: uuid.UUID
    chunk_index: int
    text: str
    filename: str
    keyword_score: float


class ChunkRepository(BaseRepository[DocumentChunk]):
    """Owns every query against the `document_chunks` table. Generic CRUD
    comes from BaseRepository; replace_for_document/list_by_document/
    delete_by_document/search_by_text are specific to chunks — every one
    of them scopes by document_id or owner_id, concepts BaseRepository
    knows nothing about.
    """

    model = DocumentChunk

    async def list_by_document(self, document_id: uuid.UUID) -> list[DocumentChunk]:
        result = await self.db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        )
        return list(result.scalars().all())

    async def delete_by_document(self, document_id: uuid.UUID) -> None:
        # One bulk DELETE, not "load every row then delete each" — the
        # same "minimize round trips" reasoning VectorStore.delete_by_
        # document already applies to Chroma, applied here to Postgres.
        with self._timed("delete_by_document"):
            await self.db.execute(
                delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
            )
            await self.db.flush()

    async def replace_for_document(
        self,
        *,
        document_id: uuid.UUID,
        owner_id: uuid.UUID,
        chunks: list[dict],
    ) -> list[DocumentChunk]:
        """Deletes this document's existing chunk rows, then bulk-inserts
        the new set — the whole reason ingestion is idempotent at the
        Postgres layer: reprocessing a document (a retry, a manual
        re-ingest) always leaves Postgres holding EXACTLY the latest run's
        chunks, never a mix of old and new rows, and never accumulating
        duplicates. This is a genuine improvement over VectorStore.
        add_chunks's upsert-by-id approach, which can't shrink a
        document's chunk count on its own (a reprocess producing FEWER
        chunks than before would leave the old tail-end vectors behind) —
        a delete-then-insert can't have that gap.

        `chunks` is a list of plain dicts (chunk_index/text/token_count/
        embedding_model) rather than DocumentChunk instances — callers
        (IngestionService) shouldn't need to import the ORM model just to
        call this.
        """
        await self.delete_by_document(document_id)

        with self._timed("replace_for_document"):
            instances = [
                DocumentChunk(document_id=document_id, owner_id=owner_id, **chunk)
                for chunk in chunks
            ]
            self.db.add_all(instances)
            await self.db.flush()
            return instances

    async def search_by_text(
        self,
        *,
        owner_id: uuid.UUID,
        terms: list[str],
        mode: Literal["and", "or"],
        limit: int,
    ) -> list[KeywordMatch]:
        """Lightweight keyword retrieval — plain PostgreSQL ILIKE, no
        Elasticsearch, no tsvector/full-text-search index. Matches EITHER
        a chunk's text OR its document's filename (a query for
        "Q3 budget" should surface a document literally named
        "q3-budget.pdf" even if that exact phrase never appears inside
        it) — this is why this method joins `documents` rather than
        querying `document_chunks` alone.

        Two-phase, not one dynamic SQL query: phase 1 asks Postgres for
        every row matching ANY term (a single OR'd ILIKE query, bounded by
        _CANDIDATE_POOL_SIZE) — this is the part that's genuinely
        "using PostgreSQL ILIKE." Phase 2 scores and filters candidates in
        Python: `mode="and"` keeps only rows where every term matched,
        `mode="or"` keeps any row with at least one match, and
        `keyword_score` (matched term count / total terms, 0..1) is what
        lets a caller COMBINE this with a vector similarity score on
        roughly the same scale (see RerankingService). Building the
        AND/OR logic and the ranking score as one large, dynamically
        constructed SQL expression would be real complexity for no
        benefit at this project's scale — "lightweight," per this phase's
        own requirement, not a hand-rolled search engine.
        """
        if not terms:
            return []

        terms = terms[:_MAX_SEARCH_TERMS]
        lowered_terms = [term.lower() for term in terms]
        candidate_filter = or_(
            *[
                clause
                for term in terms
                for clause in (
                    DocumentChunk.text.ilike(f"%{term}%"),
                    Document.filename.ilike(f"%{term}%"),
                )
            ]
        )

        result = await self.db.execute(
            select(DocumentChunk, Document.filename)
            .join(Document, DocumentChunk.document_id == Document.id)
            .where(DocumentChunk.owner_id == owner_id, candidate_filter)
            .limit(_CANDIDATE_POOL_SIZE)
        )

        scored: list[KeywordMatch] = []
        for chunk, filename in result.all():
            haystack = f"{chunk.text} {filename}".lower()
            matched_term_count = sum(1 for term in lowered_terms if term in haystack)
            if mode == "and" and matched_term_count < len(lowered_terms):
                continue
            if matched_term_count == 0:
                continue
            scored.append(
                KeywordMatch(
                    document_id=chunk.document_id,
                    chunk_index=chunk.chunk_index,
                    text=chunk.text,
                    filename=filename,
                    keyword_score=matched_term_count / len(lowered_terms),
                )
            )

        scored.sort(key=lambda match: match.keyword_score, reverse=True)
        return scored[:limit]
