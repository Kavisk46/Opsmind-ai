from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_login_rate_limiter
from core.database import get_db
from core.rate_limit import RateLimiter
from schemas.auth import LoginRequest, TokenResponse
from services.auth_service import AuthService, InvalidCredentialsError

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
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
        access_token = await service.login(
            email=payload.email, password=payload.password
        )
    except InvalidCredentialsError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        ) from error

    return TokenResponse(access_token=access_token)
