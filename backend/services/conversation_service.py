import uuid
from datetime import datetime, timezone
from typing import Protocol

from core.logging import logger
from models.conversation import Conversation
from models.message import Message


class ConversationStore(Protocol):
    """The shape of repository ConversationService actually needs — not
    the full ConversationRepository/BaseRepository surface, just the four
    methods used below. A real ConversationRepository satisfies this
    structurally with no changes; a test can substitute a plain in-memory
    fake with none of ConversationRepository's SQLAlchemy machinery (see
    tests/test_conversation_service.py).
    """

    async def create(self, *, user_id: uuid.UUID, title: str) -> Conversation: ...
    async def get_by_id(self, id: uuid.UUID) -> Conversation | None: ...
    async def list_by_owner(self, owner_id: uuid.UUID) -> list[Conversation]: ...
    async def update(self, instance: Conversation, **fields) -> Conversation: ...
    async def delete(self, instance: Conversation) -> None: ...


class MessageStore(Protocol):
    """Same reasoning as ConversationStore above, for the `messages`
    table.
    """

    async def create(
        self, *, conversation_id: uuid.UUID, role: str, content: str
    ) -> Message: ...
    async def list_by_conversation(self, conversation_id: uuid.UUID) -> list[Message]: ...


class ConversationNotFoundError(Exception):
    """Raised both when a conversation_id truly doesn't exist AND when it
    exists but belongs to a different user — same anti-enumeration
    reasoning as DocumentNotFoundError: a 404 that only fired for
    conversations you don't own would let a caller enumerate other users'
    conversation IDs by watching for 403 vs. 404.
    """


def estimate_tokens(text: str) -> int:
    """A simple, provider-agnostic token-count ESTIMATE. Real tokenization
    is provider-specific (OpenAI's tiktoken, a HuggingFace tokenizer,
    etc.), and this project deliberately doesn't hard-code a dependency on
    any one provider's exact tokenizer just to make a truncation decision.
    ~4 characters per token is a widely-used, good-enough approximation
    for English text — not exact, but exactness isn't the goal; safely
    staying under a budget is.
    """
    return max(1, len(text) // 4)


class ConversationService:
    """Owns conversation and message persistence, and decides WHICH prior
    messages fit within a token budget before handing them to
    PromptBuilder. Extracted out of ChatService (which used to own all of
    this itself) specifically so conversation-lifecycle concerns —
    create, append, retrieve, budget — are testable and reusable
    independently of "how a question gets answered" (AIOrchestrator's
    job). ChatService now depends on this class rather than on
    ConversationRepository/MessageRepository directly.

    Takes repositories as constructor parameters (dependency injection),
    not a raw db session it builds them from internally — unlike most
    other services in this codebase (DocumentService, IngestionService),
    which construct their own repository from a session. That's a
    deliberate difference here: it's what lets a test hand this class a
    plain in-memory fake store (see tests/test_conversation_service.py)
    with zero database, zero event loop juggling for a real repository —
    exercising the token-budgeting logic in complete isolation.
    """

    def __init__(
        self,
        conversation_repository: ConversationStore,
        message_repository: MessageStore,
        *,
        max_history_tokens: int,
    ):
        self.conversation_repository = conversation_repository
        self.message_repository = message_repository
        self.max_history_tokens = max_history_tokens

    async def get_or_create_conversation(
        self,
        *,
        owner_id: uuid.UUID,
        conversation_id: uuid.UUID | None,
        title_hint: str,
    ) -> Conversation:
        if conversation_id is None:
            # A short, human-readable title derived from the first
            # question — good enough for an MVP conversation list; a
            # dedicated "generate a title" LLM call would be a real
            # improvement, not justified yet by any UI that shows titles.
            conversation = await self.conversation_repository.create(
                user_id=owner_id, title=title_hint[:80]
            )
            logger.info(
                "conversation created",
                extra={
                    "conversation_id": str(conversation.id),
                    "user_id": str(owner_id),
                },
            )
            return conversation

        conversation = await self.conversation_repository.get_by_id(conversation_id)
        if conversation is None or conversation.user_id != owner_id:
            raise ConversationNotFoundError(conversation_id)
        return conversation

    async def append_message(
        self, *, conversation_id: uuid.UUID, role: str, content: str
    ) -> Message:
        """Takes a conversation_id, not a Conversation object — this is
        what lets both ChatService (which already has the object in
        hand) and the streaming route's generator (which deliberately
        only ever holds a plain UUID, never a detached ORM object across
        the session boundary — see api/routes/chat.py) call this
        identically. Costs one extra SELECT to re-fetch the conversation
        for the updated_at bump below; a small, accepted cost at this
        project's scale, the same reasoning already applied to
        RAGRetrievalTool's per-chunk citation lookups.
        """
        message = await self.message_repository.create(
            conversation_id=conversation_id, role=role, content=content
        )

        conversation = await self.conversation_repository.get_by_id(conversation_id)
        if conversation is not None:
            # Bumps the conversation's own updated_at — without this, it
            # would only ever reflect conversation-metadata edits (there
            # are none yet), never actual message activity, which is what
            # list_conversations()'s "most recently active first"
            # ordering depends on. Setting it explicitly (not just
            # re-saving the same value) is what actually marks the row
            # dirty for SQLAlchemy to emit an UPDATE.
            await self.conversation_repository.update(
                conversation, updated_at=datetime.now(timezone.utc)
            )
        return message

    async def list_conversations(self, *, owner_id: uuid.UUID) -> list[Conversation]:
        return await self.conversation_repository.list_by_owner(owner_id)

    async def get_conversation_with_messages(
        self, *, owner_id: uuid.UUID, conversation_id: uuid.UUID
    ) -> tuple[Conversation, list[Message]]:
        conversation = await self.conversation_repository.get_by_id(conversation_id)
        if conversation is None or conversation.user_id != owner_id:
            raise ConversationNotFoundError(conversation_id)
        messages = await self.message_repository.list_by_conversation(conversation_id)
        return conversation, messages

    async def delete_conversation(
        self, *, owner_id: uuid.UUID, conversation_id: uuid.UUID
    ) -> None:
        conversation = await self.conversation_repository.get_by_id(conversation_id)
        if conversation is None or conversation.user_id != owner_id:
            raise ConversationNotFoundError(conversation_id)
        # Cascades to delete every Message in it too — see
        # models/conversation.py's relationship (cascade="all, delete-orphan")
        # and the messages table's ondelete="CASCADE" foreign key.
        await self.conversation_repository.delete(conversation)

    async def prepare_history_for_prompt(
        self, *, conversation_id: uuid.UUID
    ) -> list[tuple[str, str]]:
        """Selects as many of the MOST RECENT messages as fit within
        max_history_tokens — walking backward from the newest message,
        accumulating a token estimate, stopping before the budget would
        be exceeded — then returns them in chronological order (a
        transcript should read oldest-to-newest). At least one message is
        always included even if it alone exceeds the budget, so a single
        unusually long prior turn never results in empty history.

        Extension point for future summarization (deliberately not
        implemented now): the messages this loop decides NOT to include
        because they're too old to fit are exactly what a summarization
        step would eventually condense into one short summary turn,
        prepended here instead of being silently dropped as they are
        today.
        """
        messages = await self.message_repository.list_by_conversation(conversation_id)

        selected: list[Message] = []
        token_total = 0
        for message in reversed(messages):
            message_tokens = estimate_tokens(message.content)
            if selected and token_total + message_tokens > self.max_history_tokens:
                break
            selected.append(message)
            token_total += message_tokens
        selected.reverse()

        logger.info(
            "prepared conversation history",
            extra={
                "conversation_id": str(conversation_id),
                "message_count": len(selected),
                "estimated_tokens": token_total,
            },
        )
        return [(m.role, m.content) for m in selected]
