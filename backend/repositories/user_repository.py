from sqlalchemy import select

from models.user import User
from repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Owns every query against the `users` table. get_by_id/get_all/
    create/update/delete/exists all come from BaseRepository — this class
    adds only what's genuinely specific to users: no generic method could
    know to filter on `email`, `username`, or `is_active`, since those
    columns don't exist on every entity.
    """

    model = User

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def list_active_users(self) -> list[User]:
        result = await self.db.execute(select(User).where(User.is_active.is_(True)))
        return list(result.scalars().all())
