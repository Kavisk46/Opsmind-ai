import uuid

import jwt
from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.cookies import ACCESS_TOKEN_COOKIE_NAME
from core.database import async_session_factory, get_db
from core.embeddings import SentenceTransformerEmbeddingModel
from core.rate_limit import RateLimiter
from core.request_context import set_user_id
from core.security import decode_access_token
from core.storage import LocalStorage
from core.vector_store import VectorStore
from models.user import User, UserRole
from models.workspace import Workspace
from models.workspace_member import WorkspaceRole
from repositories.chunk_repository import ChunkRepository
from repositories.conversation_repository import ConversationRepository
from repositories.document_repository import DocumentRepository
from repositories.message_repository import MessageRepository
from repositories.user_repository import UserRepository
from repositories.workspace_member_repository import WorkspaceMemberRepository
from repositories.workspace_repository import WorkspaceRepository
from services.ai_metrics_service import AIMetricsService
from services.ask_service import AskService
from services.chat_service import ChatService
from services.citation_service import CitationService
from services.context_service import ContextService
from services.conversation_service import ConversationService
from services.document_service import DocumentService
from services.ingestion_service import IngestionService
from services.llm.factory import get_llm_provider
from services.llm.protocol import LLMProvider
from services.orchestrator import AIOrchestrator
from services.planner import Planner
from services.prompt_builder import PromptBuilder
from services.query_service import QueryService
from services.reranking_service import WeightedReranker
from services.retrieval_service import RetrievalService
from services.tool_registry import ToolRegistry
from services.tools import DocumentMetadataTool, RAGRetrievalTool
from services.workspace_service import (
    WorkspacePermission,
    WorkspaceService,
    has_permission,
)

# tokenUrl points Swagger UI's "Authorize" button at the login route (even
# though that route itself takes JSON, not the form-encoded body this
# class is named after) — this is purely a docs/UI hint, it doesn't change
# how OUR route parses requests. auto_error=False is what makes this
# optional rather than an automatic 401: a real browser request carries
# the access token in the httpOnly cookie (see core/cookies.py), not this
# header, so a MISSING header here is normal, not an error — get_current_user
# below is what decides whether the cookie fills the gap before actually
# failing.
_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


async def get_current_user(
    request: Request,
    header_token: str | None = Depends(_oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """The dependency every protected route will declare. Decodes and
    verifies an access token — from EITHER the httpOnly cookie a real
    browser sends automatically, or an `Authorization: Bearer` header (an
    API client, or this project's own test suite, which has always used
    the header and is left unchanged) — then loads the user it names. Any
    failure along the way — no token in either place, bad signature,
    expired token, user since deleted — collapses to the same 401; a
    caller doesn't get to distinguish one cause from another.

    Header checked first, purely for continuity with this project's
    existing tests/API-client usage; a real frontend request has only
    the cookie, so which one wins first never actually matters in
    practice — only one is ever present at a time.
    """
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = header_token or request.cookies.get(ACCESS_TOKEN_COOKIE_NAME)
    if token is None:
        raise credentials_error

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


async def get_current_workspace(
    workspace_id: uuid.UUID | None = Query(
        default=None,
        description=(
            "Which workspace to operate in. Omit to use the caller's "
            "default workspace (every user has one, auto-created at "
            "signup — see WorkspaceService.ensure_personal_workspace)."
        ),
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Workspace:
    """Resolves "which workspace is this request about" — a query
    parameter, not a path segment, deliberately: existing routes
    (/documents, /chat, /conversations) keep their exact paths and stay
    backward-compatible (the already-working frontend never sends
    workspace_id at all, so every one of its requests implicitly
    operates on the caller's default/personal workspace — see this
    phase's Change Summary for why that matters).

    Membership is verified here, once, for every route that depends on
    this — a resolved Workspace this function returns is always one the
    caller actually belongs to; 404, not 403, for the same anti-
    enumeration reason DocumentNotFoundError/WorkspaceNotFoundError use
    elsewhere in this codebase (a caller shouldn't be able to distinguish
    "doesn't exist" from "exists but you're not in it").
    """
    resolved_workspace_id = workspace_id or current_user.default_workspace_id
    if resolved_workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No workspace found."
        )

    membership = await WorkspaceMemberRepository(db).get_membership(
        workspace_id=resolved_workspace_id, user_id=current_user.id
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found."
        )

    workspace = await WorkspaceRepository(db).get_by_id(resolved_workspace_id)
    if workspace is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found."
        )
    return workspace


def require_workspace_permission(permission: WorkspacePermission):
    """A dependency FACTORY, same shape as require_role() above — one
    per permission needed at a given route (e.g.
    Depends(require_workspace_permission(WorkspacePermission.UPLOAD))).
    Layered on top of get_current_workspace (itself layered on
    get_current_user), so authentication -> membership -> permission are
    three separate, separately-testable checks, never conflated into one.

    Re-fetches the caller's membership row rather than having
    get_current_workspace hand it over directly — a small, accepted extra
    query, the same "small round-trip cost for a cleaner dependency
    graph" trade-off RAGRetrievalTool's per-chunk citation lookups and
    ConversationService.append_message's extra SELECT already make
    elsewhere in this codebase.
    """

    async def check_permission(
        current_user: User = Depends(get_current_user),
        workspace: Workspace = Depends(get_current_workspace),
        db: AsyncSession = Depends(get_db),
    ) -> Workspace:
        membership = await WorkspaceMemberRepository(db).get_membership(
            workspace_id=workspace.id, user_id=current_user.id
        )
        # Guaranteed non-None: get_current_workspace already verified this
        # exact membership exists moments ago in the same request.
        assert membership is not None
        if not has_permission(WorkspaceRole(membership.role), permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action in this workspace.",
            )
        return workspace

    return check_permission


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
# A SEPARATE PromptBuilder instance, not _prompt_builder above — chat_
# prompt_version is fixed at construction time, and AskService (services/
# ask_service.py) uses a different system prompt ("ask_v1") than /chat's
# "v1" without touching what /chat already sends. Both instances are
# stateless (see PromptBuilder's own docstring), so a second one costs
# nothing beyond the object itself.
_ask_prompt_builder = PromptBuilder(chat_prompt_version="ask_v1")

# Process-wide, same reasoning as _storage: state (the login-attempt
# counts) genuinely needs to persist across requests for the whole
# process's lifetime for a rate limiter to mean anything. See
# core/rate_limit.py's docstring for why this is in-memory, not Redis,
# at this project's current scale.
_login_rate_limiter = RateLimiter(max_requests=5, window_seconds=60)

# A SEPARATE instance, not the same one login uses — signup and login
# are different actions with different abuse profiles (mass account
# creation vs. credential brute-forcing); sharing one counter would mean
# a burst of one silently ate into the other's budget. A little more
# generous than login's 5/60s: signup is a normal, non-suspicious action
# most callers only need once, but with zero limit before this phase,
# nothing stood between a script and mass account creation — each one
# also paying a real bcrypt hash, the same CPU-cost concern this
# project's own performance-testing phase already found and fixed for
# the event-loop-blocking case (see services/user_service.py).
_signup_rate_limiter = RateLimiter(max_requests=10, window_seconds=60)

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


async def get_signup_rate_limiter() -> RateLimiter:
    return _signup_rate_limiter


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
        chunk_repository=ChunkRepository(db),
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
        embedding_model_name=settings.embedding_model_name,
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


async def get_workspace_service(db: AsyncSession = Depends(get_db)) -> WorkspaceService:
    return WorkspaceService(db)


async def get_conversation_service(
    db: AsyncSession = Depends(get_db),
) -> ConversationService:
    return ConversationService(
        ConversationRepository(db),
        MessageRepository(db),
        max_history_tokens=settings.max_history_tokens,
    )


async def get_retrieval_service(
    db: AsyncSession = Depends(get_db),
) -> RetrievalService:
    # Shared by both get_chat_service (below) and the standalone
    # /retrieval/search route (api/routes/retrieval.py) — one construction,
    # reused, rather than the two duplicating this wiring independently.
    # WeightedReranker (services/reranking_service.py) is today's
    # Reranker implementation; a future cross-encoder/Cohere/BGE reranker
    # would only need to change what's constructed HERE, never any caller.
    return RetrievalService(
        embedding_model=_embedding_model,
        vector_store=_vector_store,
        chunk_repository=ChunkRepository(db),
        document_repository=DocumentRepository(db),
        reranker=WeightedReranker(
            vector_weight=settings.retrieval_vector_weight,
            keyword_weight=settings.retrieval_keyword_weight,
        ),
    )


async def get_query_service() -> QueryService:
    return QueryService()


async def get_context_service() -> ContextService:
    return ContextService()


async def get_citation_service() -> CitationService:
    return CitationService()


async def get_chat_service(
    db: AsyncSession = Depends(get_db),
    conversation_service: ConversationService = Depends(get_conversation_service),
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
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
    # builds fresh every request rather than caching one. retrieval_service
    # comes from get_retrieval_service via Depends() rather than being
    # constructed inline here — same object either way, just centralized.
    # RAGRetrievalTool now calls retrieve_hybrid() (the same hybrid
    # engine /retrieval/search uses), not the old vector-only retrieve()
    # — see this phase's Change Summary for why chat was upgraded rather
    # than left on the old path.
    document_repository = DocumentRepository(db)
    user_repository = UserRepository(db)

    tool_registry = ToolRegistry()
    tool_registry.register(
        RAGRetrievalTool(
            retrieval_service=retrieval_service,
            query_service=QueryService(),
            context_service=ContextService(),
            citation_service=CitationService(),
            top_k=settings.retrieval_top_k,
            max_returned_chunks=settings.retrieval_max_returned_chunks,
            max_context_tokens=settings.retrieval_max_context_tokens,
        )
    )
    tool_registry.register(
        DocumentMetadataTool(
            document_repository=document_repository, user_repository=user_repository
        )
    )

    orchestrator = AIOrchestrator(
        tool_registry=tool_registry,
        prompt_builder=_prompt_builder,
        llm=_llm,
        metrics_service=_ai_metrics_service,
        provider_name=settings.llm_provider,
        model_name=settings.llm_model_name,
    )
    return ChatService(conversation_service, orchestrator=orchestrator)


async def get_ask_service(
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
) -> AskService:
    # Planner/ContextService/CitationService are all stateless (no I/O,
    # no per-request session) — built fresh per request the same way
    # get_chat_service already builds its own ContextService/
    # CitationService instances, rather than adding more process-wide
    # singletons for objects this cheap to construct.
    return AskService(
        Planner(),
        retrieval_service,
        ContextService(),
        _ask_prompt_builder,
        CitationService(),
        _llm,
        max_context_tokens=settings.retrieval_max_context_tokens,
        max_returned_chunks=settings.retrieval_max_returned_chunks,
    )
