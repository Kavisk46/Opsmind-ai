import time
import uuid
from contextlib import contextmanager
from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.metrics import DB_QUERY_DURATION_SECONDS
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

    Every method below records its duration to DB_QUERY_DURATION_SECONDS
    (core/metrics.py) — instrumenting HERE, once, is what gives every
    repository in this codebase query-duration metrics for free, the
    same "one lever moves everything" reasoning AIOrchestrator's own
    instrumentation already uses for AI requests. Repository-SPECIFIC
    queries (UserRepository.get_by_email, ConversationRepository.
    list_by_owner, ...) are NOT covered by this — each executes its own
    self.db.execute() directly, bypassing these methods entirely. Left
    uninstrumented deliberately: real, additional effort per repository,
    better applied once a specific slow custom query actually needs
    investigating than sprinkled everywhere speculatively.
    """

    model: type[ModelT]

    def __init__(self, db: AsyncSession):
        self.db = db

    @contextmanager
    def _timed(self, operation: str):
        """A plain (non-async) context manager wrapping code that awaits
        internally — timing here is pure bookkeeping around the await
        point, not async work itself, so it doesn't need to be an async
        context manager. `model=self.model.__name__` is what turns one
        histogram into a real per-entity breakdown (e.g. "are Document
        queries slower than User queries") without any per-repository
        setup.
        """
        start = time.perf_counter()
        try:
            yield
        finally:
            DB_QUERY_DURATION_SECONDS.labels(
                operation=operation, model=self.model.__name__
            ).observe(time.perf_counter() - start)

    async def get_by_id(self, id: uuid.UUID) -> ModelT | None:
        with self._timed("get_by_id"):
            result = await self.db.execute(select(self.model).where(self.model.id == id))
            return result.scalar_one_or_none()

    async def get_all(self) -> list[ModelT]:
        with self._timed("get_all"):
            result = await self.db.execute(select(self.model))
            return list(result.scalars().all())

    async def create(self, **fields) -> ModelT:
        # flush(), not commit() — same rule as every repository before
        # this one: get_db() owns the transaction boundary, a repository
        # never decides when a transaction ends.
        with self._timed("create"):
            instance = self.model(**fields)
            self.db.add(instance)
            await self.db.flush()
            return instance

    async def update(self, instance: ModelT, **fields) -> ModelT:
        with self._timed("update"):
            for key, value in fields.items():
                setattr(instance, key, value)
            await self.db.flush()
            return instance

    async def delete(self, instance: ModelT) -> None:
        with self._timed("delete"):
            await self.db.delete(instance)
            await self.db.flush()

    async def exists(self, id: uuid.UUID) -> bool:
        # Deliberately NOT wrapped in its own _timed("exists") block —
        # it delegates to get_by_id(), which already records itself
        # under "get_by_id". A second, nested timer here would double-
        # count the same query against two different operation labels
        # for what is, underneath, a single SELECT.
        return await self.get_by_id(id) is not None
