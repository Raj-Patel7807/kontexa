"""Authentication and session lifecycle API router."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from kontexa.api.deps import (
    get_auth_service,
    get_current_user_and_session,
    get_settings,
    require_csrf,
)
from kontexa.core.config import Settings
from kontexa.database.models.sessions import UserSession
from kontexa.database.models.users import User
from kontexa.schemas.auth import (
    AuthSessionResponse,
    CurrentUserResponse,
    LoginRequest,
    RegisterRequest,
    UserProfileResponse,
)
from kontexa.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _set_session_cookie(response: Response, token: str, settings: Settings) -> None:
    """Set the HttpOnly, Secure, SameSite session cookie on the response."""
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_max_age_seconds,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        path="/",
    )


def _clear_session_cookie(response: Response, settings: Settings) -> None:
    """Clear the session cookie from the client browser."""
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
    )


@router.post(
    "/register",
    response_model=UserProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    description="Creates a new account with securely hashed credentials.",
)
async def register(
    payload: RegisterRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserProfileResponse:
    """Register a new user account."""
    user = await auth_service.register_user(payload)
    return UserProfileResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.post(
    "/login",
    response_model=AuthSessionResponse,
    summary="User authentication login",
    description="Authenticates credentials and establishes HttpOnly cookie with anti-CSRF token.",
)
async def login(
    request: Request,
    response: Response,
    payload: LoginRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthSessionResponse:
    """Authenticate with email and password and establish a browser session."""
    user = await auth_service.authenticate_user(payload)

    # Extract client IP and user agent
    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None

    raw_token, csrf_token, _ = await auth_service.create_session(
        user_id=user.id,
        user_agent=user_agent,
        ip_address=ip_address,
    )

    _set_session_cookie(response, raw_token, settings)

    # Attach CSRF token header for convenient client inspection
    response.headers["x-csrf-token"] = csrf_token

    context = await auth_service.get_current_user_context(user.id)
    active_workspace_id = context.workspaces[0].workspace_id if context.workspaces else None

    return AuthSessionResponse(
        user=UserProfileResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            avatar_url=user.avatar_url,
            is_active=user.is_active,
            created_at=user.created_at,
        ),
        active_workspace_id=active_workspace_id,
        csrf_token=csrf_token,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Sign out and revoke active session",
    description="Revokes the server-side session and clears the browser session cookie.",
    dependencies=[Depends(require_csrf)],
)
async def logout(
    request: Request,
    response: Response,
    auth_ctx: Annotated[tuple[User, UserSession, str], Depends(get_current_user_and_session)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, str]:
    """Revoke the current session and instruct the browser to delete the cookie."""
    session_token = request.cookies.get(settings.session_cookie_name)
    if session_token:
        await auth_service.revoke_session(session_token)

    _clear_session_cookie(response, settings)
    return {"status": "ok", "message": "Successfully signed out."}


@router.get(
    "/me",
    response_model=CurrentUserResponse,
    summary="Get current user context",
    description="Returns the profile and workspace memberships of the authenticated user.",
)
async def get_current_user_info(
    auth_ctx: Annotated[tuple[User, UserSession, str], Depends(get_current_user_and_session)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> CurrentUserResponse:
    """Return the active user profile and their associated workspace memberships."""
    user, _, _ = auth_ctx
    return await auth_service.get_current_user_context(user.id)


@router.get(
    "/csrf",
    summary="Get CSRF token for current session",
    description="Returns the active session CSRF token for state-mutating requests.",
)
async def get_csrf(
    auth_ctx: Annotated[tuple[User, UserSession, str], Depends(get_current_user_and_session)],
) -> dict[str, str]:
    """Return the active session's double-submit CSRF token."""
    _, _, csrf_token = auth_ctx
    return {"csrf_token": csrf_token}
