import json
import time
import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from api.dependencies import (
    get_ask_service,
    get_chat_service,
    get_current_user,
    get_session_factory,
    require_workspace_permission,
)
from core.config import settings
from core.logging import logger
from models.message import MessageRole
from models.user import User
from models.workspace import Workspace
from repositories.conversation_repository import ConversationRepository
from repositories.message_repository import MessageRepository
from schemas.chat import (
    AskCitationResponse,
    AskRequest,
    AskResponse,
    ChatRequest,
    ChatResponse,
    CitationResponse,
)
from services.ask_service import AskService
from services.ask_service import EmptyQuestionError as AskEmptyQuestionError
from services.chat_service import ChatService, ConversationNotFoundError, EmptyQuestionError
from services.conversation_service import ConversationService
from services.llm.errors import (
    ProviderNetworkError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from services.tools import Citation
from services.workspace_service import WorkspacePermission

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def ask(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(
        require_workspace_permission(WorkspacePermission.CHAT)
    ),
    service: ChatService = Depends(get_chat_service),
):
    try:
        conversation, result = await service.ask(
            owner_id=current_user.id,
            workspace_id=current_workspace.id,
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
    except ProviderRateLimitError as error:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="The AI provider is rate-limiting requests. Please try again shortly.",
        ) from error
    except ProviderTimeoutError as error:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="The AI provider took too long to respond.",
        ) from error
    except ProviderNetworkError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not reach the AI provider.",
        ) from error
    except ProviderUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The AI provider is currently unavailable.",
        ) from error

    return ChatResponse(
        conversation_id=conversation.id,
        answer=result.answer,
        tool_used=result.tool_used,
        latency_ms=result.latency_ms,
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


@router.post("/ask", response_model=AskResponse)
async def ask_question(
    payload: AskRequest,
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(
        require_workspace_permission(WorkspacePermission.CHAT)
    ),
    ask_service: AskService = Depends(get_ask_service),
):
    """A stateless sibling to POST /chat above — Planner -> Retriever ->
    Context Builder -> Prompt Builder -> LLM -> Citations, with no
    conversation created or persisted (see AskService's own docstring
    for why that split is deliberate). current_workspace is still
    required — same CHAT permission gate as every other question-
    answering route — even though AskService itself never touches
    workspace_id, for the same reason api/routes/documents.py enforces
    permissions before ever reaching DocumentService: authorization is
    the route's job, not each service's.
    """
    try:
        result = await ask_service.ask(question=payload.question, owner_id=current_user.id)
    except AskEmptyQuestionError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Question cannot be empty."
        ) from error
    except ProviderRateLimitError as error:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="The AI provider is rate-limiting requests. Please try again shortly.",
        ) from error
    except ProviderTimeoutError as error:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="The AI provider took too long to respond.",
        ) from error
    except ProviderNetworkError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not reach the AI provider.",
        ) from error
    except ProviderUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The AI provider is currently unavailable.",
        ) from error

    return AskResponse(
        answer=result.answer,
        confidence=result.confidence,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        latency_ms=result.latency_ms,
        citations=[
            AskCitationResponse(
                document_id=citation.document_id,
                filename=citation.filename,
                chunk_index=citation.chunk_index,
                page_number=citation.page_number,
            )
            for citation in result.citations
        ],
    )


def _sse_error_message(error: Exception) -> str:
    """A best-effort, human-readable message for the SSE `{"error": ...}`
    frame — varies by exception type without changing that frame's wire
    shape at all (still exactly one string field; the frontend's existing
    ChatStreamFrame parsing — see chat-api.ts — needs zero changes). By
    the time any exception reaches here, a 200 response has already been
    sent (see ask_stream()'s own docstring on why the non-streaming
    route can still choose a real HTTP status but this one cannot), so a
    distinguishing MESSAGE is the only signal left to give the client.
    """
    if isinstance(error, ProviderRateLimitError):
        return "The AI provider is rate-limiting requests. Please try again shortly."
    if isinstance(error, ProviderTimeoutError):
        return "The AI provider took too long to respond."
    if isinstance(error, ProviderNetworkError):
        return "Could not reach the AI provider."
    if isinstance(error, ProviderUnavailableError):
        return "The AI provider is currently unavailable."
    return "The response could not be completed."


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
    stream_start_time = time.perf_counter()
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
        yield _sse_event({"error": _sse_error_message(error)})
        raise
    finally:
        # End-to-end route-level duration — distinct from OpenAIProvider/
        # AnthropicProvider's own generate_stream() duration logging
        # (services/llm/*_provider.py), which only times the SDK call
        # itself, not this route's full lifetime (SSE framing, the final
        # persistence below, etc).
        stream_duration_ms = round((time.perf_counter() - stream_start_time) * 1000, 2)
        logger.info(
            "Chat stream %s",
            status_label,
            extra={"tool": tool_used, "duration_ms": stream_duration_ms},
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
                        # No token counts here — unlike ask()'s metadata,
                        # a streamed reply's usage is never captured (see
                        # AIOrchestrator.handle_stream()'s own docstring
                        # on why LLM-level metrics aren't recorded for
                        # this path). provider/model/tool_used are still
                        # known up front, before streaming even starts.
                        metadata={
                            "tool_used": tool_used,
                            "provider": settings.llm_provider,
                            "model": settings.llm_model_name,
                            "prompt_tokens": None,
                            "completion_tokens": None,
                        },
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
    current_workspace: Workspace = Depends(
        require_workspace_permission(WorkspacePermission.CHAT)
    ),
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
    if not settings.streaming_enabled:
        # Checked BEFORE any retrieval/conversation work starts — a
        # disabled-streaming deployment shouldn't pay for a real
        # ConversationService round trip just to then refuse the request.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Streaming is currently disabled on this server.",
        )

    try:
        conversation, tool_used, citations, token_stream = await service.ask_stream(
            owner_id=current_user.id,
            workspace_id=current_workspace.id,
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
