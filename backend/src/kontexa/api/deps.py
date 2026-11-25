"""Authentication dependencies for FastAPI route handlers."""

import uuid
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Path, Request
from sqlalchemy.ext.asyncio import AsyncSession

from kontexa.core.config import Settings
from kontexa.core.exceptions import AuthenticationError, PermissionDeniedError
from kontexa.core.security import verify_csrf_token
from kontexa.database.models.sessions import UserSession
from kontexa.database.models.users import User
from kontexa.database.session import get_db
from kontexa.schemas.workspaces import WorkspaceRole
from kontexa.services.auth import AuthService
from kontexa.services.conversations import ConversationService
from kontexa.services.workspaces import WorkspaceService


def get_settings(request: Request) -> Settings:
    """Extract application settings from FastAPI application state or fallback to default."""
    from kontexa.core.config import settings as default_settings

    return getattr(request.app.state, "settings", default_settings)


def get_auth_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthService:
    """Dependency provider for the domain authentication service."""
    return AuthService(db=db, settings=settings)


def get_workspace_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkspaceService:
    """Dependency provider for workspace and project tenancy isolation operations."""
    return WorkspaceService(db=db)


def get_conversation_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    ws_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> ConversationService:
    """Dependency provider for conversation and message persistence operations."""
    return ConversationService(db=db, ws_service=ws_service)


async def get_current_user_and_session(
    request: Request,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> tuple[User, UserSession, str]:
    """Extract and validate the active session cookie, returning user, session, and CSRF token."""
    session_token = request.cookies.get(settings.session_cookie_name)
    if not session_token:
        # Also check Authorization header: Bearer <session_token>
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header[7:].strip()

    if not session_token:
        raise AuthenticationError("Authentication required. Please sign in.")

    return await auth_service.validate_session(session_token)


async def get_current_user(
    auth_ctx: Annotated[tuple[User, UserSession, str], Depends(get_current_user_and_session)],
) -> User:
    """Dependency yielding the currently authenticated User model."""
    user, _, _ = auth_ctx
    return user


def require_workspace_membership(
    min_role: str = WorkspaceRole.VIEWER,
) -> Callable[..., object]:
    """Dependency factory enforcing workspace membership and role authorization."""

    async def _workspace_auth_dependency(
        workspace_id: Annotated[uuid.UUID, Path(description="Target workspace identifier")],
        user: Annotated[User, Depends(get_current_user)],
        ws_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
    ) -> str:
        return await ws_service.require_workspace_access(
            workspace_id=workspace_id,
            user_id=user.id,
            required_role=min_role,
        )

    return _workspace_auth_dependency


async def require_csrf(
    request: Request,
    auth_ctx: Annotated[tuple[User, UserSession, str], Depends(get_current_user_and_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    """Verify CSRF token on mutating requests (POST, PUT, PATCH, DELETE) when using cookie auth."""
    # If authenticated via Authorization header (Bearer token), CSRF protection is not needed
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return

    # Check incoming X-CSRF-Token or X-XSRF-Token header
    csrf_token = request.headers.get("x-csrf-token") or request.headers.get("x-xsrf-token")
    if not csrf_token:
        raise PermissionDeniedError("Missing required X-CSRF-Token header.")

    _, session, _ = auth_ctx
    if not verify_csrf_token(str(session.id), csrf_token, settings.csrf_secret):
        raise PermissionDeniedError("Invalid CSRF token.")
