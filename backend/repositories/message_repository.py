import uuid

from sqlalchemy import select

from models.message import Message
from repositories.base import BaseRepository


class MessageRepository(BaseRepository[Message]):
    """Owns every query against the `messages` table."""

    model = Message

    async def list_by_conversation(self, conversation_id: uuid.UUID) -> list[Message]:
        # Ordered by created_at so conversation history reads in the
        # order it was actually said — this is exactly the "conversation
        # memory" ChatService feeds back into the prompt for a follow-up
        # question.
        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        )
        return list(result.scalars().all())
