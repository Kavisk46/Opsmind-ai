import uuid
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import BaseModel

if TYPE_CHECKING:
    from models.user import User
    from models.workspace import Workspace


class WorkspaceRole(str, Enum):
    """A user's permission level WITHIN one specific workspace — an
    entirely different axis from models.user.UserRole (a platform-wide
    role, e.g. who can view cross-workspace AI metrics). A user can hold
    a different WorkspaceRole in every workspace they belong to; the same
    person might be OWNER of one workspace and VIEWER of another.

    OWNER is granted automatically to whoever creates a workspace (see
    WorkspaceService.create_workspace) — every workspace has exactly one
    at creation, though ownership can be transferred later (a real
    feature, not built in this phase).
    """

    OWNER = "owner"
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class WorkspaceMember(BaseModel):
    """The `workspace_members` table — the many-to-many membership between
    Users and Workspaces, with a role attached to each membership. This
    replaces the old, simpler User.team_id (one team per user) with real
    many-to-many membership: a user can belong to several workspaces, each
    with its own role, and can switch between them (see
    api/dependencies.py's get_current_workspace).
    """

    __tablename__ = "workspace_members"
    __table_args__ = (
        # A user can only have ONE membership (one role) per workspace —
        # changing role is an UPDATE to this row, never a second INSERT.
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_members_workspace_id_user_id"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String, default=WorkspaceRole.VIEWER.value)

    workspace: Mapped["Workspace"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="workspace_memberships")
