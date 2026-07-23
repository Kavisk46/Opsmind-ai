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


class ChatResponse(BaseModel):
    conversation_id: uuid.UUID
    answer: str
    citations: list[CitationResponse]
    # Which tool the orchestrator routed this question to — surfaced
    # mainly for transparency/debugging (a client or developer can see
    # WHY an answer looks the way it does, e.g. "document_metadata" vs
    # "rag_retrieval"), not something a caller is expected to act on.
    tool_used: str
