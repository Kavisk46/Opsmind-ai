import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from models.workspace_member import WorkspaceRole


class WorkspaceCreateRequest(BaseModel):
    name: str
    description: str | None = None


class WorkspaceRenameRequest(BaseModel):
    name: str


class WorkspaceResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkspaceMemberResponse(BaseModel):
    user_id: uuid.UUID
    role: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AddWorkspaceMemberRequest(BaseModel):
    user_id: uuid.UUID
    role: WorkspaceRole = WorkspaceRole.VIEWER


class ChangeWorkspaceMemberRoleRequest(BaseModel):
    role: WorkspaceRole
