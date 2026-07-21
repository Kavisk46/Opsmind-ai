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
        if user is None or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError()

        return create_access_token(subject=str(user.id))
