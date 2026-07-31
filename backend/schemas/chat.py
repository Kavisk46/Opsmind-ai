import uuid

from pydantic import BaseModel


class ChatRequest(BaseModel):
    """conversation_id is optional: omit it to start a new conversation,
    pass one back to continue an existing one — the same "create or
    continue" pattern used nowhere else in this API yet, since chat is
    the first feature with genuinely multi-turn state.
    """

    question: str
    conversation_id: uuid.UUID | None = None


class CitationResponse(BaseModel):
    document_id: uuid.UUID
    document_name: str
    chunk_index: int
    page_number: int | None


class AskRequest(BaseModel):
    """No conversation_id — POST /chat/ask (services/ask_service.py) is
    deliberately stateless, unlike ChatRequest above; there is nothing
    to continue.
    """

    question: str


class AskCitationResponse(BaseModel):
    """Mirrors services/citation_service.py's Citation shape directly
    (document_id/filename/chunk_index/page_number) — deliberately NOT
    CitationResponse above, which mirrors a different, chat-specific
    Citation type (services/tools.py) with a document_name field instead
    of filename. Two independently-evolving response shapes for two
    independently-evolving citation types, not one shared schema
    papering over a difference that already exists in the service layer.
    """

    document_id: uuid.UUID
    filename: str
    chunk_index: int
    page_number: int | None


class AskResponse(BaseModel):
    answer: str
    citations: list[AskCitationResponse]
    # Mean relevance score of the chunks actually used to ground this
    # answer — see AskResult's own docstring (services/ask_service.py)
    # for exactly how this is computed. 0.0, not null, when nothing was
    # retrieved — a real, meaningful value ("no confidence"), not a
    # missing one.
    confidence: float
    prompt_tokens: int | None
    completion_tokens: int | None
    latency_ms: float


class ChatResponse(BaseModel):
    conversation_id: uuid.UUID
    answer: str
    citations: list[CitationResponse]
    # Which tool the orchestrator routed this question to — surfaced
    # mainly for transparency/debugging (a client or developer can see
    # WHY an answer looks the way it does, e.g. "document_metadata" vs
    # "rag_retrieval"), not something a caller is expected to act on.
    tool_used: str
    # Total time from routing through LLM generation, in milliseconds —
    # already measured internally (AIOrchestrator.handle) and sent to
    # AIMetricsService, now also surfaced on the response itself so a
    # client doesn't need scrape access to /metrics just to show "answered
    # in 1.2s."
    latency_ms: float
