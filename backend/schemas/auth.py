from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    # OAuth2's own convention for this field's value — "Bearer" is what a
    # client is expected to send back: `Authorization: Bearer <token>`.
    token_type: str = "bearer"
