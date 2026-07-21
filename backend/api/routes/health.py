import time

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import Settings, get_settings
from core.database import get_db
from schemas.health import HealthResponse, ReadinessResponse

router = APIRouter(tags=["health"])

# Captured once, at module import time (process startup) — every request's
# uptime is computed relative to this, not stored anywhere. time.monotonic()
# over time.time() deliberately: monotonic never jumps backwards (e.g. from
# an NTP clock correction), which time.time()-based elapsed-time math can.
_process_started_at = time.monotonic()


@router.get("/health", response_model=HealthResponse)
def get_health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    """Liveness check — confirms the process is up and can serve a request.

    Deliberately does no real work (no DB ping, no downstream calls) so it
    stays fast and dependency-free. See get_readiness() below for the check
    that DOES depend on the database.
    """
    return HealthResponse(
        status="ok",
        environment=settings.environment,
        version=settings.app_version,
        uptime_seconds=time.monotonic() - _process_started_at,
    )


@router.get("/health/ready", response_model=ReadinessResponse)
async def get_readiness(db: AsyncSession = Depends(get_db)) -> ReadinessResponse:
    """Readiness check — confirms the app can actually serve real traffic
    right now, not just that the process is alive. Pings the database with
    a trivial query; a real deployment's load balancer/orchestrator should
    stop routing traffic here if this ever fails, even while /health still
    reports the process itself as alive.

    A DB failure here is an expected, recoverable condition (the DB is
    down/unreachable), not a bug — so it's caught and turned into a clean
    503 with a plain message, rather than left to propagate as a raw,
    internals-leaking 500.

    Deliberately `except Exception`, not a narrower SQLAlchemy-specific
    type: verified against a real unreachable database that the very first
    connection attempt raises a raw, unwrapped `ConnectionRefusedError`
    (builtin OSError) — not `sqlalchemy.exc.SQLAlchemyError` — because
    SQLAlchemy only translates DBAPI errors once a connection already
    exists to translate them through. Broad exception handling is usually
    a code smell, but a readiness probe's entire job is "did this
    dependency check succeed, yes or no" — any failure at all means
    "not ready," regardless of its exact type.
    """
    try:
        await db.execute(text("SELECT 1"))
    except Exception as error:
        # detail can be any JSON-serializable value, not just a string — a
        # structured body lets a programmatic caller check response.json()
        # ["detail"]["database"] instead of string-matching an error
        # message. The 503 status code remains the primary signal (what a
        # load balancer/orchestrator actually acts on); this is a
        # secondary, human-and-machine-readable detail on top of it.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"database": "unavailable"},
        ) from error
    return ReadinessResponse(status="ok", database="connected")
