import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
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
from core.config import INSECURE_DEFAULT_SECRET_KEY, settings
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
    # Fail fast and loud, not silently — a hardcoded, world-readable
    # default secret signing every JWT this process issues is the single
    # highest-impact misconfiguration this app could run with (see
    # core/config.py's INSECURE_DEFAULT_SECRET_KEY docstring). Refusing
    # to start is deliberately stronger than a log warning: a warning is
    # easy to miss in a wall of startup output; a crashed container that
    # never becomes ready is impossible to miss.
    if (
        settings.environment != "development"
        and settings.secret_key == INSECURE_DEFAULT_SECRET_KEY
    ):
        raise RuntimeError(
            "settings.secret_key is still the insecure development default "
            f"outside environment='development' (current environment: "
            f"{settings.environment!r}). Set a real SECRET_KEY before starting."
        )

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

# Without this, a browser running the frontend at a DIFFERENT origin
# (http://localhost:3000, per docker-compose.yml) than this API
# (http://localhost:8000) would have every cross-origin fetch() blocked
# by the browser's own same-origin policy before the request's response
# ever reached the frontend's JavaScript — CORS headers are what tell
# the BROWSER "this other origin is allowed to read this response," a
# server-side allowlist enforced client-side. allow_origins is read from
# settings (never a wildcard "*" — see core/config.py's comment on why)
# specifically so this stays a real, auditable allowlist rather than
# "anyone, anywhere" — a wildcard combined with allow_credentials=True
# is also something browsers themselves refuse to honor at all, since
# the combination would let ANY website's JavaScript make authenticated
# requests using a logged-in user's cookies/credentials.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    try:
        response = await call_next(request)
    except Exception as exc:
        # A real, verified-necessary safety net, not defensive
        # copy-paste: this project's @app.exception_handler(Exception)
        # (below) does NOT reliably catch an exception raised inside a
        # route that uses an async-generator dependency (Depends(get_db)
        # — i.e. almost every real route in this app) when combined with
        # this custom @app.middleware("http") — verified directly while
        # building this phase's tests. This is a documented upstream
        # interaction between starlette.middleware.base.BaseHTTPMiddleware
        # (what @app.middleware("http") is built on) and exception
        # handlers: an exception raised past that point can propagate
        # THROUGH call_next() as a raised exception instead of the
        # response the registered handler produced. Catching it HERE,
        # at the one place every request already passes through
        # regardless of route, is what actually guarantees no unhandled
        # exception reaches a client as a bare, unstructured error —
        # rewriting the whole middleware stack to a raw ASGI class (the
        # theoretically cleaner upstream fix) is real, unjustified scope
        # for what this phase needs.
        #
        # Assigned to `response`, not returned directly — falling
        # through to the SAME header/logging/metrics code every normal
        # response gets below is deliberate: a request that failed this
        # way still gets an X-Request-ID, still gets counted in
        # REQUEST_COUNT/REQUEST_DURATION_SECONDS (correctly labeled
        # status_code=500 — a real signal an operator needs), and still
        # gets the standard per-request log line. An early return here
        # first cost exactly this and was caught by this phase's own
        # test asserting X-Request-ID is present on an error response.
        response = _unhandled_exception_response(exc)
    duration_seconds = time.perf_counter() - start_time

    # Security headers — a small, deliberately minimal set appropriate
    # for a JSON API (not a set of HTML-serving-app headers like a full
    # Content-Security-Policy, which mainly matters when a server
    # renders HTML/JS itself; this API never does).
    # X-Content-Type-Options: nosniff — stops a browser from ever trying
    # to guess/override the declared Content-Type and rendering a JSON
    # response as something else (e.g. HTML), which is what makes a
    # reflected-content MIME-sniffing attack possible in the first place.
    # X-Frame-Options: DENY — this API serves no page meant to be
    # framed; denying it outright closes off clickjacking against any
    # endpoint here, defense in depth even though there's no HTML UI to
    # click-jack today.
    # Referrer-Policy: strict-origin-when-cross-origin — matches the
    # frontend's own next.config.ts setting exactly, so both halves of
    # this project agree on how much of a URL leaks to a third party via
    # the Referer header.
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
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

    # /health and /metrics are polled constantly by infrastructure (a
    # container orchestrator's liveness probe, a Prometheus scrape) —
    # typically every few seconds, forever. Logging those at the same
    # INFO level as real traffic would mean, over any real deployment's
    # lifetime, the overwhelming majority of log lines are probe noise
    # drowning out the request signal an engineer actually wants to grep
    # for. DEBUG here means: still visible during local development
    # (configure_logging() sets DEBUG in that environment), silently
    # dropped in production (INFO there) — no separate flag or config
    # needed, reusing the level distinction that already exists.
    log_fn = logger.debug if path_template in {"/health", "/metrics"} else logger.info
    log_fn(
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
    415: "unsupported_media_type",
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


def _unhandled_exception_response(exc: Exception) -> JSONResponse:
    """The third, previously-missing case: an exception that's neither a
    deliberately-raised HTTPException nor a request-validation error —
    a genuine bug, an unexpected third-party error, anything nobody
    wrote a specific handler for. A plain function, not the exception
    handler itself — called from TWO places (the middleware's except
    block above, and unhandled_exception_handler() below), which is
    exactly why: see add_process_time_and_log's comment for why the
    registered @app.exception_handler(Exception) alone isn't reliably
    reached for every route in this app.

    Two things this fixes at once:

    1. CONSISTENCY — without this, an unhandled exception would produce
       a bare, unstructured "Internal Server Error" with none of this
       API's error envelope (no error code, no request_id) — every
       OTHER error path in this app returns the same ErrorResponse
       shape; this was the one gap.
    2. VISIBILITY — logged here, at ERROR, with the real exception
       and a stack trace, correlated by request_id. Without this, an
       unhandled exception in production would be visible only as
       whatever the WSGI/ASGI server happens to print to stderr — not a
       structured, request-correlated log line the way every other
       error in this app already is (see Volume 4 Phase 4's structured-
       logging work).

    Deliberately generic in the response body — `message` is always the
    same fixed string, NEVER str(exc). A raw exception message can
    contain real internal detail (a file path, a query fragment, a
    library's own internal state) that has no business reaching a
    client; the real detail goes to the server-side log line only,
    where an operator — not an arbitrary caller — is the audience.
    """
    logger.error(
        "Unhandled exception: %s", exc, exc_info=True, extra={"error": str(exc)}
    )
    body = ErrorResponse(
        error="internal_error",
        message="An unexpected error occurred.",
        request_id=get_request_id(),
    )
    return JSONResponse(status_code=500, content=body.model_dump())


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Still registered, still real — this correctly catches an
    # unhandled exception raised in any route with NO async-generator
    # dependency (or one raised before the middleware's own try/except
    # would see it, e.g. during request PARSING itself). The middleware
    # is the backstop for the gap this alone doesn't cover, not a
    # replacement for it.
    return _unhandled_exception_response(exc)


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
