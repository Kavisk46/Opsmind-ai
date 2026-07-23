"""Standalone server for Phase T6 (Performance, Load, and Reliability
Testing) — deliberately NOT part of the pytest suite. pytest.ini's
testpaths=tests never discovers this directory, and it couldn't be a
pytest fixture regardless: Locust needs a real, persistently-running HTTP
process to send requests to, and a pytest TestClient only exists for the
lifetime of a single test function.

Wires the exact same KIND of fakes tests/conftest.py's `client` fixture
uses (a fake embedding model, a fake LLM) via the same
app.dependency_overrides mechanism — deliberately, per this phase's Step
3 instruction to "use fake AI dependencies... to isolate backend
performance." A load test's whole point here is measuring THIS
backend's own overhead (auth, routing, DB queries, request/response
serialization) — a real LLM call would dominate every latency number
and tell you nothing about this codebase's own performance.

Fakes are re-defined here rather than imported from tests/conftest.py —
a small, deliberate amount of duplication (two ~10-line classes) instead
of importing test infrastructure into a standalone script, or
refactoring conftest.py's fakes into a new shared module for a single
second caller. If a THIRD caller ever needs these same fakes, that's the
point to extract a shared tests/fakes.py-style module — not before.

Database: a real FILE-based SQLite database (not in-memory, not
StaticPool) — a load test needs schema and data to survive across many
real HTTP requests handled by a real running process, unlike a single
pytest function's lifetime. Built with the SAME pool_size/max_overflow
settings production actually uses (core/config.py), specifically so
this phase's "database connection usage" measurements are directly
comparable to what a real deployment would configure — even though the
underlying engine is SQLite, not Postgres (Docker/Postgres remain
unavailable in this development environment, the same constraint noted
throughout this project).

Usage:
    python scripts/perf_server.py [--port 8001]
"""

import argparse
import tempfile

import uvicorn
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import AsyncAdaptedQueuePool

from api.dependencies import (
    get_ai_metrics_service,
    get_chat_service,
    get_conversation_service,
    get_document_service,
    get_ingestion_service,
    get_login_rate_limiter,
    get_session_factory,
)
from core.config import settings
from core.database import get_db
from core.rate_limit import RateLimiter
from core.storage import LocalStorage
from core.vector_store import VectorStore
from main import app
from models.base import Base

# Every model must be imported for Base.metadata to know about its table
# — identical reasoning to tests/conftest.py and alembic/env.py's own
# comments on this exact requirement.
from models.conversation import Conversation  # noqa: F401
from models.document import Document  # noqa: F401
from models.message import Message  # noqa: F401
from models.team import Team  # noqa: F401
from models.user import User  # noqa: F401
from repositories.conversation_repository import ConversationRepository
from repositories.document_repository import DocumentRepository
from repositories.message_repository import MessageRepository
from services.ai_metrics_service import AIMetricsService
from services.chat_service import ChatService
from services.conversation_service import ConversationService
from services.document_service import DocumentService
from services.ingestion_service import IngestionService
from services.orchestrator import AIOrchestrator
from services.prompt_builder import PromptBuilder
from services.retrieval_service import RetrievalService
from services.tool_registry import ToolRegistry
from services.tools import DocumentMetadataTool, RAGRetrievalTool


class FakeEmbeddingModel:
    """Same scheme as tests/conftest.py's — deterministic and instant,
    never a real network call or model download."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(text) % 7) + 1.0] * 8 for text in texts]


class FakeLLM:
    """Same scheme as tests/conftest.py's — a fixed-latency-free,
    fixed-text response, so every measured millisecond in this load test
    is this backend's own overhead, never a real model's generation
    time."""

    @property
    def is_loaded(self) -> bool:
        return True

    async def generate(self, prompt: str):
        from services.llm.protocol import LLMResponse

        return LLMResponse(text="This is a fake answer for load testing.")

    async def generate_stream(self, prompt: str):
        for word in ["This ", "is ", "a ", "fake ", "streamed ", "answer."]:
            yield word


def build_app(db_path: str, storage_dir: str, chroma_dir: str):
    # aiosqlite's dialect defaults to NullPool (verified directly: passing
    # pool_size/max_overflow without this raises TypeError, since NullPool
    # doesn't accept either) — poolclass must be requested explicitly to
    # get a real, sized connection pool whose usage is actually
    # comparable to what production (a real QueuePool against Postgres)
    # would report.
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        poolclass=AsyncAdaptedQueuePool,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    storage = LocalStorage(storage_dir)
    vector_store = VectorStore(chroma_dir)
    embedding_model = FakeEmbeddingModel()
    llm = FakeLLM()
    prompt_builder = PromptBuilder(max_history_messages=settings.max_history_messages)
    login_rate_limiter = RateLimiter(max_requests=10_000, window_seconds=60)
    ai_metrics_service = AIMetricsService()

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
                    session, storage=storage,
                    max_size_bytes=settings.max_upload_size_bytes,
                    vector_store=vector_store,
                )
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def override_get_ingestion_service() -> IngestionService:
        return IngestionService(
            session_factory=session_factory, storage=storage,
            embedding_model=embedding_model, vector_store=vector_store,
            chunk_size=settings.chunk_size_chars, chunk_overlap=settings.chunk_overlap_chars,
        )

    async def override_get_conversation_service():
        async with session_factory() as session:
            try:
                yield ConversationService(
                    ConversationRepository(session), MessageRepository(session),
                    max_history_tokens=settings.max_history_tokens,
                )
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def override_get_chat_service():
        async with session_factory() as session:
            try:
                document_repository = DocumentRepository(session)
                retrieval_service = RetrievalService(
                    embedding_model=embedding_model, vector_store=vector_store
                )
                tool_registry = ToolRegistry()
                tool_registry.register(
                    RAGRetrievalTool(
                        retrieval_service=retrieval_service,
                        document_repository=document_repository,
                        top_k=settings.retrieval_top_k,
                    )
                )
                tool_registry.register(
                    DocumentMetadataTool(document_repository=document_repository)
                )
                orchestrator = AIOrchestrator(
                    tool_registry=tool_registry, prompt_builder=prompt_builder, llm=llm,
                    metrics_service=ai_metrics_service, provider_name="fake", model_name="fake-model",
                )
                conversation_service = ConversationService(
                    ConversationRepository(session), MessageRepository(session),
                    max_history_tokens=settings.max_history_tokens,
                )
                yield ChatService(conversation_service, orchestrator=orchestrator)
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def override_get_login_rate_limiter() -> RateLimiter:
        return login_rate_limiter

    async def override_get_session_factory():
        return session_factory

    async def override_get_ai_metrics_service() -> AIMetricsService:
        return ai_metrics_service

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_document_service] = override_get_document_service
    app.dependency_overrides[get_ingestion_service] = override_get_ingestion_service
    app.dependency_overrides[get_conversation_service] = override_get_conversation_service
    app.dependency_overrides[get_chat_service] = override_get_chat_service
    app.dependency_overrides[get_login_rate_limiter] = override_get_login_rate_limiter
    app.dependency_overrides[get_session_factory] = override_get_session_factory
    app.dependency_overrides[get_ai_metrics_service] = override_get_ai_metrics_service

    return app, engine


async def _create_schema(engine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    import asyncio

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()

    db_dir = tempfile.mkdtemp(prefix="opsmind_perf_db_")
    storage_dir = tempfile.mkdtemp(prefix="opsmind_perf_storage_")
    chroma_dir = tempfile.mkdtemp(prefix="opsmind_perf_chroma_")
    db_path = f"{db_dir}/perf.db"

    fastapi_app, engine = build_app(db_path, storage_dir, chroma_dir)
    asyncio.run(_create_schema(engine))

    print(f"Perf server: db={db_path} storage={storage_dir} chroma={chroma_dir}")
    uvicorn.run(fastapi_app, host="127.0.0.1", port=args.port, log_level="warning")
