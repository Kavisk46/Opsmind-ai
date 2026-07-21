import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from api.dependencies import get_current_user, get_document_service
from models.user import User
from schemas.document import DocumentResponse
from services.document_service import (
    DocumentNotFoundError,
    DocumentService,
    EmptyFileError,
    FileTooLargeError,
)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
):
    # UploadFile streams to a spooled temp file as FastAPI parses the
    # request; .read() here is the one point we pull the full contents
    # into memory, right before handing them to the storage backend.
    data = await file.read()
    try:
        return await service.upload_document(
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
