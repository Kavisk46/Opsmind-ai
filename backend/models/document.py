import uuid
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import BaseModel

if TYPE_CHECKING:
    from models.user import User
    from models.workspace import Workspace


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
    __table_args__ = (
        # DB-level duplicate-filename guard, scoped per WORKSPACE now, not
        # per owner (see alembic/versions/d6fede6f8731 for why this has to
        # be a constraint, not just an application-level check) — since a
        # workspace's documents are visible to every member (see
        # models/workspace.py's docstring), "no duplicate filenames" now
        # means "not within the same shared workspace," matching how the
        # rest of this phase's visibility model works. Two DIFFERENT
        # workspaces may still each have their own "report.pdf".
        UniqueConstraint("workspace_id", "filename", name="uq_documents_workspace_id_filename"),
    )

    # Who actually uploaded it — kept for authorship/audit display, but no
    # longer the ACCESS-CONTROL boundary; workspace_id below is. ondelete=
    # CASCADE still applies (deleting the uploader's account still deletes
    # their documents) — a real product might instead reassign orphaned
    # documents to the workspace, but that's a future decision, not a
    # silent behavior change to make here.
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # The actual visibility/access-control boundary (see models/workspace.py) —
    # every workspace member can see this document, gated by their
    # WorkspaceRole's permissions, regardless of who owner_id above points
    # at. ondelete=CASCADE: deleting a workspace deletes the documents
    # that only ever existed inside it.
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
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
    workspace: Mapped["Workspace"] = relationship()
