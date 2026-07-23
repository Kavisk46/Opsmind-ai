import json
import logging

from core.config import settings

# Every field this app actually attaches via logger.info(..., extra={...}).
# Only these are pulled out of a LogRecord — everything else on a record
# (args, msg, exc_info, and a dozen other logging-internal attributes) is
# deliberately left out, so a stray future `extra={"password": ...}` a
# few phases from now doesn't silently start appearing in every log line.
_STRUCTURED_FIELDS = (
    "request_id",
    "user_id",
    "method",
    "path",
    "status_code",
    "duration_ms",
    "tool",
    "llm_provider",
    "llm_model",
    "llm_duration_ms",
    "llm_success",
    "llm_prompt_tokens",
    "llm_completion_tokens",
    "conversation_id",
    "message_count",
    "estimated_tokens",
    "estimated_cost_usd",
    "error",
    "retrieval_chunk_count",
    "retrieval_duration_ms",
    "retrieval_avg_confidence",
    "citation_count",
    "context_provided",
    "answer_length_chars",
)


class JSONFormatter(logging.Formatter):
    """Renders each log record as one JSON line instead of free text.

    This reverses an earlier, deliberate decision (see the Request/
    Response phase's write-up: "no structured logging yet — nothing
    consumes it as structure"). What changed: this phase explicitly needs
    request_id/user_id/status_code/duration to be independently
    queryable fields (e.g. "show me every 5xx for user X"), which free
    text can't give you without regex-parsing — exactly the trigger
    condition flagged back then as "once there's an actual reason."
    """

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in _STRUCTURED_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        return json.dumps(payload)


def configure_logging() -> None:
    """Called once, at import time, from main.py — configuring logging
    per-request (or per-module) would risk re-adding handlers on every
    request, duplicating every log line. DEBUG in development so you see
    everything; INFO everywhere else, so routine per-request logs don't
    drown out real signal in a real deployment.
    """
    level = logging.DEBUG if settings.environment == "development" else logging.INFO
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logging.basicConfig(level=level, handlers=[handler], force=True)


# One shared logger for the whole app, named after the package rather than
# `__name__` per-module — this project is small enough that per-module
# logger names would add noise without adding useful filtering yet.
logger = logging.getLogger("opsmind")
