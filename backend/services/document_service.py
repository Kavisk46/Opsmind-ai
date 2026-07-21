import uuid
from pathlib import PurePosixPath

from sqlalchemy.ext.asyncio import AsyncSession

from core.storage import Storage
from models.document import Document
from repositories.document_repository import DocumentRepository


class EmptyFileError(Exception):
    """Raised when an upload has zero bytes — never worth storing or
    tracking as a document."""


class FileTooLargeError(Exception):
    """Raised when an upload exceeds the configured size limit."""


class DocumentNotFoundError(Exception):
    """Raised both when a document truly doesn't exist AND when it exists
    but belongs to a different owner. Collapsing those two cases is
    deliberate — the same reason a wrong password and an unknown email
    return the same error in AuthService: a 404 that only fires for
    documents you don't own would let a caller enumerate other users'
    document IDs by watching for 403 vs. 404.
    """


class DocumentService:
    def __init__(self, db: AsyncSession, storage: Storage, max_size_bytes: int):
        self.repository = DocumentRepository(db)
        self.storage = storage
        self.max_size_bytes = max_size_bytes

    async def upload_document(
        self,
        *,
        owner_id: uuid.UUID,
        filename: str,
        content_type: str,
        data: bytes,
    ) -> Document:
        if len(data) == 0:
            raise EmptyFileError(filename)
        if len(data) > self.max_size_bytes:
            raise FileTooLargeError(filename)

        # A random key, not the original filename, so two uploads named
        # "notes.pdf" by different users never collide on disk — the
        # human-readable name is preserved separately in the DB row.
        extension = PurePosixPath(filename).suffix
        storage_key = f"{uuid.uuid4()}{extension}"
        self.storage.save(key=storage_key, data=data)

        return await self.repository.create(
            owner_id=owner_id,
            filename=filename,
            content_type=content_type,
            size_bytes=len(data),
            storage_key=storage_key,
        )

    async def list_documents(self, *, owner_id: uuid.UUID) -> list[Document]:
        return await self.repository.list_by_owner(owner_id)

    async def get_document(
        self, *, owner_id: uuid.UUID, document_id: uuid.UUID
    ) -> Document:
        document = await self.repository.get_by_id(document_id)
        if document is None or document.owner_id != owner_id:
            raise DocumentNotFoundError(document_id)
        return document
