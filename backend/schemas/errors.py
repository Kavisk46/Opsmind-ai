from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """The consistent shape EVERY error response takes across this
    entire API, regardless of which route or exception produced it —
    enforced globally by main.py's exception handlers, not by each route
    individually remembering to format its own errors this way. Before
    this phase, error bodies were whatever shape each route's
    `HTTPException(detail=...)` happened to use (a plain string in most
    places, a dict in a couple) — inconsistent for any client trying to
    parse errors generically.
    """

    error: str  # short, stable, machine-readable code — e.g. "not_found"
    message: str  # human-readable detail, safe to show a user
    request_id: str | None  # correlates this error with its log line
