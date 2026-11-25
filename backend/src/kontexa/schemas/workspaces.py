"""Pydantic schemas for workspaces, projects, memberships, and role-based access control."""

import re
import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

SlugString = Annotated[
    str,
    StringConstraints(
        min_length=2,
        max_length=64,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
        strip_whitespace=True,
    ),
]


class WorkspaceRole(str):
    """Supported workspace roles in ascending or defined hierarchy."""

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


ROLE_HIERARCHY: dict[str, int] = {
    WorkspaceRole.VIEWER: 10,
    WorkspaceRole.MEMBER: 20,
    WorkspaceRole.ADMIN: 30,
    WorkspaceRole.OWNER: 40,
}


def has_required_role(user_role: str, required_role: str) -> bool:
    """Evaluate whether user_role meets or exceeds required_role in the role hierarchy."""
    user_level = ROLE_HIERARCHY.get(user_role.lower(), 0)
    required_level = ROLE_HIERARCHY.get(required_role.lower(), 0)
    return user_level >= required_level


def generate_slug_from_name(name: str) -> str:
    """Generate a clean URL-friendly slug from a human-readable name."""
    clean = re.sub(r"[^\w\s-]", "", name.lower()).strip()
    slug = re.sub(r"[-\s]+", "-", clean)
    return slug[:64] if slug else "default"


# --- Workspace Schemas ---


class WorkspaceCreateRequest(BaseModel):
    """Payload to create a new workspace."""

    name: str = Field(min_length=2, max_length=100, description="Workspace display name")
    slug: SlugString | None = Field(
        default=None,
        description="Unique workspace URL slug. Auto-generated from name if omitted.",
    )


class WorkspaceUpdateRequest(BaseModel):
    """Payload to update an existing workspace's settings."""

    name: str | None = Field(
        default=None, min_length=2, max_length=100, description="Updated workspace name"
    )
    slug: SlugString | None = Field(default=None, description="Updated workspace slug")


class WorkspaceResponse(BaseModel):
    """Public representation of a workspace entity."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    created_at: datetime
    updated_at: datetime


class WorkspaceMemberResponse(BaseModel):
    """Public representation of a workspace member."""

    model_config = ConfigDict(from_attributes=True)

    workspace_id: uuid.UUID
    user_id: uuid.UUID
    email: str
    name: str | None
    role: str


class WorkspaceDetailResponse(WorkspaceResponse):
    """Workspace response enriched with member count and current user's role."""

    current_user_role: str
    member_count: int = 1


class AddMemberRequest(BaseModel):
    """Payload to add an existing registered user to a workspace by email."""

    email: str = Field(min_length=3, max_length=255, description="Registered user email")
    role: str = Field(default="member", description="Assigned role: owner, admin, member, viewer")


class UpdateMemberRoleRequest(BaseModel):
    """Payload to update a member's role within a workspace."""

    role: str = Field(description="New role: owner, admin, member, viewer")


# --- Project Schemas ---


class ProjectCreateRequest(BaseModel):
    """Payload to create a new project within a workspace."""

    name: str = Field(min_length=2, max_length=100, description="Project display name")
    slug: SlugString | None = Field(
        default=None,
        description="Project URL slug unique per workspace. Auto-generated from name if omitted.",
    )
    description: str | None = Field(
        default=None, max_length=1000, description="Optional project description"
    )


class ProjectUpdateRequest(BaseModel):
    """Payload to update project details."""

    name: str | None = Field(
        default=None, min_length=2, max_length=100, description="Updated project display name"
    )
    slug: SlugString | None = Field(default=None, description="Updated project slug")
    description: str | None = Field(default=None, max_length=1000)
    status: str | None = Field(default=None, description="Project status: active, archived")


class ProjectResponse(BaseModel):
    """Public representation of a project entity."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    slug: str
    description: str | None
    status: str
    created_at: datetime
    updated_at: datetime
