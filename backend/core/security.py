import hashlib
import secrets
from datetime import UTC, datetime, timedelta

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
    expire = datetime.now(UTC) + timedelta(
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


def create_refresh_token() -> str:
    """A refresh token is a plain, high-entropy random string — NOT a
    JWT, and deliberately so. Its validity is decided entirely by looking
    up its hash in the refresh_tokens table (see repositories/
    refresh_token_repository.py), which is what makes real server-side
    revocation possible: logout, or reuse-after-rotation detection, both
    just flip a row's revoked_at rather than needing a separate JWT
    blocklist that a self-contained token would otherwise require.
    32 bytes (256 bits) of randomness — far beyond brute-force range,
    which is exactly why hashing it for storage can be fast (see
    hash_refresh_token) rather than deliberately slow like a password.
    """
    return secrets.token_urlsafe(32)


def hash_refresh_token(token: str) -> str:
    """SHA-256, not bcrypt — this token is already high-entropy (see
    create_refresh_token), so there's no low-entropy human-chosen secret
    to defend against brute-forcing; a fast, deterministic hash is
    correct here, and REQUIRED anyway since refresh() needs to look a
    token up by its hash directly (bcrypt's random-salt-per-call design
    makes it unusable as a lookup key)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
