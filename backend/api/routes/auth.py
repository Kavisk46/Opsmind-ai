from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_login_rate_limiter
from core.cookies import (
    REFRESH_TOKEN_COOKIE_NAME,
    clear_auth_cookies,
    set_auth_cookies,
)
from core.database import get_db
from core.rate_limit import RateLimiter
from schemas.auth import LoginRequest, TokenResponse
from services.auth_service import (
    AuthService,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    rate_limiter: RateLimiter = Depends(get_login_rate_limiter),
) -> TokenResponse:
    # Checked before anything else — a brute-force/credential-stuffing
    # attempt shouldn't even reach a real password check once it's over
    # the limit. Keyed by client IP: crude (a shared NAT/proxy means
    # multiple real users share one limit), but this endpoint's whole
    # point is slowing down automated guessing, not fingerprinting
    # individual users — a real IP-sharing false positive is an
    # acceptable, honest trade-off at this project's scale.
    client_host = request.client.host if request.client else "unknown"
    rate_limiter.check(client_host)

    service = AuthService(db)
    try:
        tokens = await service.login(email=payload.email, password=payload.password)
    except InvalidCredentialsError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        ) from error

    # BOTH a real response body AND httpOnly cookies — the body keeps
    # this endpoint usable exactly as before for a non-browser API client
    # (and this project's own test suite, which reads it directly); the
    # cookies are what the deployed frontend actually relies on (see
    # api/dependencies.py's get_current_user, which accepts either).
    set_auth_cookies(
        response, access_token=tokens.access_token, refresh_token=tokens.refresh_token
    )
    return TokenResponse(access_token=tokens.access_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Exchanges a valid refresh token for a new access token — AND a new
    refresh token (rotation; see AuthService.refresh() for why). Reads
    the refresh token ONLY from the cookie: there is no legitimate reason
    for a browser client to ever need to pass one in a request body, and
    not accepting one keeps this endpoint from becoming a second way to
    smuggle a token into a log line or a browser history entry.
    """
    refresh_token = request.cookies.get(REFRESH_TOKEN_COOKIE_NAME)
    if refresh_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token was provided.",
        )

    service = AuthService(db)
    try:
        tokens = await service.refresh(refresh_token)
    except InvalidRefreshTokenError as error:
        # Whatever was there is no longer valid either way — clearing it
        # here means the frontend's silent-refresh-then-retry logic
        # (lib/api/client.ts) fails cleanly to a real logout instead of
        # retrying forever against a cookie that will never work again.
        clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session has expired. Please sign in again.",
        ) from error

    set_auth_cookies(
        response, access_token=tokens.access_token, refresh_token=tokens.refresh_token
    )
    return TokenResponse(access_token=tokens.access_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> None:
    """A REAL logout, unlike a purely client-side "forget the token"
    approach: the refresh token is revoked server-side (see
    AuthService.logout()), so a copy of it captured before this call —
    in a proxy log, a browser history entry, wherever — stops being
    usable the moment this endpoint runs, not just whenever it happens
    to expire on its own. Succeeds even with no cookie present at all
    (AuthService.logout() is idempotent) — the caller's goal (no longer
    having a session) is already true in that case.
    """
    refresh_token = request.cookies.get(REFRESH_TOKEN_COOKIE_NAME)
    if refresh_token is not None:
        await AuthService(db).logout(refresh_token)
    clear_auth_cookies(response)
