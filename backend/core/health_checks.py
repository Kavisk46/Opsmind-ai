import asyncio
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.vector_store import VectorStore
from services.llm.protocol import LLMProvider

# Shared by both GET /health/ready (which uses these to decide the
# overall pass/fail verdict) and GET /status (which reports the same
# facts descriptively, with no pass/fail judgment attached) — one place
# defining what "healthy" means for each dependency, read by two
# different routes with two different jobs.

# A genuinely DOWN database fails fast (connection refused). A HUNG one
# — network partition, a stuck query holding a lock, Postgres itself
# wedged — does neither: it just never responds, and without a bound
# this check would await forever, which would make /health/ready itself
# hang forever right along with it. A hanging readiness check is worse
# than a fast failure: a load balancer/orchestrator polling it would
# rather see a clear "not ready" within a couple seconds than have its
# own health-check request pile up waiting on a dependency that's stuck.
_DB_CHECK_TIMEOUT_SECONDS = 3.0


async def check_database(db: AsyncSession) -> str:
    # Deliberately `except Exception`, not a narrower SQLAlchemy-specific
    # type — see get_readiness()'s original docstring for why: a truly
    # unreachable database raises a raw, unwrapped ConnectionRefusedError
    # before SQLAlchemy ever gets a connection to translate errors through.
    # asyncio.TimeoutError is a subclass of Exception, so the same
    # except below also correctly turns a HUNG check into "unavailable"
    # rather than propagating and crashing the request.
    try:
        async with asyncio.timeout(_DB_CHECK_TIMEOUT_SECONDS):
            await db.execute(text("SELECT 1"))
        return "connected"
    except Exception:
        return "unavailable"


def check_chromadb(vector_store: VectorStore) -> str:
    try:
        vector_store.count()
        return "connected"
    except Exception:
        return "unavailable"


def check_storage(storage_dir: str) -> str:
    return "writable" if os.access(storage_dir, os.W_OK) else "unavailable"


def check_llm(llm: LLMProvider) -> str:
    # "not_loaded_yet" is a healthy, expected state for a lazily-loaded
    # model — never treated as a failure by get_readiness() below.
    return "loaded" if getattr(llm, "is_loaded", False) else "not_loaded_yet"
