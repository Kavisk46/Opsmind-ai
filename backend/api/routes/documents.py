import uuid

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import Response

from api.dependencies import (
    get_current_user,
    get_current_workspace,
    get_document_service,
    get_ingestion_service,
    require_workspace_permission,
)
from models.user import User
from models.workspace import Workspace
from repositories.document_repository import SortOption
from schemas.document import DocumentResponse, DocumentStatsResponse, DocumentStatusResponse
from services.document_service import (
    DocumentNotFoundError,
    DocumentService,
    DuplicateFilenameError,
    EmptyFileError,
    FileTooLargeError,
    UnsupportedFileTypeError,
)
from services.ingestion_service import IngestionService
from services.workspace_service import WorkspacePermission

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(
        require_workspace_permission(WorkspacePermission.UPLOAD)
    ),
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
            workspace_id=current_workspace.id,
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
    except UnsupportedFileTypeError as error:
        # 415, not 400 — the request itself is well-formed; specifically
        # its PAYLOAD's media type is what's unsupported, which is
        # exactly what 415 Unsupported Media Type means.
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                "Unsupported file type. Supported types: .txt, .md, .pdf, "
                ".docx, .csv, .png, .jpg, .jpeg."
            ),
        ) from error
    except DuplicateFilenameError as error:
        # 409 Conflict: the request is well-formed and the file type is
        # fine — it's specifically the current STATE (an existing document
        # with this exact name) that makes it impossible to fulfill as-is,
        # which is exactly what 409 means as opposed to 400/415.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(error)
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
    current_workspace: Workspace = Depends(get_current_workspace),
    service: DocumentService = Depends(get_document_service),
):
    return await service.list_documents(workspace_id=current_workspace.id)


# Declared BEFORE /{document_id} deliberately — FastAPI matches routes in
# declaration order, and both "/search" and "/stats" are otherwise
# indistinguishable, path-shape-wise, from a request for
# /documents/{document_id}. Declared after it, either would 422 trying
# to parse "search"/"stats" as a UUID instead of ever reaching this
# handler.
@router.get("/search", response_model=list[DocumentResponse])
async def search_documents(
    q: str | None = Query(default=None, description="Matched against filename, case-insensitive."),
    content_type: str | None = Query(default=None, description="Exact MIME type filter."),
    sort: SortOption = Query(default="newest"),
    current_workspace: Workspace = Depends(get_current_workspace),
    service: DocumentService = Depends(get_document_service),
):
    return await service.search_documents(
        workspace_id=current_workspace.id, query=q, content_type=content_type, sort=sort
    )


@router.get("/stats", response_model=DocumentStatsResponse)
async def get_document_stats(
    current_workspace: Workspace = Depends(get_current_workspace),
    service: DocumentService = Depends(get_document_service),
):
    return await service.get_stats(workspace_id=current_workspace.id)


@router.get("/download/{document_id}")
async def download_document(
    document_id: uuid.UUID,
    current_workspace: Workspace = Depends(get_current_workspace),
    service: DocumentService = Depends(get_document_service),
):
    try:
        document, data = await service.download_document(
            workspace_id=current_workspace.id, document_id=document_id
        )
    except DocumentNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found."
        ) from error

    # filename is already sanitized at upload time (core/filenames.py) —
    # no control characters, no quote characters, nothing that could
    # break out of this header's quoted value or inject a second header.
    return Response(
        content=data,
        media_type=document.content_type,
        headers={"Content-Disposition": f'attachment; filename="{document.filename}"'},
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    current_workspace: Workspace = Depends(get_current_workspace),
    service: DocumentService = Depends(get_document_service),
):
    try:
        return await service.get_document(
            workspace_id=current_workspace.id, document_id=document_id
        )
    except DocumentNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found."
        ) from error


@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(
    document_id: uuid.UUID,
    current_workspace: Workspace = Depends(get_current_workspace),
    service: DocumentService = Depends(get_document_service),
):
    # A route of its own, not just a field on GET /documents/{id} — this
    # is the endpoint meant to be polled repeatedly while a document is
    # UPLOADED/PROCESSING/EMBEDDING, so it returns only what actually
    # changes during that window (see DocumentStatusResponse's docstring
    # for why that's a deliberately smaller payload).
    try:
        return await service.get_document(
            workspace_id=current_workspace.id, document_id=document_id
        )
    except DocumentNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found."
        ) from error


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    current_workspace: Workspace = Depends(
        require_workspace_permission(WorkspacePermission.DELETE)
    ),
    service: DocumentService = Depends(get_document_service),
):
    # 204: success, deliberately no body — there's nothing left to return
    # once a resource is gone. Same DocumentNotFoundError -> 404 mapping as
    # every other document route, so deleting a document outside this
    # workspace (or a nonexistent ID) is indistinguishable from either case.
    try:
        await service.delete_document(
            workspace_id=current_workspace.id, document_id=document_id
        )
    except DocumentNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found."
        ) from error
