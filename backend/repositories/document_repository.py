import uuid
from datetime import datetime
from typing import Literal

from sqlalchemy import UnaryExpression, func, select

from models.document import Document
from repositories.base import BaseRepository

SortOption = Literal["newest", "oldest", "largest", "smallest"]


def _sort_clause(sort: SortOption) -> UnaryExpression[datetime] | UnaryExpression[int]:
    # A plain {sort: column.desc()/.asc()} dict literal is what produced
    # mypy's "object" inference: created_at.desc() and size_bytes.desc()
    # are UnaryExpression[datetime] and UnaryExpression[int] respectively
    # — different instantiations of the same INVARIANT generic — and a
    # dict literal's value type is the JOIN of its values' types, which
    # mypy can only express as `object` when it can't find a common
    # parameterization (UnaryExpression[object] doesn't work either:
    # invariance means UnaryExpression[datetime] is not assignable to
    # UnaryExpression[object], even though datetime is an object). The
    # honest, precise type for "one of these two concrete branches" is
    # their literal union — both members are real, concrete SQLAlchemy
    # types, so this is strictly more precise than the dict version ever
    # was, not a workaround.
    if sort == "newest":
        return Document.created_at.desc()
    if sort == "oldest":
        return Document.created_at.asc()
    if sort == "largest":
        return Document.size_bytes.desc()
    return Document.size_bytes.asc()


class DocumentRepository(BaseRepository[Document]):
    """Owns every query against the `documents` table. Generic CRUD comes
    from BaseRepository; everything below scopes by WORKSPACE, not owner —
    a shared workspace's documents are visible to every member (see
    models/workspace.py's docstring), gated by their WorkspaceRole
    permission (see services/workspace_service.py), not by who originally
    uploaded a given file. owner_id is still stored on Document (who
    actually uploaded it — see models/document.py) but is no longer the
    access-control boundary these queries enforce.
    """

    model = Document

    async def list_by_workspace(self, workspace_id: uuid.UUID) -> list[Document]:
        result = await self.db.execute(
            select(Document).where(Document.workspace_id == workspace_id)
        )
        return list(result.scalars().all())

    async def list_by_status(self, status: str) -> list[Document]:
        result = await self.db.execute(
            select(Document).where(Document.status == status)
        )
        return list(result.scalars().all())

    async def get_by_workspace_and_filename(
        self, workspace_id: uuid.UUID, filename: str
    ) -> Document | None:
        # Backs DocumentService's duplicate-filename pre-check — a fast,
        # common-case rejection before any disk I/O happens. The
        # uq_documents_workspace_id_filename DB constraint (see the
        # migration) remains the authoritative guard against a true
        # concurrent-upload race this SELECT-then-decide check can't fully
        # close on its own.
        result = await self.db.execute(
            select(Document).where(
                Document.workspace_id == workspace_id, Document.filename == filename
            )
        )
        return result.scalar_one_or_none()

    async def search(
        self,
        *,
        workspace_id: uuid.UUID,
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
        stmt = select(Document).where(Document.workspace_id == workspace_id)
        if query:
            stmt = stmt.where(Document.filename.ilike(f"%{query}%"))
        if content_type:
            stmt = stmt.where(Document.content_type == content_type)
        stmt = stmt.order_by(_sort_clause(sort))

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_by_workspace(self, workspace_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count(Document.id)).where(Document.workspace_id == workspace_id)
        )
        return result.scalar_one()

    async def total_size_bytes_by_workspace(self, workspace_id: uuid.UUID) -> int:
        # coalesce to 0: SUM() over zero rows is SQL NULL, not 0 — a
        # brand new workspace with no documents should see "0 bytes used",
        # not a null that every caller would otherwise have to
        # special-case.
        result = await self.db.execute(
            select(func.coalesce(func.sum(Document.size_bytes), 0)).where(
                Document.workspace_id == workspace_id
            )
        )
        return result.scalar_one()

    async def count_by_content_type(self, workspace_id: uuid.UUID) -> dict[str, int]:
        result = await self.db.execute(
            select(Document.content_type, func.count(Document.id))
            .where(Document.workspace_id == workspace_id)
            .group_by(Document.content_type)
        )
        # dict(result.all()) fails mypy: a Row[tuple[str, int]] is
        # iterable/unpackable at runtime but isn't recognized by mypy as
        # a plain tuple[str, int], which is what dict()'s constructor
        # overload requires. Unpacking each Row via a for-loop uses
        # __iter__ typing instead, which mypy resolves correctly.
        return {content_type: count for content_type, count in result.all()}

    async def list_recent_by_workspace(
        self, workspace_id: uuid.UUID, limit: int
    ) -> list[Document]:
        result = await self.db.execute(
            select(Document)
            .where(Document.workspace_id == workspace_id)
            .order_by(Document.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
