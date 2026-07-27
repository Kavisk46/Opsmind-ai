from typing import Literal

from fastapi import Response

from core.config import settings

ACCESS_TOKEN_COOKIE_NAME = "access_token"
REFRESH_TOKEN_COOKIE_NAME = "refresh_token"

_ACCESS_TOKEN_MAX_AGE_SECONDS = settings.access_token_expire_minutes * 60
_REFRESH_TOKEN_MAX_AGE_SECONDS = settings.refresh_token_expire_days * 24 * 60 * 60

# Cross-origin by design: the deployed frontend (Vercel) and backend
# (Render) are on different origins, so the browser only sends these
# cookies back on requests to this API AT ALL if they're marked
# SameSite=None — which browsers additionally REQUIRE to be paired with
# Secure (HTTPS-only). Both are real requirements here, not caution for
# its own sake: dropping either breaks cross-origin auth outright, the
# exact class of bug the OAuth request that led to this module was about.
#
# Local development runs both sides over plain HTTP on localhost, where
# Secure cookies are never sent at all — hence the environment branch:
# "lax" + non-secure locally (works fine for same-site localhost ports),
# "none" + secure for any real deployment.
_IS_PRODUCTION_LIKE = settings.environment != "development"
_COOKIE_SAMESITE: Literal["none", "lax"] = "none" if _IS_PRODUCTION_LIKE else "lax"
_COOKIE_SECURE = _IS_PRODUCTION_LIKE


def set_auth_cookies(response: Response, *, access_token: str, refresh_token: str) -> None:
    """Called by every route that establishes or renews a session:
    POST /auth/login, POST /auth/refresh, and every OAuth provider's
    callback route. One place means all three can never drift apart on
    cookie attributes (a mismatch there is exactly the kind of bug that's
    invisible in local testing and only shows up cross-origin in prod).
    """
    response.set_cookie(
        ACCESS_TOKEN_COOKIE_NAME,
        access_token,
        max_age=_ACCESS_TOKEN_MAX_AGE_SECONDS,
        httponly=True,
        secure=_COOKIE_SECURE,
        samesite=_COOKIE_SAMESITE,
        path="/",
    )
    response.set_cookie(
        REFRESH_TOKEN_COOKIE_NAME,
        refresh_token,
        max_age=_REFRESH_TOKEN_MAX_AGE_SECONDS,
        httponly=True,
        secure=_COOKIE_SECURE,
        samesite=_COOKIE_SAMESITE,
        path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    """Deleting a cookie means setting one with the same name/path that
    expires immediately — the attributes (samesite/secure) must match
    what set_auth_cookies used, or some browsers won't recognize it as
    the same cookie to delete."""
    response.delete_cookie(
        ACCESS_TOKEN_COOKIE_NAME,
        path="/",
        secure=_COOKIE_SECURE,
        samesite=_COOKIE_SAMESITE,
    )
    response.delete_cookie(
        REFRESH_TOKEN_COOKIE_NAME,
        path="/",
        secure=_COOKIE_SECURE,
        samesite=_COOKIE_SAMESITE,
    )
