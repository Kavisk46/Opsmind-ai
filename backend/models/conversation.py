import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import BaseModel

if TYPE_CHECKING:
    from models.message import Message
    from models.user import User
    from models.workspace import Workspace


class Conversation(BaseModel):
    """The `conversations` table — a single chat thread belonging to one
    user. No document/message content lives here directly; this row is
    just the thread's identity and title, holding the Messages that make
    it up (see models/message.py).

    workspace_id records WHICH workspace a conversation happened in (for
    organizational/audit purposes — see models/workspace.py) but is
    deliberately NOT a shared-visibility boundary the way Document's is:
    a conversation stays private to the user who started it even inside a
    shared workspace, the same "your chat history is your own, even on a
    team plan" default most real chat products use. Retrieval/tool-calling
    invoked from within a conversation still scopes by owner_id for now
    (see RAGRetrievalTool) — a deliberate, staged deferral, not this
    phase's concern.
    """

    __tablename__ = "conversations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String)

    user: Mapped["User"] = relationship(back_populates="conversations")
    workspace: Mapped["Workspace"] = relationship()
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )
