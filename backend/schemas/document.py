import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    """API-facing contract for a document. Deliberately excludes
    storage_key — that's an internal detail of where bytes live, never
    something a client needs or should be able to guess at.
    """

    id: uuid.UUID
    filename: str
    content_type: str
    size_bytes: int
    status: str
    error_message: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentStatusResponse(BaseModel):
    """A deliberately lighter response than DocumentResponse — for a
    client polling GET /documents/{id}/status frequently while waiting on
    ingestion, sending back filename/content_type/size_bytes on every
    poll is wasted bandwidth for data that never changes mid-processing.
    Only the fields that actually change over the document's lifecycle.
    """

    id: uuid.UUID
    status: str
    error_message: str | None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
