import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ConversationCreateRequest(BaseModel):
    # Optional: omitted means "New conversation" — a real title only
    # exists once a first question is asked through POST /chat, which
    # derives one automatically (see ConversationService.get_or_create_conversation).
    title: str | None = None


class ConversationRenameRequest(BaseModel):
    # Required, unlike ConversationCreateRequest.title — creating with no
    # title has a sensible default ("New conversation"); explicitly
    # renaming to nothing does not, so the route rejects it (see
    # api/routes/conversations.py's empty-title check) rather than
    # silently falling back to a default the caller never asked for.
    title: str


class ConversationResponse(BaseModel):
    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    role: str
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationDetailResponse(BaseModel):
    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageResponse]
