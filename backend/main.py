import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.routes import (
    ai_metrics,
    auth,
    chat,
    conversations,
    documents,
    health,
    metrics,
    root,
    status,
    users,
)
from core.config import settings
from core.database import engine
from core.logging import configure_logging, logger
from core.metrics import REQUEST_COUNT, REQUEST_DURATION_SECONDS
from core.request_context import get_request_id, get_user_id, set_request_id, set_user_id
from schemas.errors import ErrorResponse

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Everything before `yield` runs once, before the app accepts its
    first request. Everything after `yield` runs once, as the app shuts
    down — guaranteed to run even if shutdown is triggered by Ctrl+C or a
    container stop signal, which is what makes this the right place for
    cleanup rather than something a request handler could ever guarantee.

    core.database's `engine` already exists at import time (it's created
    at module scope, not lazily) — nothing here connects to Postgres for
    the first time. `engine.dispose()` on shutdown closes every pooled
    connection cleanly; skipping it risks leaving connections open on the
    Postgres server itself across repeated restarts during development.

    Redis still doesn't exist — that placeholder remains. The AI stack
    (embedding model, vector store, LLM) DOES exist now, but deliberately
    ISN'T constructed here: all three (api/dependencies.py's
    _embedding_model/_vector_store/_llm) are process-wide singletons
    built at import time, with the genuinely expensive part (real model
    weights) deferred to first real use, not app startup — see
    core/embeddings.py's and services/llm/local_provider.py's docstrings for why eager
    loading here would also mean every test run pays that cost.
    """
    logger.info("OpsMind backend starting up (environment=%s)", settings.environment)

    # Placeholder — Redis client connection (Phase: caching)

    yield

    logger.info("OpsMind backend shutting down")
    await engine.dispose()
    # Placeholder — Redis client disconnect (Phase: caching)


app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
    lifespan=lifespan,
)


@app.middleware("http")
async def add_process_time_and_log(request: Request, call_next):
    """Wraps every request, regardless of route — this is the difference
    from a per-route Depends(): a route has to opt in to a dependency, but
    every request passes through every registered middleware whether its
    route asked for it or not.

    Generates a fresh request ID BEFORE call_next(), stored in a
    ContextVar (core/request_context.py) rather than passed as a
    parameter — that's what lets get_current_user(), deep inside the
    dependency chain call_next() triggers, set the authenticated user's
    ID into the SAME context without this middleware needing to decode
    the JWT itself. ContextVars propagate correctly here because
    call_next() runs the rest of the app in the same async context, not
    a separate task — no explicit passing required.
    """
    request_id = str(uuid.uuid4())
    set_request_id(request_id)
    set_user_id(None)  # reset each request; get_current_user sets this on success

    start_time = time.perf_counter()
    response = await call_next(request)
    duration_seconds = time.perf_counter() - start_time

    response.headers["X-Process-Time"] = f"{duration_seconds:.4f}"
    response.headers["X-Request-ID"] = request_id
    # A lightweight, non-breaking form of API versioning — see this
    # phase's write-up on why a URL path prefix (/v1/...) wasn't
    # introduced: nothing in this API has had a breaking change yet, so
    # there's no "v2" to distinguish from. A response header at least
    # lets a client detect a future version bump without every route
    # needing a new URL.
    response.headers["X-API-Version"] = settings.app_version

    # Route TEMPLATE for metrics (see core/metrics.py's docstring on
    # cardinality), raw resolved path for the human-readable log line —
    # logs benefit from the real path/IDs for correlation; metrics would
    # explode in cardinality if they used it.
    route = request.scope.get("route")
    path_template = route.path if route is not None else request.url.path

    REQUEST_COUNT.labels(
        method=request.method, path=path_template, status_code=response.status_code
    ).inc()
    REQUEST_DURATION_SECONDS.labels(method=request.method, path=path_template).observe(
        duration_seconds
    )

    logger.info(
        "%s %s %s %.4fs",
        request.method,
        request.url.path,
        response.status_code,
        duration_seconds,
        extra={
            "request_id": request_id,
            "user_id": get_user_id(),
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration_seconds * 1000, 2),
        },
    )
    return response


# --- Standardized error responses ---
# Two handlers, covering the two ways an error reaches a client: routes
# raising HTTPException explicitly (auth failures, not-found, etc.), and
# FastAPI's own automatic request-validation errors (a malformed body,
# outside anything a route wrote itself). Both get reshaped into the
# SAME ErrorResponse envelope — before this phase, each route's
# HTTPException(detail=...) shape varied (a plain string in most places,
# a dict in a couple), and validation errors used FastAPI's own default
# shape entirely — three different formats a client had to handle.
_ERROR_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    413: "payload_too_large",
    422: "validation_error",
    429: "too_many_requests",
    500: "internal_error",
    501: "not_implemented",
    503: "service_unavailable",
}


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    # A few existing routes raise HTTPException(detail={"database": "..."})
    # — a dict, not a string. Rather than rewriting those call sites to
    # match a new schema, `message` just stringifies whatever detail is;
    # the error/request_id fields around it are what's actually new and
    # consistent.
    message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    body = ErrorResponse(
        error=_ERROR_CODES.get(exc.status_code, "error"),
        message=message,
        request_id=get_request_id(),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=body.model_dump(),
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    body = ErrorResponse(
        error="validation_error",
        message=str(exc.errors()),
        request_id=get_request_id(),
    )
    return JSONResponse(status_code=422, content=body.model_dump())


app.include_router(root.router)
app.include_router(health.router)
app.include_router(status.router)
app.include_router(metrics.router)
app.include_router(users.router)
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(conversations.router)
app.include_router(ai_metrics.router)
