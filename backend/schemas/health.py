from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Response body for GET /health.

    A dedicated schema (rather than returning a plain dict) means FastAPI
    can validate the response shape, generate accurate OpenAPI docs, and
    give editors real autocomplete on the return value.
    """

    status: str
    environment: str
    version: str
    uptime_seconds: float


class ReadinessResponse(BaseModel):
    """Response body for GET /health/ready — a separate shape from
    HealthResponse since readiness reports on this instance's actual
    dependencies, not just the process itself. `llm` is informational
    only (see get_readiness()) — a model that hasn't loaded yet is a
    normal state, never a reason to fail readiness.
    """

    status: str
    database: str
    chromadb: str
    storage: str
    llm: str
