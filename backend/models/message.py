import uuid
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import BaseModel

if TYPE_CHECKING:
    from models.conversation import Conversation


class MessageRole(str, Enum):
    """Who authored a message. A bounded set, not free text — the same
    reasoning as DocumentStatus: 'asistant' or 'Assistant' typo'd
    somewhere would silently create a role no code checks for; an Enum
    makes that typo impossible to write in the first place.
    """

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(BaseModel):
    """The `messages` table — one turn in a Conversation. No message
    exists independently of a conversation, which is why deleting a
    Conversation cascades to delete its Messages (see
    models/conversation.py's relationship) rather than leaving orphaned
    rows behind.
    """

    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String)
    content: Mapped[str] = mapped_column(String)
    # Named extra_metadata, not metadata — SQLAlchemy's DeclarativeBase
    # already reserves the attribute name `metadata` for the MetaData
    # instance every model class carries; mapping a column under that
    # exact Python name raises InvalidRequestError at class-definition
    # time. mapped_column("metadata", ...) still makes the real database
    # COLUMN named "metadata" — only the Python-side attribute differs.
    # Populated with provider/model/tool_used/token counts for an
    # assistant message (see ChatService.ask()/api/routes/chat.py); None
    # for a user message, which has no such thing to record.
    extra_metadata: Mapped[dict | None] = mapped_column(
        "metadata", JSON, nullable=True
    )

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
