import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from core.security import hash_password
from models.user import User
from repositories.user_repository import UserRepository


class DuplicateEmailError(Exception):
    """Raised when signup is attempted with an email already in use.
    A plain Python exception, not an HTTPException — the service layer
    has no concept of HTTP status codes; translating this into a 409 is
    the route's job (see api/routes/users.py)."""


class UserService:
    """Business logic for users. list_users() is still a pure pass-through
    — that rule still has nowhere to live yet. create_user() below is the
    first real business rule this layer enforces: no two users may share
    an email, regardless of which route or future caller creates a user.
    """

    def __init__(self, db: AsyncSession):
        self.repository = UserRepository(db)

    async def list_users(self) -> list[User]:
        return await self.repository.get_all()

    async def create_user(self, *, email: str, name: str, password: str) -> User:
        existing = await self.repository.get_by_email(email)
        if existing is not None:
            raise DuplicateEmailError(email)

        # bcrypt.hashpw is synchronous, CPU-bound work — a real bottleneck
        # this phase's load testing found directly: calling it inline
        # blocks the ENTIRE event loop for its whole duration (bcrypt is
        # deliberately slow, that's the point of it as a KDF), which
        # means every OTHER concurrent request on this worker — including
        # totally unrelated ones like /health — stalls behind it too.
        # asyncio.to_thread offloads it to a worker thread, the exact
        # same fix already applied to LocalTransformersProvider.generate()
        # for the identical class of problem (see its docstring).
        password_hash = await asyncio.to_thread(hash_password, password)
        return await self.repository.create(
            email=email, name=name, password_hash=password_hash
        )
