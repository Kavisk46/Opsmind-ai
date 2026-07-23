import uuid

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import async_session_factory, get_db
from core.embeddings import SentenceTransformerEmbeddingModel
from core.rate_limit import RateLimiter
from core.request_context import set_user_id
from core.security import decode_access_token
from core.storage import LocalStorage
from core.vector_store import VectorStore
from models.user import User, UserRole
from repositories.conversation_repository import ConversationRepository
from repositories.document_repository import DocumentRepository
from repositories.message_repository import MessageRepository
from repositories.user_repository import UserRepository
from services.ai_metrics_service import AIMetricsService
from services.chat_service import ChatService
from services.conversation_service import ConversationService
from services.document_service import DocumentService
from services.ingestion_service import IngestionService
from services.llm.factory import get_llm_provider
from services.llm.protocol import LLMProvider
from services.orchestrator import AIOrchestrator
from services.prompt_builder import PromptBuilder
from services.retrieval_service import RetrievalService
from services.tool_registry import ToolRegistry
from services.tools import DocumentMetadataTool, RAGRetrievalTool

# tokenUrl points Swagger UI's "Authorize" button at the login route (even
# though that route itself takes JSON, not the form-encoded body this
# class is named after) — this is purely a docs/UI hint, it doesn't change
# how OUR route parses requests. FastAPI also uses this to extract the
# `Authorization: Bearer <token>` header automatically, which is the part
# that actually matters here.
_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    token: str = Depends(_oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """The dependency every protected route will declare. Decodes and
    verifies the bearer token, then loads the user it names. Any failure
    along the way — bad signature, expired token, user since deleted —
    collapses to the same 401; a caller doesn't get to distinguish "your
    token is malformed" from "that user doesn't exist anymore."
    """
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        subject = decode_access_token(token)
        user_id = uuid.UUID(subject)
    except (jwt.PyJWTError, ValueError) as error:
        raise credentials_error from error

    user = await UserRepository(db).get_by_id(user_id)
    if user is None:
        raise credentials_error

    # Set once authentication actually succeeds — read back by the
    # request-logging middleware AFTER call_next() returns, so the
    # per-request log line includes who made the request without the
    # middleware needing to decode the JWT itself (that would duplicate
    # this exact logic in a second place).
    set_user_id(str(user.id))

    return user


def require_role(*allowed_roles: UserRole):
    """A dependency FACTORY, not a dependency — calling require_role(...)
    returns a new async function shaped like any other dependency, closed
    over `allowed_roles`. This is why routes write
    `Depends(require_role(UserRole.ADMIN))` with the call included, unlike
    `Depends(get_current_user)` which passes the function itself: there's
    no single "require_role" dependency, only ones parameterized per call
    site.

    Deliberately layered ON TOP of get_current_user (via its own
    Depends()) rather than duplicating token decoding — authentication
    (who are you) stays fully separate from authorization (are you
    allowed), exactly per Step 1's distinction. 403, not 401: the caller
    IS authenticated (get_current_user already succeeded) — they're
    correctly identified and still not permitted, which is what 403
    specifically means.
    """

    async def check_role(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in {role.value for role in allowed_roles}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )
        return current_user

    return check_role


# One process-wide LocalStorage instance — it's stateless aside from the
# directory path, so there's no reason to build a new one per request the
# way get_document_service() below builds a fresh DocumentService per
# request (that one wraps a per-request AsyncSession, which can't be
# shared).
_storage = LocalStorage(settings.storage_dir)


# Also process-wide singletons, same reasoning as _storage above.
# SentenceTransformerEmbeddingModel's constructor is cheap (it only
# remembers the model name — see core/embeddings.py's docstring for why
# real weight-loading is deferred to first use, not done here at import
# time). VectorStore's constructor opens/creates a local Chroma index —
# real disk I/O, but no network call and no ML model loading, so doing it
# eagerly at import time is fine (identical reasoning to _storage
# creating its directory eagerly).
_embedding_model = SentenceTransformerEmbeddingModel(settings.embedding_model_name)
_vector_store = VectorStore(settings.chroma_persist_dir)

# Built via the factory (services/llm/factory.py), which reads
# settings.llm_provider to decide which concrete provider class this
# actually is — "local" by default (see core/config.py), so this remains
# free/no-API-key/no-external-dependency unless explicitly reconfigured.
# Same lazy-construction reasoning as _embedding_model regardless of
# which provider this resolves to: cheap to construct, real cost (a
# model load or a real API call) deferred to first .generate() call.
_llm = get_llm_provider(settings)
_prompt_builder = PromptBuilder(max_history_messages=settings.max_history_messages)

# Process-wide, same reasoning as _storage: state (the login-attempt
# counts) genuinely needs to persist across requests for the whole
# process's lifetime for a rate limiter to mean anything. See
# core/rate_limit.py's docstring for why this is in-memory, not Redis,
# at this project's current scale.
_login_rate_limiter = RateLimiter(max_requests=5, window_seconds=60)

# Process-wide, same reasoning as _login_rate_limiter: AIMetricsService's
# in-memory history and running aggregates (see its docstring) only mean
# anything if every request accumulates into the SAME instance, not a
# fresh one per request.
_ai_metrics_service = AIMetricsService()


async def get_vector_store() -> VectorStore:
    return _vector_store


async def get_session_factory():
    # Exists so streaming routes (which must open a FRESH session inside
    # their generator, after the request's own Depends(get_db) session
    # has already started closing — see api/routes/chat.py) get that
    # factory through Depends() rather than importing
    # core.database.async_session_factory directly. The import would be
    # invisible to tests: app.dependency_overrides can only intercept
    # something requested via Depends(), which is exactly the bug this
    # phase caught (the streaming route's finally-block persistence was
    # silently trying to hit real Postgres in every test, because nothing
    # let tests substitute the SQLite factory in its place).
    return async_session_factory


async def get_llm() -> LLMProvider:
    return _llm


async def get_login_rate_limiter() -> RateLimiter:
    return _login_rate_limiter


async def get_ai_metrics_service() -> AIMetricsService:
    return _ai_metrics_service


async def get_document_service(
    db: AsyncSession = Depends(get_db),
) -> DocumentService:
    return DocumentService(
        db,
        storage=_storage,
        max_size_bytes=settings.max_upload_size_bytes,
        vector_store=_vector_store,
    )


async def get_ingestion_service() -> IngestionService:
    # Takes the session FACTORY, not a per-request session — see
    # IngestionService's docstring for why: it runs as a background task,
    # after this request has already returned, and manages its own
    # transactions rather than sharing this request's.
    return IngestionService(
        session_factory=async_session_factory,
        storage=_storage,
        embedding_model=_embedding_model,
        vector_store=_vector_store,
        chunk_size=settings.chunk_size_chars,
        chunk_overlap=settings.chunk_overlap_chars,
    )


# Repository-level dependencies, distinct from get_document_service above.
# Most routes should keep depending on a *service* (business rules live
# there) — these exist for callers that genuinely only need persistence
# with no business rules attached: an admin/reporting route, a future
# script, or a Phase 5 auth flow that needs to look a user up directly
# without going through signup/login's specific rules. Both follow the
# exact same shape as get_document_service: build the repository from a
# per-request session, fresh every request, never shared/cached.
async def get_user_repository(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


async def get_document_repository(
    db: AsyncSession = Depends(get_db),
) -> DocumentRepository:
    return DocumentRepository(db)


async def get_conversation_service(
    db: AsyncSession = Depends(get_db),
) -> ConversationService:
    return ConversationService(
        ConversationRepository(db),
        MessageRepository(db),
        max_history_tokens=settings.max_history_tokens,
    )


async def get_chat_service(
    db: AsyncSession = Depends(get_db),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ChatService:
    # Unlike get_ingestion_service, this takes a live per-request session,
    # not a session factory — chat runs synchronously within the
    # request/response cycle (no BackgroundTasks involved), so it can
    # safely share get_db()'s transaction like every other request-scoped
    # service in this codebase.
    #
    # Tools/registry/orchestrator are built fresh per request (unlike
    # _embedding_model/_vector_store/_llm, which are process-wide
    # singletons) because they wrap a DocumentRepository bound to THIS
    # request's session — the same reason get_document_repository below
    # builds fresh every request rather than caching one.
    document_repository = DocumentRepository(db)
    retrieval_service = RetrievalService(
        embedding_model=_embedding_model, vector_store=_vector_store
    )

    tool_registry = ToolRegistry()
    tool_registry.register(
        RAGRetrievalTool(
            retrieval_service=retrieval_service,
            document_repository=document_repository,
            top_k=settings.retrieval_top_k,
        )
    )
    tool_registry.register(DocumentMetadataTool(document_repository=document_repository))

    orchestrator = AIOrchestrator(
        tool_registry=tool_registry,
        prompt_builder=_prompt_builder,
        llm=_llm,
        metrics_service=_ai_metrics_service,
        provider_name=settings.llm_provider,
        model_name=settings.llm_model_name,
    )
    return ChatService(conversation_service, orchestrator=orchestrator)
