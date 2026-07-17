from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Response body for GET /health.

    A dedicated schema (rather than returning a plain dict) means FastAPI
    can validate the response shape, generate accurate OpenAPI docs, and
    give editors real autocomplete on the return value.
    """

    status: str
    environment: str


class ReadinessResponse(BaseModel):
    """Response body for GET /health/ready — a separate shape from
    HealthResponse since readiness reports on a dependency (the database),
    not just the process itself."""

    status: str
    database: str
