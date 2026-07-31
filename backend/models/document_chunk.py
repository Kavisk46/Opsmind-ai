import uuid

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from models.base import BaseModel


class DocumentChunk(BaseModel):
    """The `document_chunks` table — a queryable Postgres mirror of the
    text/metadata half of what IngestionService also writes into
    ChromaDB. The EMBEDDING VECTOR itself never lives here (see
    core/vector_store.py); this table exists so a chunk's text and token
    count can be inspected, joined, or reported on without going through
    the vector store at all.

    (document_id, chunk_index) is unique so re-ingesting a document can't
    accumulate duplicate rows even under a bug in the calling code — the
    same guarantee ChunkRepository.replace_for_document already provides
    at the application level, enforced here too as a DB-level backstop
    (same "app-level pre-check + DB constraint as the real guarantee"
    pattern as Document's uq_documents_owner_id_filename).
    """

    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint(
            "document_id", "chunk_index", name="uq_document_chunks_document_id_chunk_index"
        ),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(String)
    # A cheap word-count estimate (see IngestionService), not a real
    # tokenizer count — consistent with this codebase's existing
    # character-based (not token-based) chunking; introducing a real
    # tokenizer dependency is out of scope for this table.
    token_count: Mapped[int] = mapped_column(Integer)
    # Recorded per-chunk (not just globally) so a future re-embedding
    # with a different model leaves old rows honestly labeled with
    # whichever model actually produced their vector, rather than
    # silently implying every row was embedded the same way.
    embedding_model: Mapped[str] = mapped_column(String)
