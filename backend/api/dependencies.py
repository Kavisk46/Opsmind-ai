import uuid

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from core.security import decode_access_token
from core.storage import LocalStorage
from models.user import User
from repositories.document_repository import DocumentRepository
from repositories.user_repository import UserRepository
from services.document_service import DocumentService

# tokenUrl points Swagger UI's "Authorize" button at the login route (even
# though that route itself takes JSON, not the form-encoded body this
# class is named after) — this is purely a docs/UI hint, it doesn't change
# how OUR route parses requests. FastAPI also uses this to extract the
# `Authorization: Bearer <token>` header automatically, which is the part
# that actually matters here.
_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    token: str = Depends(_oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """The dependency every protected route will declare. Decodes and
    verifies the bearer token, then loads the user it names. Any failure
    along the way — bad signature, expired token, user since deleted —
    collapses to the same 401; a caller doesn't get to distinguish "your
    token is malformed" from "that user doesn't exist anymore."
    """
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        subject = decode_access_token(token)
        user_id = uuid.UUID(subject)
    except (jwt.PyJWTError, ValueError) as error:
        raise credentials_error from error

    user = await UserRepository(db).get_by_id(user_id)
    if user is None:
        raise credentials_error

    return user


# One process-wide LocalStorage instance — it's stateless aside from the
# directory path, so there's no reason to build a new one per request the
# way get_document_service() below builds a fresh DocumentService per
# request (that one wraps a per-request AsyncSession, which can't be
# shared).
_storage = LocalStorage(settings.storage_dir)


async def get_document_service(
    db: AsyncSession = Depends(get_db),
) -> DocumentService:
    return DocumentService(
        db, storage=_storage, max_size_bytes=settings.max_upload_size_bytes
    )


# Repository-level dependencies, distinct from get_document_service above.
# Most routes should keep depending on a *service* (business rules live
# there) — these exist for callers that genuinely only need persistence
# with no business rules attached: an admin/reporting route, a future
# script, or a Phase 5 auth flow that needs to look a user up directly
# without going through signup/login's specific rules. Both follow the
# exact same shape as get_document_service: build the repository from a
# per-request session, fresh every request, never shared/cached.
async def get_user_repository(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


async def get_document_repository(
    db: AsyncSession = Depends(get_db),
) -> DocumentRepository:
    return DocumentRepository(db)
