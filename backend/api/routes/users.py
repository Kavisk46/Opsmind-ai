from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_current_user, require_role
from core.database import get_db
from models.user import User, UserRole
from schemas.user import UserCreate, UserResponse
from services.user_service import DuplicateEmailError, UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN)),
) -> list[User]:
    # SECURITY FIX: this route had no auth dependency at all — any
    # unauthenticated caller could list every user's email/name/id.
    # require_role(UserRole.ADMIN) fixes both problems at once: it depends
    # on get_current_user internally (so a missing/invalid token now
    # correctly 401s), then additionally requires the admin role (so an
    # authenticated non-admin correctly 403s instead of seeing every user).
    # The parameter is named `_` because the route doesn't need the
    # returned User — it's declared purely to enforce the check; unlike
    # GET /users/me below, nothing here reads who's calling.
    #
    # Returns ORM objects, not UserResponse — `response_model` above is
    # what actually converts them at serialization time (via
    # UserResponse's `from_attributes=True`). The type hint reflects what
    # this function really returns, not what the client receives.
    service = UserService(db)
    return await service.list_users()


@router.get("/me", response_model=UserResponse)
async def get_my_profile(current_user: User = Depends(get_current_user)) -> User:
    # The whole point of this route: it needs no db session, no service,
    # no repository call of its own — get_current_user() already did all
    # of that to prove the token was valid, and handed back the user.
    # This route exists purely to demonstrate the dependency working.
    return current_user


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate, db: AsyncSession = Depends(get_db)
) -> User:
    # This is the route's real job in a layered architecture: translate
    # between HTTP concerns (request bodies, status codes) and the
    # service's plain-Python API. The service doesn't know what a 409 is;
    # the route doesn't know what "duplicate email" means as a rule — each
    # layer only knows its own vocabulary.
    service = UserService(db)
    try:
        return await service.create_user(
            email=payload.email, name=payload.name, password=payload.password
        )
    except DuplicateEmailError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from error
