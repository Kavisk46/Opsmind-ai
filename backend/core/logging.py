import logging

from core.config import settings


def configure_logging() -> None:
    """Called once, at import time, from main.py — configuring logging
    per-request (or per-module) would risk re-adding handlers on every
    request, duplicating every log line. DEBUG in development so you see
    everything; INFO everywhere else, so routine per-request logs don't
    drown out real signal in a real deployment.
    """
    level = logging.DEBUG if settings.environment == "development" else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


# One shared logger for the whole app, named after the package rather than
# `__name__` per-module — this project is small enough that per-module
# logger names would add noise without adding useful filtering yet.
logger = logging.getLogger("opsmind")
