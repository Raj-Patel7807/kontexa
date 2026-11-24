"""Pydantic schemas for authentication requests and user session responses."""

import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


class RegisterRequest(BaseModel):
    """Payload submitted when registering a new user account."""

    email: str = Field(description="User primary email address")
    password: str = Field(
        min_length=8, max_length=128, description="Account password (min 8 characters)"
    )
    name: str = Field(min_length=1, max_length=100, description="Full display name")

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        clean_email = v.strip().lower()
        if not EMAIL_REGEX.match(clean_email):
            raise ValueError("Invalid email address format.")
        return clean_email


class LoginRequest(BaseModel):
    """Payload submitted for password-based user authentication."""

    email: str = Field(description="User primary email address")
    password: str = Field(min_length=1, description="Account password")

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        clean_email = v.strip().lower()
        if not EMAIL_REGEX.match(clean_email):
            raise ValueError("Invalid email address format.")
        return clean_email


class UserProfileResponse(BaseModel):
    """Public user identity model returned across authentication boundaries."""

    id: UUID
    email: str
    name: str
    avatar_url: str | None = None
    is_active: bool
    created_at: datetime


class WorkspaceMembershipSummary(BaseModel):
    """Summary of a user's role within an associated workspace."""

    workspace_id: UUID
    name: str
    slug: str
    role: str


class CurrentUserResponse(BaseModel):
    """Payload representing the currently authenticated user and active tenancy."""

    id: UUID
    email: str
    name: str
    avatar_url: str | None = None
    is_active: bool
    created_at: datetime
    workspaces: list[WorkspaceMembershipSummary] = Field(default_factory=list)


class AuthSessionResponse(BaseModel):
    """Response returned upon successful authentication or session renewal."""

    user: UserProfileResponse
    active_workspace_id: UUID | None = None
    csrf_token: str = Field(
        description="Signed anti-CSRF token required for subsequent state mutations"
    )
