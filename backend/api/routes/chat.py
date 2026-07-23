import json
import uuid
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from api.dependencies import get_chat_service, get_current_user, get_session_factory
from core.config import settings
from core.logging import logger
from models.message import MessageRole
from models.user import User
from repositories.conversation_repository import ConversationRepository
from repositories.message_repository import MessageRepository
from schemas.chat import ChatRequest, ChatResponse, CitationResponse
from services.chat_service import ChatService, ConversationNotFoundError, EmptyQuestionError
from services.conversation_service import ConversationService
from services.tools import Citation

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def ask(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    try:
        conversation, result = await service.ask(
            owner_id=current_user.id,
            question=payload.question,
            conversation_id=payload.conversation_id,
        )
    except EmptyQuestionError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Question cannot be empty."
        ) from error
    except ConversationNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found."
        ) from error

    return ChatResponse(
        conversation_id=conversation.id,
        answer=result.answer,
        tool_used=result.tool_used,
        citations=[
            CitationResponse(
                document_id=citation.document_id,
                document_name=citation.document_name,
                chunk_index=citation.chunk_index,
                page_number=citation.page_number,
            )
            for citation in result.citations
        ],
    )


def _sse_event(payload: dict) -> str:
    """Server-Sent-Events framing: each event is one "data: <json>\\n\\n"
    line — the format a browser's EventSource, or a fetch() +
    ReadableStream reader, expects to split incoming bytes on. JSON
    inside each event (rather than raw text) is what lets a single
    stream carry both incremental answer text AND a final structured
    payload (citations, tool_used) without inventing a second channel.
    """
    return f"data: {json.dumps(payload)}\n\n"


async def _stream_chat_response(
    *,
    conversation_id: uuid.UUID,
    tool_used: str,
    citations: list[Citation],
    token_stream: AsyncIterator[str],
    session_factory,
):
    """The actual StreamingResponse body. Runs AFTER the route function
    that constructs it has already returned — which is exactly why it
    never touches that request's `Depends(get_db)` session (see
    ChatService.ask_stream()'s docstring): by the time Starlette starts
    iterating this generator, that session may already be closing.
    Persistence of the final assistant message below opens its own,
    independent session instead, built from `session_factory` — passed
    in via Depends(get_session_factory) rather than imported directly,
    which is exactly what lets tests substitute the SQLite factory here
    instead of the real Postgres one (see get_session_factory's
    docstring for the bug this fixed).
    """
    full_text_parts: list[str] = []
    # Three possible outcomes — same reasoning as OpenAIProvider.generate_stream():
    # "success" (the loop finishes naturally), "failed" (an exception
    # propagates), or "cancelled" (the client disconnected and Starlette
    # closes this generator early via GeneratorExit, skipping both the
    # success line and the except block below).
    status_label = "cancelled"
    try:
        async for delta in token_stream:
            full_text_parts.append(delta)
            yield _sse_event({"delta": delta})
        status_label = "success"
    except Exception as error:
        status_label = "failed"
        logger.error("Chat stream failed: %s", error)
        # A best-effort message to the client before re-raising — a
        # partial stream that just stops with no explanation is worse
        # than one that says plainly it couldn't finish.
        yield _sse_event({"error": "The response could not be completed."})
        raise
    finally:
        logger.info(
            "Chat stream %s",
            status_label,
            extra={"tool": tool_used},
        )

        # Persist whatever text was actually generated — even a
        # cancelled or partial response is real conversation history
        # worth keeping, not silently discarded. Goes through
        # ConversationService (not a bare MessageRepository) for
        # consistency with the non-streaming path — this is also what
        # correctly bumps the conversation's updated_at (see
        # ConversationService.append_message()), so a streamed reply
        # counts as activity for list_conversations()'s ordering exactly
        # like a non-streamed one does.
        full_text = "".join(full_text_parts)
        if full_text:
            async with session_factory() as session:
                try:
                    conversation_service = ConversationService(
                        ConversationRepository(session),
                        MessageRepository(session),
                        max_history_tokens=settings.max_history_tokens,
                    )
                    await conversation_service.append_message(
                        conversation_id=conversation_id,
                        role=MessageRole.ASSISTANT.value,
                        content=full_text,
                    )
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise

    # Sent only on natural completion — a cancelled or failed stream ends
    # without this event, which is itself how a well-behaved client tells
    # "the server finished normally" apart from "the connection dropped."
    yield _sse_event(
        {
            "done": True,
            "tool_used": tool_used,
            "citations": [
                {
                    "document_id": str(citation.document_id),
                    "document_name": citation.document_name,
                    "chunk_index": citation.chunk_index,
                    "page_number": citation.page_number,
                }
                for citation in citations
            ],
        }
    )


@router.post("/stream")
async def ask_stream(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
    session_factory=Depends(get_session_factory),
):
    """Returns a StreamingResponse instead of a normal JSON response
    because the whole point of streaming is sending bytes to the client
    AS THEY become available, rather than waiting for the complete
    answer and sending it all at once. A normal response_model-based
    JSON response can only be constructed and sent after the handler
    function has the ENTIRE object in hand — exactly what defeats
    streaming's purpose (the client would wait just as long either way).
    StreamingResponse instead takes an async generator and sends each
    yielded chunk to the client the moment it's produced.
    """
    try:
        conversation, tool_used, citations, token_stream = await service.ask_stream(
            owner_id=current_user.id,
            question=payload.question,
            conversation_id=payload.conversation_id,
        )
    except EmptyQuestionError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Question cannot be empty."
        ) from error
    except ConversationNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found."
        ) from error

    return StreamingResponse(
        _stream_chat_response(
            conversation_id=conversation.id,
            tool_used=tool_used,
            citations=citations,
            token_stream=token_stream,
            session_factory=session_factory,
        ),
        media_type="text/event-stream",
        headers={"X-Conversation-ID": str(conversation.id)},
    )
