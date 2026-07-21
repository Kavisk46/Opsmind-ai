import uuid
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
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

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
