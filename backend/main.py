try:
    from fastapi import FastAPI
except ImportError as exc:
    raise ImportError(
        "fastapi is required to run this application. Install with 'pip install fastapi'"
    ) from exc

from api.routes import health
from core.config import settings

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
)

app.include_router(health.router)
