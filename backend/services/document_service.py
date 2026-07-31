import uuid
from dataclasses import dataclass
from pathlib import PurePosixPath

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.filenames import sanitize_filename
from core.storage import Storage
from core.text_extraction import SUPPORTED_CONTENT_TYPES
from core.vector_store import VectorStore
from models.document import Document
from repositories.chunk_repository import ChunkRepository
from repositories.document_repository import DocumentRepository, SortOption

# Recent-uploads list length for GET /documents/stats — a fixed, small
# constant rather than a client-supplied parameter: this endpoint answers
# "what's been happening lately," not "give me a paginated document
# list" (that's what /documents and /documents/search are for).
_STATS_RECENT_UPLOADS_LIMIT = 5

# Every type SUPPORTED_CONTENT_TYPES (core/text_extraction.py) can extract
# text from is, by definition, also safe to accept for upload — derived
# via union rather than hand-duplicated so the two lists can never
# silently drift apart if a future phase adds a new extractable format.
# The extra types below have no text-extraction path at all (see
# IngestionService.process_document, which knows to skip them and mark
# the document READY directly rather than FAILED) but are still
# legitimate knowledge-base assets: a screenshot, a signed contract scan.
# A client can still LIE about content_type (see this phase's security
# review for why that's an accepted, honestly-documented limit, not
# something this list fixes).
ACCEPTED_UPLOAD_CONTENT_TYPES = SUPPORTED_CONTENT_TYPES | frozenset(
    {
        "image/png",
        "image/jpeg",
    }
)


class EmptyFileError(Exception):
    """Raised when an upload has zero bytes — never worth storing or
    tracking as a document."""


class FileTooLargeError(Exception):
    """Raised when an upload exceeds the configured size limit."""


class UnsupportedFileTypeError(Exception):
    """Raised when a client-declared content_type isn't one this app
    accepts at all — checked and rejected HERE, at upload time, rather
    than only discovered later during background ingestion. Before this,
    an arbitrary file (a .zip, an .exe, anything) with any content_type
    was accepted, stored to disk, given a 202, and only failed minutes
    later in a background task — wasted storage and bandwidth for
    something rejectable in milliseconds. This is a declared-content-type
    check, not a magic-bytes/real-file-sniffing check — a client can
    still LIE about content_type (see this phase's security review for
    why that's an accepted, honestly-documented limit, not something this
    fixes)."""


class DuplicateFilenameError(Exception):
    """Raised when the workspace already has a document with this exact
    (sanitized) filename. Authoritatively enforced by the
    uq_documents_workspace_id_filename DB constraint (see the migration
    that added it) — the repository pre-check in upload_document exists
    purely so the common case returns a clean error without ever writing
    bytes to disk first; the constraint is what actually closes the race
    a true concurrent double-upload could otherwise slip through.
    """

    def __init__(self, filename: str):
        self.filename = filename
        super().__init__(f"A document named {filename!r} already exists.")


class DocumentNotFoundError(Exception):
    """Raised both when a document truly doesn't exist AND when it exists
    but belongs to a different workspace. Collapsing those two cases is
    deliberate — the same reason a wrong password and an unknown email
    return the same error in AuthService: a 404 that only fires for
    documents outside your workspace would let a caller enumerate other
    workspaces' document IDs by watching for 403 vs. 404.
    """


@dataclass
class DocumentStats:
    """Backs GET /documents/stats. A plain dataclass, not a query
    result tuple — schemas.document.DocumentStatsResponse validates
    directly off of it (Pydantic's from_attributes), so this is the one
    place the shape of that response is actually defined; the schema
    just mirrors it for the API contract.
    """

    total_documents: int
    total_storage_bytes: int
    documents_by_type: dict[str, int]
    recent_uploads: list[Document]


class DocumentService:
    """Every method here scopes by WORKSPACE, not owner — see
    repositories/document_repository.py's docstring for why: a shared
    workspace's documents are visible to every member, gated by their
    WorkspaceRole permission (enforced upstream, at the route layer, via
    api/dependencies.py's require_workspace_permission — this service
    itself only needs to know WHICH workspace, not re-check who's
    allowed to act on it).
    """

    def __init__(
        self,
        db: AsyncSession,
        storage: Storage,
        max_size_bytes: int,
        vector_store: VectorStore,
        chunk_repository: ChunkRepository,
    ):
        self.db = db
        self.repository = DocumentRepository(db)
        self.storage = storage
        self.max_size_bytes = max_size_bytes
        self.vector_store = vector_store
        self.chunk_repository = chunk_repository

    async def upload_document(
        self,
        *,
        owner_id: uuid.UUID,
        workspace_id: uuid.UUID,
        filename: str,
        content_type: str,
        data: bytes,
    ) -> Document:
        if len(data) == 0:
            raise EmptyFileError(filename)
        if len(data) > self.max_size_bytes:
            raise FileTooLargeError(filename)
        if content_type not in ACCEPTED_UPLOAD_CONTENT_TYPES:
            raise UnsupportedFileTypeError(content_type)

        # Cleaned before it's ever persisted, displayed, or (once the
        # download endpoint exists) sent back in a response header — see
        # core/filenames.py's own docstring for exactly what this guards
        # against and what it deliberately does NOT (path traversal is
        # already impossible; the bytes are never written under this
        # name).
        safe_filename = sanitize_filename(filename)

        # Fast-path rejection before any disk I/O — the common case (a
        # second upload of the same filename INTO THE SAME WORKSPACE,
        # regardless of who uploads it) never needs to touch storage at
        # all. This is a plain SELECT, so it does NOT close the race a
        # true concurrent double-upload could hit; the
        # uq_documents_workspace_id_filename constraint below is what
        # actually guarantees correctness.
        existing = await self.repository.get_by_workspace_and_filename(
            workspace_id, safe_filename
        )
        if existing is not None:
            raise DuplicateFilenameError(safe_filename)

        # A random key, not the original filename, so two uploads named
        # "notes.pdf" in different workspaces never collide on disk — the
        # human-readable name is preserved separately in the DB row.
        # Namespaced under the UPLOADER's id (see core/storage.py's
        # Storage Protocol docstring) so one user's files live together
        # on disk, the same layout an S3 bucket would use for prefixes —
        # this is purely a storage-layout detail, unrelated to which
        # workspace the document is visible in.
        extension = PurePosixPath(safe_filename).suffix
        storage_key = f"{owner_id}/{uuid.uuid4()}{extension}"
        self.storage.save(key=storage_key, data=data)

        try:
            return await self.repository.create(
                owner_id=owner_id,
                workspace_id=workspace_id,
                filename=safe_filename,
                content_type=content_type,
                size_bytes=len(data),
                storage_key=storage_key,
            )
        except IntegrityError as error:
            # The rare case the pre-check above couldn't catch: two
            # requests for the same new filename both passed the SELECT
            # before either committed. The DB constraint is what actually
            # rejects the second INSERT — this just turns that into the
            # same clean DuplicateFilenameError as the fast path, and
            # cleans up the file this request already wrote (an orphaned
            # blob nothing will ever reference again otherwise). A failed
            # flush leaves the session's transaction unusable until rolled
            # back — required here, not optional, before anything else
            # touches self.db.
            await self.db.rollback()
            self.storage.delete(key=storage_key)
            raise DuplicateFilenameError(safe_filename) from error

    async def list_documents(self, *, workspace_id: uuid.UUID) -> list[Document]:
        return await self.repository.list_by_workspace(workspace_id)

    async def search_documents(
        self,
        *,
        workspace_id: uuid.UUID,
        query: str | None,
        content_type: str | None,
        sort: SortOption,
    ) -> list[Document]:
        return await self.repository.search(
            workspace_id=workspace_id, query=query, content_type=content_type, sort=sort
        )

    async def get_stats(self, *, workspace_id: uuid.UUID) -> DocumentStats:
        return DocumentStats(
            total_documents=await self.repository.count_by_workspace(workspace_id),
            total_storage_bytes=await self.repository.total_size_bytes_by_workspace(
                workspace_id
            ),
            documents_by_type=await self.repository.count_by_content_type(workspace_id),
            recent_uploads=await self.repository.list_recent_by_workspace(
                workspace_id, _STATS_RECENT_UPLOADS_LIMIT
            ),
        )

    async def get_document(
        self, *, workspace_id: uuid.UUID, document_id: uuid.UUID
    ) -> Document:
        document = await self.repository.get_by_id(document_id)
        if document is None or document.workspace_id != workspace_id:
            raise DocumentNotFoundError(document_id)
        return document

    async def download_document(
        self, *, workspace_id: uuid.UUID, document_id: uuid.UUID
    ) -> tuple[Document, bytes]:
        # Reuses get_document()'s workspace check — same anti-enumeration
        # guarantee as delete_document. storage.open() stays encapsulated
        # here rather than the route reaching into self.storage directly,
        # the same "routes only ever call service methods" boundary every
        # other endpoint in this file already respects.
        document = await self.get_document(workspace_id=workspace_id, document_id=document_id)
        data = self.storage.open(key=document.storage_key)
        return document, data

    async def delete_document(
        self, *, workspace_id: uuid.UUID, document_id: uuid.UUID
    ) -> None:
        # Reuses get_document() rather than repeating the workspace
        # check — same DocumentNotFoundError, same anti-enumeration
        # guarantee, for free: a delete attempt on a document outside
        # this workspace 404s exactly like a GET does, never revealing
        # that the document exists. WHETHER the caller is ALLOWED to
        # delete (not just see) is enforced upstream, at the route layer,
        # via require_workspace_permission(WorkspacePermission.DELETE).
        document = await self.get_document(workspace_id=workspace_id, document_id=document_id)

        # Order matters: delete the file bytes and vectors first, the DB
        # row second. If either delete fails (e.g. a permissions error),
        # the DB row survives and the document is still visible/retryable.
        # The reverse order — delete the row, then the file/vectors —
        # risks a crash between the steps leaving orphaned data with no DB
        # row pointing at it, invisible and unrecoverable through this
        # API. An orphaned DB row (this order's failure mode) is at least
        # still visible and fixable. chunk_repository is called explicitly
        # here (not left to the document_chunks table's ON DELETE CASCADE
        # foreign key alone) for the same reason vector_store is: this
        # project's test suite runs against SQLite with foreign key
        # enforcement off (see tests/conftest.py), so relying purely on
        # the DB-level cascade would leave this behavior untested there.
        self.storage.delete(key=document.storage_key)
        self.vector_store.delete_by_document(document_id=str(document.id))
        await self.chunk_repository.delete_by_document(document.id)
        await self.repository.delete(document)
