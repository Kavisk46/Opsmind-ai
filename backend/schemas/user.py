import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class UserCreate(BaseModel):
    """API-facing INPUT shape — what a client sends to create a user.
    Deliberately a different class from UserResponse below, even though
    they describe "the same resource": a client sends a plain-text
    `password`, but a response must never echo a password (or its hash)
    back — one schema can't correctly describe both directions at once.
    """

    email: EmailStr
    name: str
    password: str


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
