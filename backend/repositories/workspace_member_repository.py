import uuid

from sqlalchemy import select

from models.workspace_member import WorkspaceMember
from repositories.base import BaseRepository


class WorkspaceMemberRepository(BaseRepository[WorkspaceMember]):
    """Owns every query against the `workspace_members` table — who
    belongs to a workspace, with what role. Generic CRUD (create/update/
    delete a single membership row) comes from BaseRepository;
    get_membership/list_by_workspace are specific to this join table.
    """

    model = WorkspaceMember

    async def get_membership(
        self, *, workspace_id: uuid.UUID, user_id: uuid.UUID
    ) -> WorkspaceMember | None:
        """The single query everything else in this phase's authorization
        is built on: is this user a member of this workspace, and if so,
        what's their role? (see api/dependencies.py's get_current_workspace
        and require_workspace_permission).
        """
        result = await self.db.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_workspace(self, workspace_id: uuid.UUID) -> list[WorkspaceMember]:
        result = await self.db.execute(
            select(WorkspaceMember)
            .where(WorkspaceMember.workspace_id == workspace_id)
            .order_by(WorkspaceMember.created_at)
        )
        return list(result.scalars().all())
