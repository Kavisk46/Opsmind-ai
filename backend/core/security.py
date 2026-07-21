from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from core.config import settings

# bcrypt operates on bytes, not str, and its own encoded output already
# includes the salt — nothing else needs to be stored alongside the hash.
_ENCODING = "utf-8"


def hash_password(plain_password: str) -> str:
    """One-way hash — there is no corresponding `unhash_password()`, by
    design. See the Phase 3 write-up for why passwords are hashed, never
    encrypted."""
    hashed = bcrypt.hashpw(plain_password.encode(_ENCODING), bcrypt.gensalt())
    return hashed.decode(_ENCODING)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Re-hashes the login attempt and compares — never decrypts the
    stored value, because a bcrypt hash cannot be decrypted."""
    return bcrypt.checkpw(
        plain_password.encode(_ENCODING), hashed_password.encode(_ENCODING)
    )


def create_access_token(subject: str) -> str:
    """Issues a signed JWT identifying `subject` (the user's id, as a
    string — JWT claims must be JSON-serializable, and a UUID object isn't).
    Anyone holding this token is trusted as that user until it expires.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> str:
    """Verifies the token's signature and expiration, returns the subject
    (user id) it was issued for. Raises a jwt.PyJWTError subclass if the
    token is invalid, tampered with, or expired — api/dependencies.py's
    get_current_user() catches that and responds 401, not this function.
    """
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    return payload["sub"]
