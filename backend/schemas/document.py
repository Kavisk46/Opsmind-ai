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
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
