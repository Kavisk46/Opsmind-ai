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


async def check_database(db: AsyncSession) -> str:
    # Deliberately `except Exception`, not a narrower SQLAlchemy-specific
    # type — see get_readiness()'s original docstring for why: a truly
    # unreachable database raises a raw, unwrapped ConnectionRefusedError
    # before SQLAlchemy ever gets a connection to translate errors through.
    try:
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
