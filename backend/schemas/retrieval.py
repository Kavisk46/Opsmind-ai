import uuid

from pydantic import BaseModel, ConfigDict


class RetrievalSearchRequest(BaseModel):
    question: str
    # None means "use settings.retrieval_top_k" — see the route. A
    # client-supplied value lets a caller ask for a wider/narrower
    # candidate pool per-request without this becoming a server
    # reconfiguration.
    top_k: int | None = None


class CitationResponse(BaseModel):
    document_id: uuid.UUID
    filename: str
    chunk_index: int
    page_number: int | None

    model_config = ConfigDict(from_attributes=True)


class RetrievedChunkResponse(BaseModel):
    """API-facing shape for one ranked chunk, scores included — this is
    what makes "retrieved chunks + scores" (this phase's own requirement)
    inspectable by a caller, distinct from the assembled `context` string,
    which is what an LLM would actually be given.
    """

    document_id: uuid.UUID
    chunk_index: int
    page_number: int | None
    filename: str
    text: str
    vector_score: float | None
    keyword_score: float | None
    combined_score: float

    model_config = ConfigDict(from_attributes=True)


class RetrievalSearchResponse(BaseModel):
    context: str
    citations: list[CitationResponse]
    chunks: list[RetrievedChunkResponse]
