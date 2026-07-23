import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from core.security import create_access_token, verify_password
from repositories.user_repository import UserRepository


class InvalidCredentialsError(Exception):
    """Raised for both 'no such user' and 'wrong password'. Deliberately
    the SAME error either way — see the Phase 4 write-up for why telling
    an attacker which one it was is a real information leak, not a
    convenience."""


class AuthService:
    """Verifying who someone is, and issuing proof of that (a token) —
    a distinct concern from UserService, which manages user records
    themselves. Login isn't really "user management," even though it
    reads from the same table.
    """

    def __init__(self, db: AsyncSession):
        self.repository = UserRepository(db)

    async def login(self, *, email: str, password: str) -> str:
        user = await self.repository.get_by_email(email)
        # Short-circuits on `user is None` exactly as before — bcrypt is
        # never invoked for a nonexistent email, unchanged behavior, only
        # WHERE the real verify_password() call runs is different now.
        # bcrypt.checkpw is the same class of blocking, CPU-bound call as
        # hash_password() (see UserService.create_user()'s identical
        # fix) — inline, it stalls the whole event loop for every OTHER
        # concurrent request for its duration, which this phase's load
        # testing caught directly (100% login failure at just 15
        # concurrent users, each queued behind others' bcrypt calls).
        if user is None or not await asyncio.to_thread(
            verify_password, password, user.password_hash
        ):
            raise InvalidCredentialsError()

        return create_access_token(subject=str(user.id))
