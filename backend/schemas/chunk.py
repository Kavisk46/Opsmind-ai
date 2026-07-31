import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentChunkResponse(BaseModel):
    """API-facing contract for a document chunk. Not yet wired to any
    route — retrieval/chat endpoints that would actually return this
    belong to a later sprint; this exists now so the shape is typed and
    ready when they arrive.
    """

    id: uuid.UUID
    document_id: uuid.UUID
    chunk_index: int
    text: str
    token_count: int
    embedding_model: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
