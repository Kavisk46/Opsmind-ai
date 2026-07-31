import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_current_user, get_workspace_service
from models.user import User
from schemas.workspace import (
    AddWorkspaceMemberRequest,
    ChangeWorkspaceMemberRoleRequest,
    WorkspaceCreateRequest,
    WorkspaceMemberResponse,
    WorkspaceRenameRequest,
    WorkspaceResponse,
)
from services.workspace_service import (
    EmptyWorkspaceNameError,
    InsufficientWorkspacePermissionError,
    LastOwnerError,
    NotAWorkspaceMemberError,
    WorkspaceNotFoundError,
    WorkspaceService,
)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    payload: WorkspaceCreateRequest,
    current_user: User = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service),
):
    try:
        return await service.create_workspace(
            owner_id=current_user.id, name=payload.name, description=payload.description
        )
    except EmptyWorkspaceNameError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Workspace name cannot be empty."
        ) from error


@router.get("", response_model=list[WorkspaceResponse])
async def list_workspaces(
    current_user: User = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service),
):
    return await service.list_workspaces_for_user(current_user.id)


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service),
):
    try:
        return await service.get_workspace(user_id=current_user.id, workspace_id=workspace_id)
    except WorkspaceNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found."
        ) from error


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
async def rename_workspace(
    workspace_id: uuid.UUID,
    payload: WorkspaceRenameRequest,
    current_user: User = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service),
):
    try:
        return await service.rename_workspace(
            user_id=current_user.id, workspace_id=workspace_id, name=payload.name
        )
    except EmptyWorkspaceNameError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Workspace name cannot be empty."
        ) from error
    except WorkspaceNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found."
        ) from error
    except InsufficientWorkspacePermissionError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to change this workspace's settings.",
        ) from error


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service),
):
    try:
        await service.delete_workspace(user_id=current_user.id, workspace_id=workspace_id)
    except WorkspaceNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found."
        ) from error
    except InsufficientWorkspacePermissionError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the workspace owner can delete it.",
        ) from error


@router.get("/{workspace_id}/members", response_model=list[WorkspaceMemberResponse])
async def list_workspace_members(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service),
):
    try:
        return await service.list_members(user_id=current_user.id, workspace_id=workspace_id)
    except WorkspaceNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found."
        ) from error


@router.post(
    "/{workspace_id}/members",
    response_model=WorkspaceMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_workspace_member(
    workspace_id: uuid.UUID,
    payload: AddWorkspaceMemberRequest,
    current_user: User = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service),
):
    try:
        return await service.add_member(
            actor_user_id=current_user.id,
            workspace_id=workspace_id,
            new_member_user_id=payload.user_id,
            role=payload.role,
        )
    except WorkspaceNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found."
        ) from error
    except InsufficientWorkspacePermissionError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage members in this workspace.",
        ) from error


@router.patch(
    "/{workspace_id}/members/{user_id}", response_model=WorkspaceMemberResponse
)
async def change_workspace_member_role(
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: ChangeWorkspaceMemberRoleRequest,
    current_user: User = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service),
):
    try:
        return await service.change_member_role(
            actor_user_id=current_user.id,
            workspace_id=workspace_id,
            target_user_id=user_id,
            new_role=payload.role,
        )
    except WorkspaceNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found."
        ) from error
    except NotAWorkspaceMemberError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="That user is not a member."
        ) from error
    except InsufficientWorkspacePermissionError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage members in this workspace.",
        ) from error
    except LastOwnerError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A workspace must always have at least one owner.",
        ) from error


@router.delete("/{workspace_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_workspace_member(
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service),
):
    try:
        await service.remove_member(
            actor_user_id=current_user.id, workspace_id=workspace_id, target_user_id=user_id
        )
    except WorkspaceNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found."
        ) from error
    except NotAWorkspaceMemberError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="That user is not a member."
        ) from error
    except InsufficientWorkspacePermissionError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage members in this workspace.",
        ) from error
    except LastOwnerError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A workspace must always have at least one owner.",
        ) from error
