import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import BaseModel

if TYPE_CHECKING:
    from models.user import User


class OAuthAccount(BaseModel):
    """The `oauth_accounts` table — links one external provider identity
    (e.g. a specific Google account) to exactly one local User row.

    A separate table, not columns bolted onto User, because a single
    user can plausibly link MULTIPLE providers to the same account
    (sign up with a password, later also connect Google) — one row per
    (provider, provider_account_id) pair, not one row per user.
    """

    __tablename__ = "oauth_accounts"
    __table_args__ = (
        UniqueConstraint(
            "provider", "provider_account_id", name="uq_oauth_provider_account"
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # "google" | "github" | "microsoft" — a plain string, not an Enum
    # column, same reasoning as DocumentStatus/UserRole: Python-level
    # validation (see the Literal type on AuthService.get_or_create_oauth_user)
    # is enough, and a plain String avoids a migration to add the next
    # provider.
    provider: Mapped[str] = mapped_column(String)
    # The provider's own stable identifier for this account (Google's
    # `sub` claim, GitHub's numeric user id, Microsoft's `oid`) — NEVER
    # the user's email. Emails can change or be reused; a provider's
    # subject identifier is the one thing guaranteed stable for the life
    # of that account, which is why it's what THIS table keys on, even
    # though email is what AuthService uses to link a first-time OAuth
    # login to an existing password-based account.
    provider_account_id: Mapped[str] = mapped_column(String)

    user: Mapped["User"] = relationship()
