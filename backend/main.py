import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from api.routes import auth, documents, health, root, status, users
from core.config import settings
from core.database import engine
from core.logging import configure_logging, logger

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

    Redis and the AI stack don't exist yet — those startup/shutdown steps
    are left as explicit placeholders (not real connections) so the shape
    is ready without pretending something is wired up that isn't.
    """
    logger.info("OpsMind backend starting up (environment=%s)", settings.environment)

    # Placeholder — Redis client connection (Phase: caching)
    # Placeholder — embedding model / LLM client load (Phase: AI)

    yield

    logger.info("OpsMind backend shutting down")
    await engine.dispose()
    # Placeholder — Redis client disconnect (Phase: caching)
    # Placeholder — release AI model resources (Phase: AI)


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

    `request` here is the raw Starlette Request — request.method and
    request.url.path aren't Pydantic-parsed data, they're properties of
    the HTTP request itself, unavailable through any route parameter.
    `call_next(request)` runs the rest of the pipeline (routing, the
    matched route, response_model serialization) and hands back the real
    Response object — which we then mutate directly by setting a header,
    something response_model has no way to express.
    """
    start_time = time.perf_counter()
    response = await call_next(request)
    duration_seconds = time.perf_counter() - start_time

    response.headers["X-Process-Time"] = f"{duration_seconds:.4f}"
    logger.info(
        "%s %s %s %.4fs",
        request.method,
        request.url.path,
        response.status_code,
        duration_seconds,
    )
    return response


app.include_router(root.router)
app.include_router(health.router)
app.include_router(status.router)
app.include_router(users.router)
app.include_router(auth.router)
app.include_router(documents.router)
