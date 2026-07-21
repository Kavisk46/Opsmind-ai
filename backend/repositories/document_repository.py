import uuid

from sqlalchemy import select

from models.document import Document
from repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    """Owns every query against the `documents` table. Generic CRUD comes
    from BaseRepository; list_by_owner/list_by_status are specific to
    documents — ownership and processing status aren't concepts every
    entity has.
    """

    model = Document

    async def list_by_owner(self, owner_id: uuid.UUID) -> list[Document]:
        result = await self.db.execute(
            select(Document).where(Document.owner_id == owner_id)
        )
        return list(result.scalars().all())

    async def list_by_status(self, status: str) -> list[Document]:
        result = await self.db.execute(
            select(Document).where(Document.status == status)
        )
        return list(result.scalars().all())
