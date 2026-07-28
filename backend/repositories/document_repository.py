import uuid
from typing import Literal

from sqlalchemy import func, select

from models.document import Document
from repositories.base import BaseRepository

SortOption = Literal["newest", "oldest", "largest", "smallest"]

_SORT_COLUMNS = {
    "newest": Document.created_at.desc(),
    "oldest": Document.created_at.asc(),
    "largest": Document.size_bytes.desc(),
    "smallest": Document.size_bytes.asc(),
}


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

    async def get_by_owner_and_filename(
        self, owner_id: uuid.UUID, filename: str
    ) -> Document | None:
        # Backs DocumentService's duplicate-filename pre-check — a fast,
        # common-case rejection before any disk I/O happens. The
        # uq_documents_owner_id_filename DB constraint (see the migration)
        # remains the authoritative guard against a true concurrent-upload
        # race this SELECT-then-decide check can't fully close on its own.
        result = await self.db.execute(
            select(Document).where(
                Document.owner_id == owner_id, Document.filename == filename
            )
        )
        return result.scalar_one_or_none()

    async def search(
        self,
        *,
        owner_id: uuid.UUID,
        query: str | None,
        content_type: str | None,
        sort: SortOption,
    ) -> list[Document]:
        """Backs GET /documents/search. `query` matches filename only —
        the other two fields your spec calls "searchable" (metadata,
        mime type) are exact-match FILTERS in this schema (content_type
        below), not free-text fields; there is no separate "metadata"
        column to search against, and treating content_type as a filter
        rather than a substring match is what makes "give me only my
        PDFs" a precise, reliable query instead of a fuzzy one.

        ilike() (case-insensitive LIKE) is used instead of like() so a
        search for "report" also finds "Report.pdf" — SQLAlchemy compiles
        this to a portable `LOWER(x) LIKE LOWER(y)` on backends (like this
        project's SQLite test suite) that have no native ILIKE, so this
        behaves identically in tests and in the real Postgres deployment.
        """
        stmt = select(Document).where(Document.owner_id == owner_id)
        if query:
            stmt = stmt.where(Document.filename.ilike(f"%{query}%"))
        if content_type:
            stmt = stmt.where(Document.content_type == content_type)
        stmt = stmt.order_by(_SORT_COLUMNS[sort])

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_by_owner(self, owner_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count(Document.id)).where(Document.owner_id == owner_id)
        )
        return result.scalar_one()

    async def total_size_bytes_by_owner(self, owner_id: uuid.UUID) -> int:
        # coalesce to 0: SUM() over zero rows is SQL NULL, not 0 — a
        # brand new user with no documents should see "0 bytes used", not
        # a null that every caller would otherwise have to special-case.
        result = await self.db.execute(
            select(func.coalesce(func.sum(Document.size_bytes), 0)).where(
                Document.owner_id == owner_id
            )
        )
        return result.scalar_one()

    async def count_by_content_type(self, owner_id: uuid.UUID) -> dict[str, int]:
        result = await self.db.execute(
            select(Document.content_type, func.count(Document.id))
            .where(Document.owner_id == owner_id)
            .group_by(Document.content_type)
        )
        return dict(result.all())

    async def list_recent_by_owner(
        self, owner_id: uuid.UUID, limit: int
    ) -> list[Document]:
        result = await self.db.execute(
            select(Document)
            .where(Document.owner_id == owner_id)
            .order_by(Document.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
