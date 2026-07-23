import time
from collections import defaultdict

from fastapi import HTTPException, status


class RateLimiter:
    """A simple, single-process, in-memory sliding-window rate limiter.

    Deliberately NOT distributed — state lives in this process's memory,
    so it resets on restart, and each replica in a future multi-instance
    deployment would enforce its own independent limit rather than one
    shared across all of them. That's an honest, accepted limitation at
    this project's current scale (one process, no load balancer yet); the
    real fix once that changes is the same one already noted for
    conversation memory and background jobs — move the counters to Redis
    (INCR + EXPIRE), which enforces one shared limit across every replica.

    Scoped narrowly to /auth/login, not applied globally — see the
    evaluation in this phase's write-up for why login specifically
    (brute-force/credential-stuffing protection) justifies the added
    complexity where most of this API doesn't yet.
    """

    def __init__(self, *, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str) -> None:
        """Raises 429 if `key` (typically a client IP) has already made
        max_requests within the trailing window_seconds. Records this
        call as a hit only if it's allowed through.
        """
        now = time.monotonic()
        window_start = now - self.window_seconds
        hits = self._hits[key]

        # Drop timestamps that have aged out of the window before
        # counting — this is what makes it a genuine SLIDING window
        # rather than an ever-growing list or a hard reset-every-N-seconds
        # bucket that lets a burst through right at the boundary.
        while hits and hits[0] < window_start:
            hits.pop(0)

        if len(hits) >= self.max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts. Please try again later.",
            )

        hits.append(now)
