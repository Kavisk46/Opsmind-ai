import uuid
from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.base import BaseModel

# Bound to BaseModel (not just "any class") so the type checker knows
# every ModelT has an `.id` column — required for get_by_id/exists below
# to type-check at all. Every concrete model (User, Document, ...)
# satisfies this bound since all of them inherit from BaseModel.
ModelT = TypeVar("ModelT", bound=BaseModel)


class BaseRepository(Generic[ModelT]):
    """The ~80% of persistence logic that's identical for every entity —
    get by ID, get all, create, update, delete, check existence — written
    once and parameterized by `model`. A subclass sets `model = User` (or
    whichever table it owns) and gets all six methods for free, then adds
    only the queries that are genuinely specific to that entity (see
    UserRepository.get_by_email, which has no generic equivalent).
    """

    model: type[ModelT]

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, id: uuid.UUID) -> ModelT | None:
        result = await self.db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_all(self) -> list[ModelT]:
        result = await self.db.execute(select(self.model))
        return list(result.scalars().all())

    async def create(self, **fields) -> ModelT:
        # flush(), not commit() — same rule as every repository before
        # this one: get_db() owns the transaction boundary, a repository
        # never decides when a transaction ends.
        instance = self.model(**fields)
        self.db.add(instance)
        await self.db.flush()
        return instance

    async def update(self, instance: ModelT, **fields) -> ModelT:
        for key, value in fields.items():
            setattr(instance, key, value)
        await self.db.flush()
        return instance

    async def delete(self, instance: ModelT) -> None:
        await self.db.delete(instance)
        await self.db.flush()

    async def exists(self, id: uuid.UUID) -> bool:
        return await self.get_by_id(id) is not None
