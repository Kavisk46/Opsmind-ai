import time

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_llm, get_vector_store
from core.config import Settings, get_settings, settings as app_settings
from core.database import get_db
from core.health_checks import check_chromadb, check_database, check_llm, check_storage
from core.vector_store import VectorStore
from schemas.health import HealthResponse, ReadinessResponse
from services.llm.protocol import LLMProvider

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
    that DOES depend on real infrastructure.
    """
    return HealthResponse(
        status="ok",
        environment=settings.environment,
        version=settings.app_version,
        uptime_seconds=time.monotonic() - _process_started_at,
    )


@router.get("/health/ready", response_model=ReadinessResponse)
async def get_readiness(
    db: AsyncSession = Depends(get_db),
    vector_store: VectorStore = Depends(get_vector_store),
    llm: LLMProvider = Depends(get_llm),
) -> ReadinessResponse:
    """Readiness check — confirms the app can actually serve real traffic
    right now, not just that the process is alive. A real deployment's
    load balancer/orchestrator should stop routing traffic here if this
    ever fails, even while /health still reports the process itself as
    alive.

    Checks three HARD dependencies (database, ChromaDB, storage) — any of
    them failing means genuinely "not ready." The LLM is checked too, but
    informationally only: "not_loaded_yet" is a normal state for a
    lazily-loaded model (see services/llm/local_provider.py), never a
    reason to fail readiness — an instance that hasn't answered its first
    chat question yet is still perfectly capable of serving every other
    kind of request.
    """
    checks = {
        "database": await check_database(db),
        "chromadb": check_chromadb(vector_store),
        "storage": check_storage(app_settings.storage_dir),
        "llm": check_llm(llm),
    }

    hard_dependencies_ok = (
        checks["database"] == "connected"
        and checks["chromadb"] == "connected"
        and checks["storage"] == "writable"
    )
    if not hard_dependencies_ok:
        # detail can be any JSON-serializable value, not just a string —
        # main.py's exception handler stringifies it into ErrorResponse.message,
        # so a caller still sees exactly which dependency failed.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=checks
        )

    return ReadinessResponse(status="ok", **checks)
