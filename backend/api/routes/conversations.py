import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import (
    get_conversation_service,
    get_current_user,
    require_workspace_permission,
)
from models.user import User
from models.workspace import Workspace
from schemas.conversation import (
    ConversationCreateRequest,
    ConversationDetailResponse,
    ConversationRenameRequest,
    ConversationResponse,
    MessageResponse,
)
from services.conversation_service import (
    ConversationNotFoundError,
    ConversationService,
    EmptyTitleError,
)
from services.workspace_service import WorkspacePermission

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: ConversationCreateRequest,
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(
        require_workspace_permission(WorkspacePermission.CHAT)
    ),
    service: ConversationService = Depends(get_conversation_service),
):
    # A dedicated "start a new, empty conversation" endpoint — distinct
    # from POST /chat's implicit creation, for a client that wants a
    # conversation to exist (e.g. to show in a sidebar) before the user
    # has typed a first question yet.
    return await service.get_or_create_conversation(
        owner_id=current_user.id,
        workspace_id=current_workspace.id,
        conversation_id=None,
        title_hint=payload.title or "New conversation",
    )


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
):
    return await service.list_conversations(owner_id=current_user.id)


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
):
    try:
        conversation, messages = await service.get_conversation_with_messages(
            owner_id=current_user.id, conversation_id=conversation_id
        )
    except ConversationNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found."
        ) from error

    return ConversationDetailResponse(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[
            MessageResponse(role=m.role, content=m.content, created_at=m.created_at)
            for m in messages
        ],
    )


@router.patch("/{conversation_id}", response_model=ConversationResponse)
async def rename_conversation(
    conversation_id: uuid.UUID,
    payload: ConversationRenameRequest,
    current_user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
):
    try:
        return await service.rename_conversation(
            owner_id=current_user.id,
            conversation_id=conversation_id,
            title=payload.title,
        )
    except EmptyTitleError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Title cannot be empty."
        ) from error
    except ConversationNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found."
        ) from error


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
):
    try:
        await service.delete_conversation(
            owner_id=current_user.id, conversation_id=conversation_id
        )
    except ConversationNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found."
        ) from error
