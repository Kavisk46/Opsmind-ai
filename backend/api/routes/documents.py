import uuid

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    UploadFile,
    status,
)

from api.dependencies import get_current_user, get_document_service, get_ingestion_service
from models.user import User
from schemas.document import DocumentResponse, DocumentStatusResponse
from services.document_service import (
    DocumentNotFoundError,
    DocumentService,
    EmptyFileError,
    FileTooLargeError,
)
from services.ingestion_service import IngestionService

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
    ingestion_service: IngestionService = Depends(get_ingestion_service),
):
    # UploadFile streams to a spooled temp file as FastAPI parses the
    # request; .read() here is the one point we pull the full contents
    # into memory, right before handing them to the storage backend.
    data = await file.read()
    try:
        document = await service.upload_document(
            owner_id=current_user.id,
            filename=file.filename or "untitled",
            content_type=file.content_type or "application/octet-stream",
            data=data,
        )
    except EmptyFileError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty."
        ) from error
    except FileTooLargeError as error:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Uploaded file exceeds the maximum allowed size.",
        ) from error

    # Scheduled to run AFTER this response is sent — the client gets 202
    # immediately, without waiting for chunking/embedding to finish.
    # ingestion_service was already built via its own Depends() above
    # (using a session FACTORY, not this request's session — see
    # IngestionService's docstring), so it's safe to hand its method
    # straight to add_task: nothing here depends on this request's
    # transaction still being open.
    background_tasks.add_task(ingestion_service.process_document, document.id)

    # 202, not 201: the Document ROW is fully created (201's usual
    # meaning), but the resource isn't yet in its final state — real
    # ingestion work is still pending, which is exactly what 202 Accepted
    # means ("the request has been accepted for processing, but the
    # processing has not been completed"). A client that wants to know
    # when it's actually done polls GET /documents/{id}/status.
    return document


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    current_user: User = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
):
    return await service.list_documents(owner_id=current_user.id)


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
):
    try:
        return await service.get_document(
            owner_id=current_user.id, document_id=document_id
        )
    except DocumentNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found."
        ) from error


@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
):
    # A route of its own, not just a field on GET /documents/{id} — this
    # is the endpoint meant to be polled repeatedly while a document is
    # UPLOADED/PROCESSING/EMBEDDING, so it returns only what actually
    # changes during that window (see DocumentStatusResponse's docstring
    # for why that's a deliberately smaller payload).
    try:
        return await service.get_document(
            owner_id=current_user.id, document_id=document_id
        )
    except DocumentNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found."
        ) from error


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
):
    # 204: success, deliberately no body — there's nothing left to return
    # once a resource is gone. Same DocumentNotFoundError -> 404 mapping as
    # every other document route, so deleting someone else's document (or
    # a nonexistent ID) is indistinguishable from either case.
    try:
        await service.delete_document(
            owner_id=current_user.id, document_id=document_id
        )
    except DocumentNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found."
        ) from error
