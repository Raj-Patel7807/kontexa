"""FastAPI route handlers for workspaces, memberships, and projects."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Path, status

from kontexa.api.deps import (
    get_current_user,
    get_workspace_service,
    require_csrf,
)
from kontexa.database.models.users import User
from kontexa.schemas.workspaces import (
    AddMemberRequest,
    ProjectCreateRequest,
    ProjectResponse,
    ProjectUpdateRequest,
    UpdateMemberRoleRequest,
    WorkspaceCreateRequest,
    WorkspaceDetailResponse,
    WorkspaceMemberResponse,
    WorkspaceResponse,
    WorkspaceUpdateRequest,
)
from kontexa.services.workspaces import WorkspaceService

router = APIRouter(prefix="/workspaces", tags=["Workspaces & Projects"])


# --- Workspace Routes ---


@router.get("", response_model=list[WorkspaceDetailResponse], summary="List user workspaces")
async def list_workspaces(
    user: Annotated[User, Depends(get_current_user)],
    ws_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> list[dict]:
    """List all workspaces where the authenticated user is an active member."""
    return await ws_service.list_workspaces_for_user(user.id)


@router.post(
    "",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
    summary="Create a new workspace",
)
async def create_workspace(
    payload: WorkspaceCreateRequest,
    user: Annotated[User, Depends(get_current_user)],
    ws_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> WorkspaceResponse:
    """Create a new workspace with the authenticated user designated as Owner."""
    workspace = await ws_service.create_workspace(user_id=user.id, payload=payload)
    return WorkspaceResponse.model_validate(workspace)


@router.get(
    "/{workspace_id}",
    response_model=WorkspaceDetailResponse,
    summary="Get workspace details",
)
async def get_workspace(
    workspace_id: Annotated[uuid.UUID, Path(description="Target workspace identifier")],
    user: Annotated[User, Depends(get_current_user)],
    ws_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> dict:
    """Get workspace details, verifying membership and caller's role."""
    return await ws_service.get_workspace(workspace_id=workspace_id, user_id=user.id)


@router.patch(
    "/{workspace_id}",
    response_model=WorkspaceResponse,
    dependencies=[Depends(require_csrf)],
    summary="Update workspace settings",
)
async def update_workspace(
    workspace_id: Annotated[uuid.UUID, Path(description="Target workspace identifier")],
    payload: WorkspaceUpdateRequest,
    user: Annotated[User, Depends(get_current_user)],
    ws_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> WorkspaceResponse:
    """Update workspace name or slug. Requires Admin or Owner role."""
    workspace = await ws_service.update_workspace(
        workspace_id=workspace_id, user_id=user.id, payload=payload
    )
    return WorkspaceResponse.model_validate(workspace)


@router.delete(
    "/{workspace_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
    summary="Delete workspace",
)
async def delete_workspace(
    workspace_id: Annotated[uuid.UUID, Path(description="Target workspace identifier")],
    user: Annotated[User, Depends(get_current_user)],
    ws_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> None:
    """Soft delete a workspace. Only the Owner can delete a workspace."""
    await ws_service.soft_delete_workspace(workspace_id=workspace_id, user_id=user.id)


# --- Workspace Membership Routes ---


@router.get(
    "/{workspace_id}/members",
    response_model=list[WorkspaceMemberResponse],
    summary="List workspace members",
)
async def list_members(
    workspace_id: Annotated[uuid.UUID, Path(description="Target workspace identifier")],
    user: Annotated[User, Depends(get_current_user)],
    ws_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> list[WorkspaceMemberResponse]:
    """List all members of a workspace."""
    return await ws_service.list_workspace_members(workspace_id=workspace_id, user_id=user.id)


@router.post(
    "/{workspace_id}/members",
    response_model=WorkspaceMemberResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
    summary="Add member to workspace",
)
async def add_member(
    workspace_id: Annotated[uuid.UUID, Path(description="Target workspace identifier")],
    payload: AddMemberRequest,
    user: Annotated[User, Depends(get_current_user)],
    ws_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> WorkspaceMemberResponse:
    """Add a registered user to the workspace. Requires Admin or Owner."""
    return await ws_service.add_workspace_member(
        workspace_id=workspace_id, user_id=user.id, payload=payload
    )


@router.patch(
    "/{workspace_id}/members/{target_user_id}",
    response_model=WorkspaceMemberResponse,
    dependencies=[Depends(require_csrf)],
    summary="Update member role",
)
async def update_member_role(
    workspace_id: Annotated[uuid.UUID, Path(description="Target workspace identifier")],
    target_user_id: Annotated[uuid.UUID, Path(description="Target member user identifier")],
    payload: UpdateMemberRoleRequest,
    user: Annotated[User, Depends(get_current_user)],
    ws_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> WorkspaceMemberResponse:
    """Update a member's role. Requires Admin or Owner."""
    return await ws_service.update_member_role(
        workspace_id=workspace_id,
        user_id=user.id,
        target_user_id=target_user_id,
        new_role=payload.role,
    )


@router.delete(
    "/{workspace_id}/members/{target_user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
    summary="Remove member from workspace",
)
async def remove_member(
    workspace_id: Annotated[uuid.UUID, Path(description="Target workspace identifier")],
    target_user_id: Annotated[uuid.UUID, Path(description="Target member user identifier")],
    user: Annotated[User, Depends(get_current_user)],
    ws_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> None:
    """Remove a member or leave workspace. Requires Admin/Owner unless removing oneself."""
    await ws_service.remove_workspace_member(
        workspace_id=workspace_id, user_id=user.id, target_user_id=target_user_id
    )


# --- Workspace Project Routes ---


@router.get(
    "/{workspace_id}/projects",
    response_model=list[ProjectResponse],
    summary="List workspace projects",
)
async def list_projects(
    workspace_id: Annotated[uuid.UUID, Path(description="Target workspace identifier")],
    user: Annotated[User, Depends(get_current_user)],
    ws_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> list[ProjectResponse]:
    """List all projects scoped to the workspace."""
    projects = await ws_service.list_projects(workspace_id=workspace_id, user_id=user.id)
    return [ProjectResponse.model_validate(p) for p in projects]


@router.post(
    "/{workspace_id}/projects",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
    summary="Create project in workspace",
)
async def create_project(
    workspace_id: Annotated[uuid.UUID, Path(description="Target workspace identifier")],
    payload: ProjectCreateRequest,
    user: Annotated[User, Depends(get_current_user)],
    ws_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> ProjectResponse:
    """Create a new project. Requires Member or higher role in workspace."""
    project = await ws_service.create_project(
        workspace_id=workspace_id, user_id=user.id, payload=payload
    )
    return ProjectResponse.model_validate(project)


@router.get(
    "/{workspace_id}/projects/{project_id}",
    response_model=ProjectResponse,
    summary="Get project by ID",
)
async def get_project(
    workspace_id: Annotated[uuid.UUID, Path(description="Target workspace identifier")],
    project_id: Annotated[uuid.UUID, Path(description="Target project identifier")],
    user: Annotated[User, Depends(get_current_user)],
    ws_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> ProjectResponse:
    """Get project details ensuring strict workspace tenancy."""
    project = await ws_service.get_project(
        workspace_id=workspace_id, project_id=project_id, user_id=user.id
    )
    return ProjectResponse.model_validate(project)


@router.patch(
    "/{workspace_id}/projects/{project_id}",
    response_model=ProjectResponse,
    dependencies=[Depends(require_csrf)],
    summary="Update project details",
)
async def update_project(
    workspace_id: Annotated[uuid.UUID, Path(description="Target workspace identifier")],
    project_id: Annotated[uuid.UUID, Path(description="Target project identifier")],
    payload: ProjectUpdateRequest,
    user: Annotated[User, Depends(get_current_user)],
    ws_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> ProjectResponse:
    """Update project details. Requires Member or higher."""
    project = await ws_service.update_project(
        workspace_id=workspace_id,
        project_id=project_id,
        user_id=user.id,
        payload=payload,
    )
    return ProjectResponse.model_validate(project)


@router.delete(
    "/{workspace_id}/projects/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
    summary="Delete project",
)
async def delete_project(
    workspace_id: Annotated[uuid.UUID, Path(description="Target workspace identifier")],
    project_id: Annotated[uuid.UUID, Path(description="Target project identifier")],
    user: Annotated[User, Depends(get_current_user)],
    ws_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> None:
    """Soft delete a project. Requires Admin or Owner role."""
    await ws_service.soft_delete_project(
        workspace_id=workspace_id, project_id=project_id, user_id=user.id
    )
