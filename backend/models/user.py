import uuid
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import BaseModel

if TYPE_CHECKING:
    from models.conversation import Conversation
    from models.document import Document
    from models.team import Team


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
    password_hash: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String, default=UserRole.MEMBER.value)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    team_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("teams.id", ondelete="SET NULL"), nullable=True, index=True
    )

    team: Mapped["Team | None"] = relationship(back_populates="users")
    documents: Mapped[list["Document"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
