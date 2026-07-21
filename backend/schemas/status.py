from pydantic import BaseModel


class StatusResponse(BaseModel):
    """Response body for GET /status — a per-dependency breakdown, distinct
    from GET /health/ready. database/redis/ai are deliberately static
    placeholders for now (Redis and the AI stack don't exist yet); each
    becomes a real check in the phase that introduces that dependency,
    without changing this schema's shape.
    """

    backend: str
    database: str
    redis: str
    ai: str
