from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_llm, get_vector_store
from core.config import settings
from core.database import get_db
from core.health_checks import check_chromadb, check_database, check_llm, check_storage
from core.vector_store import VectorStore
from schemas.status import StatusResponse
from services.llm.protocol import LLMProvider

router = APIRouter(tags=["status"])


@router.get("/status", response_model=StatusResponse)
async def get_status(
    db: AsyncSession = Depends(get_db),
    vector_store: VectorStore = Depends(get_vector_store),
    llm: LLMProvider = Depends(get_llm),
) -> StatusResponse:
    """A per-dependency status summary. database/chromadb/storage/llm
    are real checks now, sharing the exact same logic GET /health/ready
    uses (see core/health_checks.py) — the difference is this route never
    raises on a failed check; it just reports what it found. redis
    remains a genuine placeholder — Redis doesn't exist in this codebase
    yet.
    """
    return StatusResponse(
        backend="ok",
        database=await check_database(db),
        chromadb=check_chromadb(vector_store),
        storage=check_storage(settings.storage_dir),
        llm=check_llm(llm),
        redis="not_configured",
    )
