import uuid
from datetime import UTC, datetime

from sqlalchemy import select

from models.refresh_token import RefreshToken
from repositories.base import BaseRepository


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    model = RefreshToken

    async def get_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        """Unfiltered lookup — used only for reuse-detection (see
        AuthService.refresh()), which needs to tell "this token was
        already rotated away" apart from "this token never existed", so
        it can respond to the former by revoking every OTHER token for
        that user too (a rotated-away token being presented again is a
        real signal someone else has a copy of it).
        """
        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def get_valid_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        """Only returns a row that's still usable — not expired, not
        revoked. A caller doesn't need to duplicate that "is this actually
        valid" logic; a row failing either check is indistinguishable from
        no row at all, which is exactly the semantics AuthService.refresh()
        needs (both should raise the same InvalidRefreshTokenError).
        """
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > datetime.now(UTC),
            )
        )
        return result.scalar_one_or_none()

    async def revoke(self, token: RefreshToken) -> None:
        token.revoked_at = datetime.now(UTC)
        await self.db.flush()

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        """The reuse-detection response: a rotated-away token being
        presented again means whoever is holding it isn't the legitimate
        session anymore (see AuthService.refresh()) — the safe response
        is to kill every refresh token this user has outstanding, not
        just the one that was replayed, forcing a fresh login everywhere.
        """
        now = datetime.now(UTC)
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None)
            )
        )
        for token in result.scalars().all():
            token.revoked_at = now
        await self.db.flush()
