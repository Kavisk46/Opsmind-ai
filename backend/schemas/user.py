import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """API-facing INPUT shape — what a client sends to create a user.
    Deliberately a different class from UserResponse below, even though
    they describe "the same resource": a client sends a plain-text
    `password`, but a response must never echo a password (or its hash)
    back — one schema can't correctly describe both directions at once.
    """

    email: EmailStr
    name: str
    # min_length=8 — roughly NIST 800-63B's own current baseline
    # (length matters far more than forced complexity rules like
    # "must contain a symbol," which NIST's own current guidance
    # actively discourages as more annoying than protective). Before
    # this, ANY non-empty string — including a single character — was
    # accepted, silently, all the way through to a real bcrypt hash.
    # max_length=128 is defensive, not a UX opinion: bcrypt itself
    # silently truncates at 72 BYTES regardless, but without an upper
    # bound here, nothing stops a request body from carrying a
    # multi-megabyte "password" string that this process would still
    # copy into memory and pass to bcrypt before truncation ever
    # happens — a cheap, real request-size guard.
    password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    """API-facing OUTPUT shape of a User. Deliberately separate from
    models/user.py (the DB table definition) — we will never add
    `password_hash` here, even though the table has one.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    name: str
    created_at: datetime
