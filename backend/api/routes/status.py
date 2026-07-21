from fastapi import APIRouter

from schemas.status import StatusResponse

router = APIRouter(tags=["status"])


@router.get("/status", response_model=StatusResponse)
def get_status() -> StatusResponse:
    """A per-dependency status summary. database/redis/ai are static
    placeholders on purpose — Redis and the AI stack don't exist in this
    codebase yet (see GET /health/ready for the one dependency that IS
    really checked today: the database connection).
    """
    return StatusResponse(
        backend="ok",
        database="not_configured",
        redis="not_configured",
        ai="not_configured",
    )
