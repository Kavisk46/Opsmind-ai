import uuid
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import BaseModel

if TYPE_CHECKING:
    from models.user import User


class DocumentStatus(str, Enum):
    """Where a document is in the ingestion pipeline.

    EMBEDDING is a genuine addition, not just relabeling: unlike an
    earlier, rejected proposal to split READY into READY/INDEXED (which
    had no distinct work to justify two states), PROCESSING (extraction +
    chunking — fast, CPU-only) and EMBEDDING (running the actual ML
    model — measurably slower, verified directly in the RAG phase's real
    LLM/embedding runs) really are two different, separately-observable
    stages of work. Each transition below is committed as its own
    transaction (see IngestionService._set_status), so a client polling
    mid-run sees the real stage, not just "processing" the whole time.
    """

    UPLOADED = "uploaded"
    PROCESSING = "processing"
    EMBEDDING = "embedding"
    READY = "ready"
    FAILED = "failed"


class Document(BaseModel):
    """The `documents` table. Tracks an uploaded file's metadata and where
    its bytes live (`storage_key`) — the bytes themselves are never in the
    database, only a pointer to them (see core/storage.py).
    """

    __tablename__ = "documents"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # Nullable for now: the existing upload flow (services/document_service.py)
    # derives everything from the uploaded file itself and doesn't collect a
    # separate title yet — same "don't break the existing write path"
    # reasoning as User.username. Tightening this to NOT NULL is future
    # work for whichever phase actually adds a title to the upload request.
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    filename: Mapped[str] = mapped_column(String)
    content_type: Mapped[str] = mapped_column(String)
    size_bytes: Mapped[int] = mapped_column(Integer)
    # The key LocalStorage (or, later, an S3 backend) used to save the file
    # — not a filesystem path a client should ever see directly.
    storage_key: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default=DocumentStatus.UPLOADED.value)
    # Populated only when status=FAILED — a short, safe-to-display reason
    # (see IngestionService's exception handling for exactly what gets
    # written here and why it's truncated before being stored).
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)

    owner: Mapped["User"] = relationship(back_populates="documents")
