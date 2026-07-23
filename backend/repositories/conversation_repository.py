import uuid

from sqlalchemy import select

from models.conversation import Conversation
from repositories.base import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    """Owns every query against the `conversations` table."""

    model = Conversation

    async def list_by_owner(self, owner_id: uuid.UUID) -> list[Conversation]:
        # Most-recently-updated first — a conversation list is naturally
        # read newest-first (matches every real chat UI's conversation
        # sidebar), and `updated_at` changes whenever a new message is
        # appended (see models/base.py's BaseModel), so this also
        # reflects recent ACTIVITY, not just creation order.
        result = await self.db.execute(
            select(Conversation)
            .where(Conversation.user_id == owner_id)
            .order_by(Conversation.updated_at.desc())
        )
        return list(result.scalars().all())
