from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import settings

# One engine per process. SQLAlchemy pools connections internally, so this
# is created once at import time and reused across every request rather
# than opening a fresh connection per request.
engine = create_async_engine(settings.database_url)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db():
    """FastAPI dependency that yields a DB session scoped to one request.

    Routes ask for a session via `Depends(get_db)` instead of importing a
    module-level session directly. That indirection is what lets FastAPI
    guarantee the session is closed after the request finishes — even if
    the handler raises — and lets tests swap in a different session/database
    later without changing a single route's code.
    """
    async with async_session_factory() as session:
        yield session
