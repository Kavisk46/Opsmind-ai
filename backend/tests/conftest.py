import asyncio
import shutil
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from api.dependencies import get_document_service
from core.database import get_db
from core.storage import LocalStorage
from main import app
from models.base import Base

# Importing every model — not just the ones the app currently wires into a
# route — is what registers each table onto Base.metadata (see
# alembic/env.py's identical comment). Without this, Base.metadata.create_all()
# below would only build tables for models something else happened to
# import already, and any foreign key pointing at an unimported model's
# table (e.g. User.team_id -> teams) would fail with NoReferencedTableError.
from models.conversation import Conversation  # noqa: F401
from models.document import Document  # noqa: F401
from models.message import Message  # noqa: F401
from models.team import Team  # noqa: F401
from models.user import User  # noqa: F401
from services.document_service import DocumentService


@pytest.fixture()
def client():
    """A TestClient wired to an in-memory SQLite database and a temp-directory
    Storage backend, instead of the real Postgres DB and local storage
    directory — fast, isolated, and needs no Docker (which isn't available
    in this environment; see the Phase 1/3 write-ups). The overridden
    get_db still commits on success / rolls back on exception, matching
    production exactly, so a regression like Phase 3's missing commit
    would still be caught by tests using this fixture.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def init_models() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    asyncio.run(init_models())

    storage_dir = tempfile.mkdtemp()
    storage = LocalStorage(storage_dir)

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def override_get_document_service():
        async with session_factory() as session:
            try:
                yield DocumentService(
                    session, storage=storage, max_size_bytes=20 * 1024 * 1024
                )
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_document_service] = override_get_document_service

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())
    shutil.rmtree(storage_dir, ignore_errors=True)
