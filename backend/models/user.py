import uuid
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import BaseModel

if TYPE_CHECKING:
    from models.conversation import Conversation
    from models.document import Document
    from models.workspace import Workspace
    from models.workspace_member import WorkspaceMember


class UserRole(str, Enum):
    """A bounded set of roles, not free text — same reasoning as
    DocumentStatus in models/document.py. MEMBER is the default (see the
    `role` column below); MANAGER/ADMIN are opt-in, granted explicitly.

    Adding MANAGER here needs no migration: `role` is a plain String
    column (see repositories/base.py's design note on Python-level vs.
    database-level enums) — the database has no CHECK constraint
    restricting which strings are valid, only this Python Enum does. A
    native Postgres ENUM type would have required an ALTER TYPE migration
    for this exact change; this deliberately simpler choice is why it
    doesn't.
    """

    ADMIN = "admin"
    MANAGER = "manager"
    MEMBER = "member"


class User(BaseModel):
    """The `users` table.

    This is a database-shape definition only — it has no opinion on what
    the API exposes. See schemas/user.py for the separate, API-facing
    contract; the two are allowed to differ and evolve independently.
    """

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    # Nullable, unique when set: the existing signup flow (services/
    # user_service.py) doesn't collect a username yet, so this can't be
    # NOT NULL without breaking every existing signup. NULL is exempt from
    # the unique constraint in Postgres/SQLite (multiple NULLs are
    # allowed), so many usernameless users can coexist safely until the
    # signup flow is extended to require one.
    username: Mapped[str | None] = mapped_column(String, unique=True, index=True, nullable=True)
    name: Mapped[str] = mapped_column(String)
    # A bcrypt hash, never a plaintext password — see core/security.py.
    # Nullable: a user who signs up via Google/GitHub/Microsoft OAuth
    # (see services/auth_service.py's get_or_create_oauth_user) has no
    # password at all — AuthService.login() must reject a password-login
    # attempt against such a row rather than crash comparing against None.
    password_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    role: Mapped[str] = mapped_column(String, default=UserRole.MEMBER.value)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Replaces the earlier single team_id FK — real membership (many
    # workspaces per user, each with its own role) now lives in
    # WorkspaceMember; this is just a convenience pointer to "which
    # workspace to use when a request doesn't say" (see
    # api/dependencies.py's get_current_workspace). ondelete="SET NULL":
    # deleting a workspace shouldn't cascade into deleting the USER who
    # merely had it set as their default.
    default_workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # foreign_keys is required here, not optional — Workspace.created_by
    # is ALSO a FK from workspaces back to users.id, so there are two
    # distinct FK paths between these two tables (users.default_workspace_id
    # -> workspaces.id, and workspaces.created_by -> users.id).
    # SQLAlchemy can't guess which one THIS relationship means without
    # being told explicitly; omitting this raises AmbiguousForeignKeysError
    # at mapper-configuration time (verified directly while wiring this
    # phase's tests).
    default_workspace: Mapped["Workspace | None"] = relationship(
        foreign_keys=[default_workspace_id]
    )
    workspace_memberships: Mapped[list["WorkspaceMember"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    documents: Mapped[list["Document"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
