"""Workspaces and projects domain service for tenancy isolation and resource management."""

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from kontexa.core.exceptions import ConflictError, PermissionDeniedError, ResourceNotFoundError
from kontexa.database.models.projects import Project
from kontexa.database.models.users import User
from kontexa.database.models.workspaces import Workspace, WorkspaceMember
from kontexa.schemas.workspaces import (
    ROLE_HIERARCHY,
    AddMemberRequest,
    ProjectCreateRequest,
    ProjectUpdateRequest,
    WorkspaceCreateRequest,
    WorkspaceMemberResponse,
    WorkspaceRole,
    WorkspaceUpdateRequest,
    generate_slug_from_name,
    has_required_role,
)

logger = logging.getLogger(__name__)


class WorkspaceService:
    """Service encapsulating tenant isolation, workspace CRUD, members, and project management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # --- Authorization & Membership Checking ---

    async def get_member_role(self, workspace_id: uuid.UUID, user_id: uuid.UUID) -> str | None:
        """Fetch the member's assigned role in the given workspace, or None if not a member."""
        query = select(WorkspaceMember.role).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def require_workspace_access(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        required_role: str = WorkspaceRole.VIEWER,
    ) -> str:
        """Verify user is an active member with at least required_role; raises 404 or 403."""
        # Check if workspace exists and is not soft-deleted
        ws_query = select(Workspace).where(
            Workspace.id == workspace_id,
            Workspace.deleted_at.is_(None),
        )
        ws_res = await self.db.execute(ws_query)
        workspace = ws_res.scalar_one_or_none()
        if not workspace:
            raise ResourceNotFoundError(f"Workspace {workspace_id} not found.")

        # Check membership
        user_role = await self.get_member_role(workspace_id, user_id)
        if not user_role:
            # Reject with ResourceNotFoundError to prevent existence probing across tenants
            raise ResourceNotFoundError(f"Workspace {workspace_id} not found.")

        if not has_required_role(user_role, required_role):
            raise PermissionDeniedError(
                f"Action requires role '{required_role}', but current role is '{user_role}'."
            )

        return user_role

    # --- Workspace Operations ---

    async def list_workspaces_for_user(self, user_id: uuid.UUID) -> list[dict]:
        """List all non-deleted workspaces where the user is an active member."""
        query = (
            select(Workspace, WorkspaceMember.role)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(
                WorkspaceMember.user_id == user_id,
                Workspace.deleted_at.is_(None),
            )
            .order_by(Workspace.created_at.desc())
        )
        result = await self.db.execute(query)
        rows = result.all()

        workspaces_with_roles = []
        for workspace, role in rows:
            workspaces_with_roles.append(
                {
                    "id": workspace.id,
                    "name": workspace.name,
                    "slug": workspace.slug,
                    "created_at": workspace.created_at,
                    "updated_at": workspace.updated_at,
                    "current_user_role": role,
                }
            )
        return workspaces_with_roles

    async def get_workspace(self, workspace_id: uuid.UUID, user_id: uuid.UUID) -> dict:
        """Get workspace detail with caller's verified role and total member count."""
        role = await self.require_workspace_access(
            workspace_id, user_id, required_role=WorkspaceRole.VIEWER
        )

        query = select(Workspace).where(Workspace.id == workspace_id)
        res = await self.db.execute(query)
        workspace = res.scalar_one()

        count_query = select(func.count(WorkspaceMember.user_id)).where(
            WorkspaceMember.workspace_id == workspace_id
        )
        count_res = await self.db.execute(count_query)
        member_count = count_res.scalar_one() or 1

        return {
            "id": workspace.id,
            "name": workspace.name,
            "slug": workspace.slug,
            "created_at": workspace.created_at,
            "updated_at": workspace.updated_at,
            "current_user_role": role,
            "member_count": member_count,
        }

    async def create_workspace(
        self, user_id: uuid.UUID, payload: WorkspaceCreateRequest
    ) -> Workspace:
        """Create a workspace and automatically assign caller as Owner."""
        slug = payload.slug or generate_slug_from_name(payload.name)

        # Check slug collision
        existing_query = select(Workspace.id).where(
            Workspace.slug == slug, Workspace.deleted_at.is_(None)
        )
        res = await self.db.execute(existing_query)
        if res.scalar_one_or_none():
            raise ConflictError(f"Workspace with slug '{slug}' already exists.")

        workspace = Workspace(
            name=payload.name,
            slug=slug,
        )
        self.db.add(workspace)
        await self.db.flush()

        # Add creator as OWNER
        member = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=user_id,
            role=WorkspaceRole.OWNER,
        )
        self.db.add(member)
        await self.db.commit()
        await self.db.refresh(workspace)
        return workspace

    async def update_workspace(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: WorkspaceUpdateRequest,
    ) -> Workspace:
        """Update workspace name or slug. Requires ADMIN or OWNER role."""
        await self.require_workspace_access(
            workspace_id, user_id, required_role=WorkspaceRole.ADMIN
        )

        query = select(Workspace).where(
            Workspace.id == workspace_id, Workspace.deleted_at.is_(None)
        )
        res = await self.db.execute(query)
        workspace = res.scalar_one()

        if payload.slug and payload.slug != workspace.slug:
            existing = await self.db.execute(
                select(Workspace.id).where(
                    Workspace.slug == payload.slug,
                    Workspace.id != workspace_id,
                    Workspace.deleted_at.is_(None),
                )
            )
            if existing.scalar_one_or_none():
                raise ConflictError(f"Workspace slug '{payload.slug}' is already taken.")
            workspace.slug = payload.slug

        if payload.name:
            workspace.name = payload.name

        workspace.updated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(workspace)
        return workspace

    async def soft_delete_workspace(self, workspace_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """Soft delete a workspace. Only the OWNER can delete a workspace."""
        await self.require_workspace_access(
            workspace_id, user_id, required_role=WorkspaceRole.OWNER
        )

        query = select(Workspace).where(
            Workspace.id == workspace_id, Workspace.deleted_at.is_(None)
        )
        res = await self.db.execute(query)
        workspace = res.scalar_one()

        workspace.deleted_at = datetime.now(UTC)
        await self.db.commit()

    # --- Membership Operations ---

    async def list_workspace_members(
        self, workspace_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[WorkspaceMemberResponse]:
        """List all members belonging to a workspace."""
        await self.require_workspace_access(
            workspace_id, user_id, required_role=WorkspaceRole.VIEWER
        )

        query = (
            select(
                WorkspaceMember.workspace_id,
                WorkspaceMember.user_id,
                WorkspaceMember.role,
                User.email,
                User.name,
            )
            .join(User, User.id == WorkspaceMember.user_id)
            .where(WorkspaceMember.workspace_id == workspace_id)
            .order_by(WorkspaceMember.role.desc(), User.name.asc())
        )
        result = await self.db.execute(query)
        rows = result.all()

        return [
            WorkspaceMemberResponse(
                workspace_id=row.workspace_id,
                user_id=row.user_id,
                email=row.email,
                name=row.name,
                role=row.role,
            )
            for row in rows
        ]

    async def add_workspace_member(
        self, workspace_id: uuid.UUID, user_id: uuid.UUID, payload: AddMemberRequest
    ) -> WorkspaceMemberResponse:
        """Add an existing user to a workspace by email. Requires ADMIN or OWNER role."""
        caller_role = await self.require_workspace_access(
            workspace_id, user_id, required_role=WorkspaceRole.ADMIN
        )

        target_role = payload.role.lower()
        if target_role not in ROLE_HIERARCHY:
            raise ConflictError(f"Invalid role '{payload.role}'.")

        # Admin cannot create Owners
        if target_role == WorkspaceRole.OWNER and caller_role != WorkspaceRole.OWNER:
            raise PermissionDeniedError("Only an existing Owner can assign the Owner role.")

        user_query = select(User).where(User.email == payload.email.lower().strip())
        user_res = await self.db.execute(user_query)
        target_user = user_res.scalar_one_or_none()
        if not target_user:
            raise ResourceNotFoundError(f"No registered user found with email '{payload.email}'.")

        # Check existing membership
        existing_member = await self.get_member_role(workspace_id, target_user.id)
        if existing_member:
            raise ConflictError("User is already a member of this workspace.")

        member = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=target_user.id,
            role=target_role,
        )
        self.db.add(member)
        await self.db.commit()

        return WorkspaceMemberResponse(
            workspace_id=workspace_id,
            user_id=target_user.id,
            email=target_user.email,
            name=target_user.name,
            role=target_role,
        )

    async def update_member_role(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        target_user_id: uuid.UUID,
        new_role: str,
    ) -> WorkspaceMemberResponse:
        """Update a member's role. Requires ADMIN or OWNER. Cannot demote last Owner."""
        caller_role = await self.require_workspace_access(
            workspace_id, user_id, required_role=WorkspaceRole.ADMIN
        )
        new_role = new_role.lower()
        if new_role not in ROLE_HIERARCHY:
            raise ConflictError(f"Invalid role '{new_role}'.")

        target_role = await self.get_member_role(workspace_id, target_user_id)
        if not target_role:
            raise ResourceNotFoundError("Member not found in workspace.")

        if target_role == WorkspaceRole.OWNER and caller_role != WorkspaceRole.OWNER:
            raise PermissionDeniedError("Only owners can modify an owner's role.")

        if new_role == WorkspaceRole.OWNER and caller_role != WorkspaceRole.OWNER:
            raise PermissionDeniedError("Only owners can promote members to owner.")

        # Prevent demoting the last owner
        if target_role == WorkspaceRole.OWNER and new_role != WorkspaceRole.OWNER:
            owners_count_query = select(func.count(WorkspaceMember.user_id)).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.role == WorkspaceRole.OWNER,
            )
            owners_count = (await self.db.execute(owners_count_query)).scalar_one()
            if owners_count <= 1:
                raise ConflictError("Cannot demote the last owner of the workspace.")

        stmt = (
            update(WorkspaceMember)
            .where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == target_user_id,
            )
            .values(role=new_role)
        )
        await self.db.execute(stmt)
        await self.db.commit()

        user = (await self.db.execute(select(User).where(User.id == target_user_id))).scalar_one()

        return WorkspaceMemberResponse(
            workspace_id=workspace_id,
            user_id=target_user_id,
            email=user.email,
            name=user.name,
            role=new_role,
        )

    async def remove_workspace_member(
        self, workspace_id: uuid.UUID, user_id: uuid.UUID, target_user_id: uuid.UUID
    ) -> None:
        """Remove a member from a workspace. Admins can remove members, or users can self-leave."""
        caller_role = await self.require_workspace_access(
            workspace_id, user_id, required_role=WorkspaceRole.VIEWER
        )

        target_role = await self.get_member_role(workspace_id, target_user_id)
        if not target_role:
            raise ResourceNotFoundError("Member not found in workspace.")

        # If not self-leaving, require ADMIN+
        is_self = user_id == target_user_id
        if not is_self:
            if not has_required_role(caller_role, WorkspaceRole.ADMIN):
                raise PermissionDeniedError("Admin permission required to remove members.")
            if target_role == WorkspaceRole.OWNER and caller_role != WorkspaceRole.OWNER:
                raise PermissionDeniedError("Only an owner can remove another owner.")

        # Check if target is last owner
        if target_role == WorkspaceRole.OWNER:
            owners_count_query = select(func.count(WorkspaceMember.user_id)).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.role == WorkspaceRole.OWNER,
            )
            owners_count = (await self.db.execute(owners_count_query)).scalar_one()
            if owners_count <= 1:
                raise ConflictError("Cannot remove the last owner of the workspace.")

        stmt = delete(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == target_user_id,
        )
        await self.db.execute(stmt)
        await self.db.commit()

    # --- Project Operations ---

    async def list_projects(self, workspace_id: uuid.UUID, user_id: uuid.UUID) -> list[Project]:
        """List active non-deleted projects scoped strictly to the given workspace."""
        await self.require_workspace_access(
            workspace_id, user_id, required_role=WorkspaceRole.VIEWER
        )

        query = (
            select(Project)
            .where(
                Project.workspace_id == workspace_id,
                Project.deleted_at.is_(None),
            )
            .order_by(Project.created_at.desc())
        )
        res = await self.db.execute(query)
        return list(res.scalars().all())

    async def get_project(
        self, workspace_id: uuid.UUID, project_id: uuid.UUID, user_id: uuid.UUID
    ) -> Project:
        """Fetch project ensuring both workspace scoping and user access; raises 404 on mismatch."""
        await self.require_workspace_access(
            workspace_id, user_id, required_role=WorkspaceRole.VIEWER
        )

        query = select(Project).where(
            Project.id == project_id,
            Project.workspace_id == workspace_id,
            Project.deleted_at.is_(None),
        )
        res = await self.db.execute(query)
        project = res.scalar_one_or_none()
        if not project:
            raise ResourceNotFoundError(
                f"Project {project_id} not found in workspace {workspace_id}."
            )
        return project

    async def create_project(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: ProjectCreateRequest,
    ) -> Project:
        """Create a new project within a workspace. Requires MEMBER or above."""
        await self.require_workspace_access(
            workspace_id, user_id, required_role=WorkspaceRole.MEMBER
        )

        slug = payload.slug or generate_slug_from_name(payload.name)

        # Check unique constraint on (workspace_id, slug)
        existing_query = select(Project.id).where(
            Project.workspace_id == workspace_id,
            Project.slug == slug,
            Project.deleted_at.is_(None),
        )
        existing = (await self.db.execute(existing_query)).scalar_one_or_none()
        if existing:
            raise ConflictError(f"Project with slug '{slug}' already exists in this workspace.")

        project = Project(
            workspace_id=workspace_id,
            name=payload.name,
            slug=slug,
            description=payload.description,
            status="active",
        )
        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def update_project(
        self,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: ProjectUpdateRequest,
    ) -> Project:
        """Update project details. Requires MEMBER or above."""
        await self.require_workspace_access(
            workspace_id, user_id, required_role=WorkspaceRole.MEMBER
        )

        project = await self.get_project(workspace_id, project_id, user_id)

        if payload.slug and payload.slug != project.slug:
            existing = (
                await self.db.execute(
                    select(Project.id).where(
                        Project.workspace_id == workspace_id,
                        Project.slug == payload.slug,
                        Project.id != project_id,
                        Project.deleted_at.is_(None),
                    )
                )
            ).scalar_one_or_none()
            if existing:
                raise ConflictError(
                    f"Project slug '{payload.slug}' already exists in this workspace."
                )
            project.slug = payload.slug

        if payload.name:
            project.name = payload.name
        if payload.description is not None:
            project.description = payload.description
        if payload.status:
            project.status = payload.status

        project.updated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def soft_delete_project(
        self, workspace_id: uuid.UUID, project_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        """Soft delete a project. Requires ADMIN or OWNER."""
        await self.require_workspace_access(
            workspace_id, user_id, required_role=WorkspaceRole.ADMIN
        )

        project = await self.get_project(workspace_id, project_id, user_id)
        project.deleted_at = datetime.now(UTC)
        await self.db.commit()
