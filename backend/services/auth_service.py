import asyncio
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings

# TEMPORARY debug instrumentation for the login-timeout investigation —
# remove once the root cause is confirmed and fixed.
from core.logging import logger
from core.security import (
    create_access_token,
    create_refresh_token,
    hash_refresh_token,
    verify_password,
)
from models.user import User
from repositories.oauth_account_repository import OAuthAccountRepository
from repositories.refresh_token_repository import RefreshTokenRepository
from repositories.user_repository import UserRepository


class InvalidCredentialsError(Exception):
    """Raised for both 'no such user' and 'wrong password'. Deliberately
    the SAME error either way — see the Phase 4 write-up for why telling
    an attacker which one it was is a real information leak, not a
    convenience."""


class InvalidRefreshTokenError(Exception):
    """Raised when a presented refresh token doesn't exist, is expired,
    or has already been revoked (including via rotation — see
    AuthService.refresh()). Collapsed into one error/one 401 for the same
    anti-enumeration reason as InvalidCredentialsError: a caller doesn't
    get to distinguish "expired" from "revoked" from "never existed"."""


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str


class AuthService:
    """Verifying who someone is, and issuing proof of that (tokens) — a
    distinct concern from UserService, which manages user records
    themselves. Login isn't really "user management," even though it
    reads from the same table.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.users = UserRepository(db)
        self.refresh_tokens = RefreshTokenRepository(db)
        self.oauth_accounts = OAuthAccountRepository(db)

    async def issue_token_pair(self, user_id: uuid.UUID) -> TokenPair:
        """Shared by every path that establishes a session — password
        login, refresh rotation, and every OAuth callback (see
        api/routes/oauth.py, which calls this directly once it has a
        real User row) — so all three create the SAME shape of access
        token and store the SAME shape of refresh-token row. Access
        tokens are never persisted (they're self-contained JWTs, verified
        by signature+expiry alone); refresh tokens are, since revocation
        requires a row to revoke.
        """
        logger.info("JWT_START")
        jwt_start = time.perf_counter()
        access_token = create_access_token(subject=str(user_id))
        refresh_token = create_refresh_token()
        logger.info("JWT_END elapsed_ms=%.1f", (time.perf_counter() - jwt_start) * 1000)

        logger.info("DB_INSERT_START (refresh_tokens.create)")
        db_start = time.perf_counter()
        await self.refresh_tokens.create(
            user_id=user_id,
            token_hash=hash_refresh_token(refresh_token),
            expires_at=datetime.now(UTC)
            + timedelta(days=settings.refresh_token_expire_days),
        )
        logger.info(
            "DB_INSERT_END (refresh_tokens.create) elapsed_ms=%.1f",
            (time.perf_counter() - db_start) * 1000,
        )

        return TokenPair(access_token=access_token, refresh_token=refresh_token)

    async def login(self, *, email: str, password: str) -> TokenPair:
        logger.info("DB_LOOKUP_START (get_by_email)")
        db_start = time.perf_counter()
        user = await self.users.get_by_email(email)
        logger.info(
            "DB_LOOKUP_END (get_by_email) elapsed_ms=%.1f found=%s",
            (time.perf_counter() - db_start) * 1000,
            user is not None,
        )

        # Short-circuits on `user is None` OR a None password_hash (an
        # OAuth-only account — see models/user.py) exactly as it did
        # before this only checked `user is None`: bcrypt is never
        # invoked for either case. bcrypt.checkpw is the same class of
        # blocking, CPU-bound call as hash_password() (see
        # UserService.create_user()'s identical fix) — inline, it stalls
        # the whole event loop for every OTHER concurrent request for its
        # duration, which this phase's load testing caught directly
        # (100% login failure at just 15 concurrent users, each queued
        # behind others' bcrypt calls).
        logger.info("PASSWORD_VERIFY_START")
        verify_start = time.perf_counter()
        if (
            user is None
            or user.password_hash is None
            or not await asyncio.to_thread(
                verify_password, password, user.password_hash
            )
        ):
            logger.info(
                "PASSWORD_VERIFY_END elapsed_ms=%.1f result=invalid",
                (time.perf_counter() - verify_start) * 1000,
            )
            raise InvalidCredentialsError()
        logger.info(
            "PASSWORD_VERIFY_END elapsed_ms=%.1f result=valid",
            (time.perf_counter() - verify_start) * 1000,
        )

        return await self.issue_token_pair(user.id)

    async def refresh(self, refresh_token: str) -> TokenPair:
        """Rotation, not reuse: the presented token is revoked and a
        BRAND NEW one issued alongside a new access token, every single
        call. This is what makes reuse-detection possible below — a
        legitimate client always presents its most recent token, so any
        future presentation of THIS one again can only mean someone else
        also has a copy of it.
        """
        token_hash = hash_refresh_token(refresh_token)
        stored = await self.refresh_tokens.get_valid_by_token_hash(token_hash)

        if stored is None:
            # Distinguishing "never existed" from "exists but already
            # revoked" is exactly the reuse signal described above — a
            # token that's revoked (as opposed to simply unknown or
            # expired) was very likely rotated away by a legitimate
            # refresh, meaning THIS presentation of it is coming from
            # somewhere else. Revoke every other session this user has
            # as a precaution; the legitimate client will just have to
            # log in again, which is a small cost against a real
            # possible token theft.
            existing = await self.refresh_tokens.get_by_token_hash(token_hash)
            if existing is not None and existing.revoked_at is not None:
                await self.refresh_tokens.revoke_all_for_user(existing.user_id)
            raise InvalidRefreshTokenError()

        await self.refresh_tokens.revoke(stored)
        return await self.issue_token_pair(stored.user_id)

    async def logout(self, refresh_token: str) -> None:
        """Idempotent by design — logging out with an already-expired or
        already-revoked (or even nonexistent) token still "succeeds": the
        caller's goal (no longer having a valid session) is achieved
        either way, and a 401 here would be a confusing response to a
        request whose entire point is to end the session, not start one.
        """
        stored = await self.refresh_tokens.get_by_token_hash(
            hash_refresh_token(refresh_token)
        )
        if stored is not None and stored.revoked_at is None:
            await self.refresh_tokens.revoke(stored)

    async def get_or_create_oauth_user(
        self, *, provider: str, provider_account_id: str, email: str, name: str
    ) -> User:
        """Find-or-create, in three steps, cheapest/most-specific first:

        1. An OAuthAccount already links this exact provider identity to
           a user — the common case for a returning OAuth user.
        2. No linked account yet, but a User with this email already
           exists (they signed up with a password, or via a different
           provider, using the same address) — link this provider to
           that SAME user rather than creating a second, disconnected
           account. This trusts the provider's email as verified, which
           is a standard, accepted assumption for Google/GitHub/
           Microsoft specifically (all three verify email ownership
           before allowing it to be returned via their OAuth scopes).
        3. Neither exists — a genuinely new user, with no password at
           all (models/user.py's password_hash is nullable exactly for
           this row).
        """
        existing_link = await self.oauth_accounts.get_by_provider_account_id(
            provider=provider, provider_account_id=provider_account_id
        )
        if existing_link is not None:
            user = await self.users.get_by_id(existing_link.user_id)
            assert user is not None  # the FK guarantees this; asserted for mypy
            return user

        user = await self.users.get_by_email(email)
        if user is None:
            user = await self.users.create(
                email=email, name=name, password_hash=None
            )

        await self.oauth_accounts.create(
            user_id=user.id, provider=provider, provider_account_id=provider_account_id
        )
        return user
