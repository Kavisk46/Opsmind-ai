import uuid
from typing import AsyncIterator

from models.conversation import Conversation
from models.message import MessageRole
from services.conversation_service import ConversationService
from services.orchestrator import AIOrchestrator, OrchestratorResult
from services.tools import Citation

# Re-exported so existing callers (api/routes/chat.py) don't need to know
# this moved to ConversationService — ChatService's public error surface
# stays the same even though the responsibility it once owned directly
# has been extracted out.
from services.conversation_service import ConversationNotFoundError  # noqa: F401


class EmptyQuestionError(Exception):
    """Raised for a blank/whitespace-only question — never worth
    retrieving context or calling the LLM for."""


class ChatService:
    """Orchestrates one chat turn: validate the question, delegate
    conversation lifecycle (create/continue, history, persistence) to
    ConversationService, delegate "how to answer" to AIOrchestrator.
    Deliberately thin — this class's only real job is calling its two
    collaborators in the right order; conversation-lifecycle concerns and
    tool-routing concerns live in two separate, independently-testable
    classes.
    """

    def __init__(
        self, conversation_service: ConversationService, orchestrator: AIOrchestrator
    ):
        self.conversation_service = conversation_service
        self.orchestrator = orchestrator

    async def ask(
        self,
        *,
        owner_id: uuid.UUID,
        question: str,
        conversation_id: uuid.UUID | None,
    ) -> tuple[Conversation, OrchestratorResult]:
        if not question.strip():
            raise EmptyQuestionError()

        conversation = await self.conversation_service.get_or_create_conversation(
            owner_id=owner_id, conversation_id=conversation_id, title_hint=question
        )

        # Fetched BEFORE persisting this turn's user message, so history
        # never includes the question currently being answered. Token-
        # budgeted, not just count-limited — see
        # ConversationService.prepare_history_for_prompt()'s docstring.
        history = await self.conversation_service.prepare_history_for_prompt(
            conversation_id=conversation.id
        )

        await self.conversation_service.append_message(
            conversation_id=conversation.id, role=MessageRole.USER.value, content=question
        )

        result = await self.orchestrator.handle(
            question=question,
            owner_id=owner_id,
            history=history,
            conversation_id=conversation.id,
        )

        await self.conversation_service.append_message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT.value,
            content=result.answer,
        )

        return conversation, result

    async def ask_stream(
        self,
        *,
        owner_id: uuid.UUID,
        question: str,
        conversation_id: uuid.UUID | None,
    ) -> tuple[Conversation, str, list[Citation], AsyncIterator[str]]:
        """Same validation, conversation resolution, history preparation,
        and user-message persistence as ask() — all of that fully
        completes here, using this instance's normal per-request
        ConversationService, before any streaming begins.

        Deliberately does NOT persist the assistant's message itself —
        unlike ask(), which has the complete answer text in hand
        immediately. Here, the answer only exists as token_stream, not
        yet consumed. Persisting it is the CALLER's job (see
        api/routes/chat.py), using its OWN ConversationService built from
        a session that survives past this method's return — the FastAPI
        route function returns (and this instance's session starts
        closing) before the stream is ever read from, so anything needing
        to happen after full consumption can't safely reuse it. Same
        reasoning IngestionService uses a session factory instead of a
        shared per-request session for background work.
        """
        if not question.strip():
            raise EmptyQuestionError()

        conversation = await self.conversation_service.get_or_create_conversation(
            owner_id=owner_id, conversation_id=conversation_id, title_hint=question
        )

        history = await self.conversation_service.prepare_history_for_prompt(
            conversation_id=conversation.id
        )

        await self.conversation_service.append_message(
            conversation_id=conversation.id, role=MessageRole.USER.value, content=question
        )

        tool_used, citations, token_stream = await self.orchestrator.handle_stream(
            question=question,
            owner_id=owner_id,
            history=history,
            conversation_id=conversation.id,
        )

        return conversation, tool_used, citations, token_stream
