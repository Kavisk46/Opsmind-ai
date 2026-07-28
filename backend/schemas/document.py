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


class DocumentStatsResponse(BaseModel):
    """API-facing contract for GET /documents/stats. Mirrors
    services.document_service.DocumentStats field-for-field —
    from_attributes lets this validate directly off that dataclass
    (including recursively converting its `recent_uploads` list of real
    Document ORM rows into DocumentResponse instances), no manual mapping
    step needed in the route.
    """

    total_documents: int
    total_storage_bytes: int
    documents_by_type: dict[str, int]
    recent_uploads: list[DocumentResponse]

    model_config = ConfigDict(from_attributes=True)
