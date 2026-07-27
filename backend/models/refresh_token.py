import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import BaseModel

if TYPE_CHECKING:
    from models.user import User


class RefreshToken(BaseModel):
    """The `refresh_tokens` table — one row per issued refresh token.

    Deliberately NOT a JWT (see core/security.py's create_refresh_token
    docstring) — an opaque random string whose SHA-256 hash is stored
    here, so this row is the single source of truth for whether a given
    refresh token is still valid. That's what makes real revocation
    possible: logout, or detecting reuse of an already-rotated token,
    both just need to flip `revoked_at` on the right row — no JWT
    blocklist, no waiting for a self-contained token to merely expire.
    """

    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # SHA-256 hex digest, never the raw token — same reasoning as
    # password_hash: a database leak shouldn't hand out usable
    # credentials. Unlike a password, this token is already
    # high-entropy (secrets.token_urlsafe(32)), so a fast cryptographic
    # hash is correct here — bcrypt's deliberate slowness defends against
    # guessing a LOW-entropy human-chosen secret, which doesn't apply to
    # a 256-bit random value with no brute-forceable structure.
    token_hash: Mapped[str] = mapped_column(String, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # None while valid. Set on logout, or on rotation (see
    # AuthService.refresh) — a rotated-away token is kept, not deleted,
    # specifically so a REPLAY of it (someone reusing a token that's
    # already been rotated past) is detectable rather than silently
    # looking like "just doesn't exist".
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped["User"] = relationship()
