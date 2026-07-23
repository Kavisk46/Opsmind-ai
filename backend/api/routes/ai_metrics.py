from fastapi import APIRouter, Depends

from api.dependencies import get_ai_metrics_service, require_role
from models.user import User, UserRole
from services.ai_metrics_service import AIMetricsService

router = APIRouter(prefix="/internal", tags=["internal"])


@router.get("/ai-metrics")
async def get_ai_metrics_summary(
    metrics_service: AIMetricsService = Depends(get_ai_metrics_service),
    _: User = Depends(require_role(UserRole.ADMIN)),
) -> dict:
    """Aggregated, human-readable AI usage/cost/quality summary — distinct
    from GET /metrics (Prometheus's machine-oriented text exposition
    format, meant to be scraped on an interval, not read directly). This
    is meant to be opened in a browser or hit with curl during
    development and demos: how many LLM calls have happened, what did
    they cost, how healthy does retrieval look.

    Gated by require_role(UserRole.ADMIN), unlike GET /metrics (which has
    no app-level auth at all) — a real Prometheus scrape target is
    typically restricted at the network level instead (only the
    monitoring stack can reach it), but this project has no equivalent
    network-level restriction for an arbitrary JSON endpoint, and the
    data here is more sensitive (estimated spend, per-conversation
    correlation) than a scrape-oriented counter dump. App-level RBAC is
    the right gate given what this project actually has available.
    """
    return metrics_service.summary()
