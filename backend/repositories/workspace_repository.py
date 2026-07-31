import uuid

from sqlalchemy import select

from models.workspace import Workspace
from models.workspace_member import WorkspaceMember
from repositories.base import BaseRepository


class WorkspaceRepository(BaseRepository[Workspace]):
    """Owns every query against the `workspaces` table itself. Membership
    queries (who belongs to a workspace, with what role) live on
    WorkspaceMemberRepository instead — a workspace's own identity/name
    and its membership list are different concerns, the same separation
    Document/DocumentChunk already have.
    """

    model = Workspace

    async def list_for_user(self, user_id: uuid.UUID) -> list[Workspace]:
        """Every workspace a user is a MEMBER of — not just ones they
        created — via a join through workspace_members. This is what
        backs "list my workspaces" / the workspace switcher.
        """
        result = await self.db.execute(
            select(Workspace)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(WorkspaceMember.user_id == user_id)
            .order_by(Workspace.created_at)
        )
        return list(result.scalars().all())
