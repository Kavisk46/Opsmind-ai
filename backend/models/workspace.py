import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import BaseModel

if TYPE_CHECKING:
    from models.workspace_member import WorkspaceMember


class Workspace(BaseModel):
    """The `workspaces` table — the multi-tenancy boundary (renamed from
    the earlier placeholder `Team`, which was never wired into any route:
    "Team exists now so that team-level scoping can be added later
    without retrofitting a column" — this model, plus WorkspaceMember and
    workspace_id on Document/Conversation, is that later phase.

    Documents and conversations uploaded/started inside a workspace are
    visible to every member of that workspace (see
    repositories/document_repository.py's workspace-scoped queries),
    gated by each member's WorkspaceRole permission (see
    services/workspace_service.py) — NOT limited to whoever originally
    uploaded/asked, which is what makes this a real shared workspace
    rather than just a label. Retrieval/chat's underlying vector search
    still scopes by owner_id for now (a deliberate, staged deferral — see
    this phase's Change Summary); only Document/Conversation-level access
    is workspace-shared as of this phase.
    """

    __tablename__ = "workspaces"

    # Deliberately NOT globally unique (Team's earlier `name` column was) —
    # every user gets an auto-created "Personal" workspace at signup (see
    # WorkspaceService.ensure_personal_workspace), so a global unique
    # constraint on name would make the second user's signup fail outright.
    name: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    # Who created it — distinct from WorkspaceMember's OWNER role (which
    # can be transferred later); this column is a permanent, factual
    # record of authorship, not a mutable permission grant. ondelete=
    # RESTRICT (the default, no ondelete specified): a workspace can't be
    # left pointing at a deleted user — deleting its creator's account is
    # a real product decision (transfer ownership? delete the workspace
    # too?) this phase doesn't need to make, so the FK simply refuses the
    # delete rather than silently choosing an answer.
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)

    members: Mapped[list["WorkspaceMember"]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan"
    )
