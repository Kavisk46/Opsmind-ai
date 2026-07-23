from pydantic import BaseModel


class StatusResponse(BaseModel):
    """Response body for GET /status — a per-dependency breakdown, distinct
    from GET /health/ready: readiness gives a binary pass/fail verdict a
    load balancer acts on; this gives descriptive detail a human or
    dashboard reads, with no pass/fail judgment attached to any one field.

    database/chromadb/storage/llm are now REAL checks (see
    core/health_checks.py) — replacing the static placeholders this
    schema originally shipped with before those dependencies existed.
    redis remains a genuine placeholder: Redis itself still doesn't exist
    in this codebase.
    """

    backend: str
    database: str
    chromadb: str
    storage: str
    llm: str
    redis: str
