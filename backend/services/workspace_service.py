import uuid
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession

from models.workspace import Workspace
from models.workspace_member import WorkspaceMember, WorkspaceRole
from repositories.user_repository import UserRepository
from repositories.workspace_member_repository import WorkspaceMemberRepository
from repositories.workspace_repository import WorkspaceRepository


class WorkspacePermission(str, Enum):
    """One action a WorkspaceRole either grants or doesn't — see
    _ROLE_PERMISSIONS below for the actual mapping. A bounded set, not
    free text, for the same reason every other role/status enum in this
    codebase is (DocumentStatus, UserRole, WorkspaceRole itself).
    """

    UPLOAD = "upload"
    DELETE = "delete"
    CHAT = "chat"
    MANAGE_SETTINGS = "manage_settings"
    MANAGE_MEMBERS = "manage_members"
    VIEW_AUDIT_LOGS = "view_audit_logs"


# The actual permission matrix this phase's RBAC module asks for. VIEWER
# can read/chat but never mutate anything; EDITOR adds upload/delete;
# ADMIN adds workspace administration; OWNER has everything ADMIN does
# plus is the only role that can delete the workspace itself (enforced
# separately in delete_workspace, not via this table — "can delete the
# whole workspace" isn't a per-action permission the way the rest are).
_ROLE_PERMISSIONS: dict[WorkspaceRole, frozenset[WorkspacePermission]] = {
    WorkspaceRole.VIEWER: frozenset({WorkspacePermission.CHAT}),
    WorkspaceRole.EDITOR: frozenset(
        {WorkspacePermission.CHAT, WorkspacePermission.UPLOAD, WorkspacePermission.DELETE}
    ),
    WorkspaceRole.ADMIN: frozenset(
        {
            WorkspacePermission.CHAT,
            WorkspacePermission.UPLOAD,
            WorkspacePermission.DELETE,
            WorkspacePermission.MANAGE_SETTINGS,
            WorkspacePermission.MANAGE_MEMBERS,
            WorkspacePermission.VIEW_AUDIT_LOGS,
        }
    ),
    WorkspaceRole.OWNER: frozenset(
        {
            WorkspacePermission.CHAT,
            WorkspacePermission.UPLOAD,
            WorkspacePermission.DELETE,
            WorkspacePermission.MANAGE_SETTINGS,
            WorkspacePermission.MANAGE_MEMBERS,
            WorkspacePermission.VIEW_AUDIT_LOGS,
        }
    ),
}


def has_permission(role: WorkspaceRole, permission: WorkspacePermission) -> bool:
    """The single source of truth every permission check in this phase
    goes through — both WorkspaceService's own member-management checks
    below AND api/dependencies.py's require_workspace_permission()
    dependency call this SAME function against the SAME table, rather
    than each maintaining its own copy that could silently drift apart.
    """
    return permission in _ROLE_PERMISSIONS[role]


class WorkspaceNotFoundError(Exception):
    """Raised both when a workspace_id truly doesn't exist AND when it
    exists but the caller isn't a member — same anti-enumeration
    reasoning as DocumentNotFoundError/ConversationNotFoundError: a 404
    that only fired for workspaces you don't belong to would let a caller
    enumerate other workspaces' IDs by watching for 403 vs. 404.
    """


class NotAWorkspaceMemberError(Exception):
    """Raised when an operation targets a user who isn't (or isn't yet) a
    member of the workspace in question — e.g. changing the role of
    someone who was never added, or removing them twice.
    """


class InsufficientWorkspacePermissionError(Exception):
    """Raised when an authenticated, real MEMBER of the workspace still
    doesn't have the specific permission an action requires — distinct
    from NotAWorkspaceMemberError (not a member at all) the same way a
    403 is distinct from a 404 everywhere else in this codebase.
    """


class LastOwnerError(Exception):
    """Raised when an action would leave a workspace with zero OWNERs —
    removing the last owner, or demoting them to a lesser role. Every
    workspace must always have at least one OWNER capable of managing it;
    without this guard, a workspace could be permanently locked (no one
    left with MANAGE_MEMBERS/settings permission to fix it) by a single
    careless role change.
    """


class EmptyWorkspaceNameError(Exception):
    """Raised when creating or renaming a workspace with a blank/
    whitespace-only name — same "never worth persisting" reasoning as
    EmptyQuestionError/EmptyTitleError elsewhere in this codebase.
    """


class WorkspaceService:
    """Owns workspace lifecycle and membership — creation, rename,
    delete, and adding/removing/re-roling members. Permission enforcement
    for MEMBERSHIP operations lives here (has_permission() calls below);
    permission enforcement for DOCUMENT/CHAT operations lives in
    api/dependencies.py's require_workspace_permission(), reusing the
    exact same has_permission() function — one shared table, two call
    sites.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.workspaces = WorkspaceRepository(db)
        self.members = WorkspaceMemberRepository(db)
        self.users = UserRepository(db)

    async def ensure_personal_workspace(self, user_id: uuid.UUID, user_name: str) -> Workspace:
        """Called once, right after a brand-new user is created (signup
        or OAuth first-login — see api/routes/users.py/oauth.py), so
        every user always has at least one workspace to operate in
        without a client ever having to create one first. Safe to call
        more than once for the same user (checks for an existing default
        first) — not because normal operation ever does, but because
        "the caller already has a default workspace" is a real,
        recoverable state worth handling gracefully rather than assuming
        away.
        """
        user = await self.users.get_by_id(user_id)
        if user is not None and user.default_workspace_id is not None:
            existing = await self.workspaces.get_by_id(user.default_workspace_id)
            if existing is not None:
                return existing

        workspace = await self.workspaces.create(
            name=f"{user_name}'s Workspace" if user_name else "Personal Workspace",
            description=None,
            created_by=user_id,
        )
        await self.members.create(
            workspace_id=workspace.id, user_id=user_id, role=WorkspaceRole.OWNER.value
        )
        if user is not None:
            await self.users.update(user, default_workspace_id=workspace.id)
        return workspace

    async def create_workspace(
        self, *, owner_id: uuid.UUID, name: str, description: str | None = None
    ) -> Workspace:
        if not name.strip():
            raise EmptyWorkspaceNameError()

        workspace = await self.workspaces.create(
            name=name.strip(), description=description, created_by=owner_id
        )
        await self.members.create(
            workspace_id=workspace.id, user_id=owner_id, role=WorkspaceRole.OWNER.value
        )
        return workspace

    async def list_workspaces_for_user(self, user_id: uuid.UUID) -> list[Workspace]:
        return await self.workspaces.list_for_user(user_id)

    async def get_workspace(
        self, *, user_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> Workspace:
        membership = await self.members.get_membership(
            workspace_id=workspace_id, user_id=user_id
        )
        if membership is None:
            raise WorkspaceNotFoundError(workspace_id)
        workspace = await self.workspaces.get_by_id(workspace_id)
        if workspace is None:
            raise WorkspaceNotFoundError(workspace_id)
        return workspace

    async def rename_workspace(
        self, *, user_id: uuid.UUID, workspace_id: uuid.UUID, name: str
    ) -> Workspace:
        if not name.strip():
            raise EmptyWorkspaceNameError()

        workspace = await self._require_permission(
            user_id=user_id,
            workspace_id=workspace_id,
            permission=WorkspacePermission.MANAGE_SETTINGS,
        )
        return await self.workspaces.update(workspace, name=name.strip())

    async def delete_workspace(self, *, user_id: uuid.UUID, workspace_id: uuid.UUID) -> None:
        # Deliberately OWNER-only, not just MANAGE_SETTINGS — every role
        # that can manage settings (ADMIN, OWNER) shares that permission,
        # but deleting the whole workspace (and every document/
        # conversation inside it — see the CASCADE in models/workspace.py)
        # is a bigger, less reversible action than a settings change.
        membership = await self.members.get_membership(
            workspace_id=workspace_id, user_id=user_id
        )
        if membership is None:
            raise WorkspaceNotFoundError(workspace_id)
        if WorkspaceRole(membership.role) != WorkspaceRole.OWNER:
            raise InsufficientWorkspacePermissionError()

        workspace = await self.workspaces.get_by_id(workspace_id)
        if workspace is None:
            raise WorkspaceNotFoundError(workspace_id)
        await self.workspaces.delete(workspace)

    async def list_members(
        self, *, user_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> list[WorkspaceMember]:
        # Any member can see who else is in the workspace — membership
        # itself is the only gate, not a specific permission, matching
        # how most real products treat "who's in this workspace" as
        # baseline, non-sensitive information for members.
        membership = await self.members.get_membership(
            workspace_id=workspace_id, user_id=user_id
        )
        if membership is None:
            raise WorkspaceNotFoundError(workspace_id)
        return await self.members.list_by_workspace(workspace_id)

    async def add_member(
        self,
        *,
        actor_user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        new_member_user_id: uuid.UUID,
        role: WorkspaceRole,
    ) -> WorkspaceMember:
        await self._require_permission(
            user_id=actor_user_id,
            workspace_id=workspace_id,
            permission=WorkspacePermission.MANAGE_MEMBERS,
        )
        existing = await self.members.get_membership(
            workspace_id=workspace_id, user_id=new_member_user_id
        )
        if existing is not None:
            return await self.members.update(existing, role=role.value)
        return await self.members.create(
            workspace_id=workspace_id, user_id=new_member_user_id, role=role.value
        )

    async def change_member_role(
        self,
        *,
        actor_user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        target_user_id: uuid.UUID,
        new_role: WorkspaceRole,
    ) -> WorkspaceMember:
        await self._require_permission(
            user_id=actor_user_id,
            workspace_id=workspace_id,
            permission=WorkspacePermission.MANAGE_MEMBERS,
        )
        target_membership = await self.members.get_membership(
            workspace_id=workspace_id, user_id=target_user_id
        )
        if target_membership is None:
            raise NotAWorkspaceMemberError(target_user_id)

        if (
            WorkspaceRole(target_membership.role) == WorkspaceRole.OWNER
            and new_role != WorkspaceRole.OWNER
            and await self._is_last_owner(workspace_id)
        ):
            raise LastOwnerError()

        return await self.members.update(target_membership, role=new_role.value)

    async def remove_member(
        self, *, actor_user_id: uuid.UUID, workspace_id: uuid.UUID, target_user_id: uuid.UUID
    ) -> None:
        await self._require_permission(
            user_id=actor_user_id,
            workspace_id=workspace_id,
            permission=WorkspacePermission.MANAGE_MEMBERS,
        )
        target_membership = await self.members.get_membership(
            workspace_id=workspace_id, user_id=target_user_id
        )
        if target_membership is None:
            raise NotAWorkspaceMemberError(target_user_id)

        if (
            WorkspaceRole(target_membership.role) == WorkspaceRole.OWNER
            and await self._is_last_owner(workspace_id)
        ):
            raise LastOwnerError()

        await self.members.delete(target_membership)

    async def _require_permission(
        self, *, user_id: uuid.UUID, workspace_id: uuid.UUID, permission: WorkspacePermission
    ) -> Workspace:
        membership = await self.members.get_membership(
            workspace_id=workspace_id, user_id=user_id
        )
        if membership is None:
            raise WorkspaceNotFoundError(workspace_id)
        if not has_permission(WorkspaceRole(membership.role), permission):
            raise InsufficientWorkspacePermissionError()

        workspace = await self.workspaces.get_by_id(workspace_id)
        if workspace is None:
            raise WorkspaceNotFoundError(workspace_id)
        return workspace

    async def _is_last_owner(self, workspace_id: uuid.UUID) -> bool:
        members = await self.members.list_by_workspace(workspace_id)
        owner_count = sum(1 for m in members if WorkspaceRole(m.role) == WorkspaceRole.OWNER)
        return owner_count <= 1
