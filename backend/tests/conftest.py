import asyncio
import shutil
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from api.dependencies import (
    get_ai_metrics_service,
    get_chat_service,
    get_conversation_service,
    get_document_service,
    get_ingestion_service,
    get_login_rate_limiter,
    get_session_factory,
)
from core.database import get_db
from core.rate_limit import RateLimiter
from core.storage import LocalStorage
from core.vector_store import VectorStore
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
from repositories.conversation_repository import ConversationRepository
from repositories.document_repository import DocumentRepository
from repositories.message_repository import MessageRepository
from repositories.user_repository import UserRepository
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
    """Deterministic, instant, network-free stand-in for
    SentenceTransformerEmbeddingModel — same reasoning as using SQLite for
    Postgres and a temp-dir LocalStorage for real storage: fake only the
    one genuinely expensive/external piece (downloading and running a
    real ML model), keep everything downstream of it (chunking, ChromaDB
    storage, status transitions) real. The vector's exact values never
    matter to any test — only that embed() returns one fixed-length
    vector per input text.

    `+ 1.0` matters here, not just cosmetically: the vector store's
    ChromaDB collection uses cosine distance, which divides by each
    vector's norm — a text whose length happens to be a multiple of 7
    (e.g. "What does OpsMind do?", 21 characters) would otherwise produce
    an all-zero vector, undefined under cosine similarity. This isn't
    hypothetical; it's the exact input the RAG phase's chat tests use.
    """

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(text) % 7) + 1.0] * 8 for text in texts]


class FakeLLM:
    """Deterministic, instant, network-free stand-in for any real
    LLMProvider (local, OpenAI, etc.) — same reasoning as
    FakeEmbeddingModel above: real text generation is slow and depends on
    a downloaded model or a network call, so tests fake only that one
    piece. last_prompt is exposed so a test can assert the ASSEMBLED
    prompt actually contains retrieved context, without needing a real
    provider to prove PromptBuilder did its job. Satisfies the
    LLMProvider protocol structurally — async generate() returning an
    LLMResponse, an is_loaded property — without importing anything from
    services/llm at all, proof that a fake needs to match only the
    Protocol's shape, not inherit from anything real.
    """

    def __init__(self):
        self.last_prompt: str | None = None

    @property
    def is_loaded(self) -> bool:
        return True

    async def generate(self, prompt: str):
        from services.llm.protocol import LLMResponse

        self.last_prompt = prompt
        return LLMResponse(text="This is a fake answer for testing.")

    async def generate_stream(self, prompt: str):
        # Multiple chunks, not one — real proof a test using this can
        # distinguish "streaming actually happened incrementally" from
        # "the whole answer arrived as a single chunk" (see
        # tests/test_chat_streaming.py).
        self.last_prompt = prompt
        for word in ["This ", "is ", "a ", "fake ", "streamed ", "answer."]:
            yield word


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

    chroma_dir = tempfile.mkdtemp()
    vector_store = VectorStore(chroma_dir)
    embedding_model = FakeEmbeddingModel()
    fake_llm = FakeLLM()
    # Built ONCE per test (not per request) and captured by closure below
    # — the override function must return the SAME instance across every
    # request within one test (so hit counts actually accumulate and a
    # 6th rapid login attempt can trip the limit), while still being a
    # brand new, empty-count instance for the NEXT test.
    login_rate_limiter = RateLimiter(max_requests=5, window_seconds=60)
    # Same "one instance per test, shared across every request in it"
    # reasoning as login_rate_limiter — AIMetricsService's in-memory
    # aggregates would be meaningless if a fresh, empty instance were
    # built per request instead of accumulating across a whole test.
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
                    session,
                    storage=storage,
                    max_size_bytes=20 * 1024 * 1024,
                    vector_store=vector_store,
                )
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def override_get_ingestion_service() -> IngestionService:
        return IngestionService(
            session_factory=session_factory,
            storage=storage,
            embedding_model=embedding_model,
            vector_store=vector_store,
            chunk_size=1000,
            chunk_overlap=200,
        )

    async def override_get_conversation_service():
        async with session_factory() as session:
            try:
                yield ConversationService(
                    ConversationRepository(session),
                    MessageRepository(session),
                    max_history_tokens=2000,
                )
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def override_get_chat_service():
        # Matches override_get_document_service's pattern above: manages
        # its own session from session_factory directly rather than
        # depending on the (also-overridden) get_db, to stay consistent
        # with how every other overridden service-with-a-session is wired
        # in this fixture. Builds the same tool registry + orchestrator
        # shape as production (api/dependencies.py's get_chat_service),
        # just with the fake embedding model/LLM instead of real ones.
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
                        top_k=5,
                    )
                )
                tool_registry.register(
                    DocumentMetadataTool(document_repository=document_repository)
                )

                orchestrator = AIOrchestrator(
                    tool_registry=tool_registry,
                    prompt_builder=PromptBuilder(),
                    llm=fake_llm,
                    metrics_service=ai_metrics_service,
                    provider_name="fake",
                    model_name="fake-model",
                )
                conversation_service = ConversationService(
                    ConversationRepository(session),
                    MessageRepository(session),
                    max_history_tokens=2000,
                )
                yield ChatService(conversation_service, orchestrator=orchestrator)
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    # A FRESH RateLimiter per test — TestClient sends every request from
    # the same fake client host ("testclient"), so without this override,
    # the production singleton's hit-count would accumulate ACROSS
    # different test functions in the same pytest run, eventually
    # 429-ing tests that have nothing to do with rate limiting at all.
    # Matches how every other stateful singleton (storage, vector_store,
    # embedding_model) already gets a fresh, isolated instance per test.
    async def override_get_login_rate_limiter() -> RateLimiter:
        return login_rate_limiter

    # Real bug, caught by running the streaming tests: the streaming
    # route needs a session factory usable from INSIDE its generator,
    # after the request has already returned (see api/routes/chat.py's
    # _stream_chat_response). It gets one via Depends(get_session_factory)
    # specifically so this override can hand it the SQLite factory —
    # without this, it would silently fall back to the real
    # (unreachable, in this environment) Postgres factory instead.
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

    with TestClient(app) as test_client:
        # Exposed so tests can set up state the public API deliberately
        # can't create itself — e.g. an admin user. Signup has no `role`
        # field on purpose (self-service admin creation would be a real
        # vulnerability); tests that need an admin insert one directly.
        test_client.session_factory = session_factory
        # Exposed so tests can assert on real filesystem state (e.g. "the
        # file is actually gone after DELETE"), not just on the API's
        # response — the storage layer is a real dependency being tested,
        # not a mock standing in for one.
        test_client.storage_dir = storage_dir
        # Exposed so tests can assert on real ChromaDB state (e.g. "chunks
        # were actually indexed", "vectors were actually removed on
        # delete") — a real Chroma collection, just pointed at a temp dir
        # and fed fake vectors instead of real ones.
        test_client.vector_store = vector_store
        # Exposed so a test can assert the ASSEMBLED prompt actually
        # contains retrieved context/history — real proof PromptBuilder
        # and RetrievalService did their jobs, without needing a real LLM.
        test_client.fake_llm = fake_llm
        # Exposed so a test can assert on recorded AI metrics directly
        # (e.g. after hitting /chat) without needing to go through the
        # admin-only /internal/ai-metrics endpoint for every assertion.
        test_client.ai_metrics_service = ai_metrics_service
        yield test_client

    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())
    shutil.rmtree(storage_dir, ignore_errors=True)
    shutil.rmtree(chroma_dir, ignore_errors=True)


@pytest.fixture()
def auth_headers(client):
    """A FACTORY fixture — requesting `auth_headers` hands a test a
    FUNCTION, not a fixed dict, because different tests need different
    numbers of distinct logged-in users (a single caller vs. two owners
    proving cross-user isolation, e.g. test_chat_with_another_users_
    conversation_returns_404). A plain value fixture could only ever
    hand back one pre-built result per test; a factory fixture can be
    called as many times as a test needs, each call producing a genuinely
    different registered-and-logged-in user.

    Replaces an identical `_auth_headers(client, email=...)` helper
    function that used to be copy-pasted, nearly verbatim, across seven
    separate test files (test_chat.py, test_chat_streaming.py,
    test_conversations.py, test_documents.py, test_ingestion.py,
    test_observability.py, test_ai_metrics_endpoint.py) — seven copies
    that could silently drift out of sync (e.g. one gets updated to
    match a signup-flow change and the other six don't, and nothing
    would catch that until one of them started failing for a confusing
    reason). One definition now, reused everywhere.
    """

    def _make(email: str = "test-user@example.com", name: str = "Test User") -> dict:
        client.post(
            "/users", json={"email": email, "name": name, "password": "secret123"}
        )
        response = client.post(
            "/auth/login", json={"email": email, "password": "secret123"}
        )
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _make


# --- Repository-level fixtures (Phase T4: Database Integration Testing) ---
#
# Deliberately separate from `client` above, not built on top of it —
# repository tests exercise persistence directly (a repository, a real
# session, a real in-memory database) with no FastAPI app, no HTTP layer,
# no dependency_overrides involved at all. Reusing `client`'s heavier
# machinery (TestClient, storage dirs, ChromaDB, fake LLM) for a test that
# only needs "give me a session against a fresh database" would be
# pulling in a great deal of unrelated setup cost for no benefit.


@pytest.fixture()
def db_engine():
    """A fresh, empty in-memory SQLite engine — one per test function,
    thrown away afterward. This is the SAME isolation strategy `client`
    already uses (a brand-new database per test, rather than one shared
    database with each test's changes rolled back in a transaction
    afterward) — see this phase's write-up for why that simpler strategy
    is a deliberate, sufficient choice at this project's scale rather
    than a corner cut.

    PRAGMA foreign_keys=ON is enabled explicitly via a connect-time
    listener: SQLite does NOT enforce foreign key constraints by default
    (unlike Postgres, which always does) — without this, a test proving
    a foreign-key violation is rejected would silently pass for the
    wrong reason (nothing was ever enforcing it), which is worse than no
    test at all. `client`'s own engine does not enable this — a real,
    pre-existing gap this phase's audit surfaced, called out rather than
    silently fixed there (see the Step 2 review for why it's left alone
    for now).
    """
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def _enable_foreign_keys(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async def _create_schema() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    asyncio.run(_create_schema())
    yield engine
    asyncio.run(engine.dispose())


@pytest.fixture()
def db_session(db_engine):
    """One real AsyncSession per test, bound to db_engine above. Handed
    to repository tests directly — no service layer, no route, nothing
    between the test and the actual SQL a repository method generates.

    Constructing an AsyncSession is itself synchronous (no I/O happens
    until a query is actually awaited), which is what lets this be a
    plain `def` fixture instead of needing pytest-asyncio — exactly the
    same reasoning `client` already relies on. Test functions that use
    this fixture drive it with `asyncio.run(...)` per call, matching
    every other async-touching test in this suite (see
    tests/test_conversation_service.py).
    """
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    session = session_factory()
    yield session
    asyncio.run(session.close())


@pytest.fixture()
def user_repository(db_session):
    return UserRepository(db_session)


@pytest.fixture()
def document_repository(db_session):
    return DocumentRepository(db_session)


@pytest.fixture()
def conversation_repository(db_session):
    return ConversationRepository(db_session)


@pytest.fixture()
def message_repository(db_session):
    return MessageRepository(db_session)
