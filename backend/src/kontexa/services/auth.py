"""Authentication and account lifecycle service logic."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kontexa.core.config import Settings
from kontexa.core.exceptions import AuthenticationError, ConflictError, ResourceNotFoundError
from kontexa.core.security import (
    generate_csrf_token,
    generate_session_token,
    hash_password,
    hash_session_token,
    verify_password,
)
from kontexa.database.models.sessions import UserSession
from kontexa.database.models.users import User
from kontexa.database.models.workspaces import Workspace, WorkspaceMember
from kontexa.schemas.auth import (
    CurrentUserResponse,
    LoginRequest,
    RegisterRequest,
    WorkspaceMembershipSummary,
)


class AuthService:
    """Handles user registration, authentication verification, session rotation, and logout."""

    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    async def register_user(self, payload: RegisterRequest) -> User:
        """Register a new unique user account with hashed credentials."""
        # 1. Verify email uniqueness
        stmt = select(User).where(User.email == payload.email)
        res = await self.db.execute(stmt)
        existing_user = res.scalar_one_or_none()
        if existing_user is not None:
            raise ConflictError("An account with this email address already exists.")

        # 2. Hash password and persist user
        hashed = hash_password(payload.password)
        new_user = User(
            email=payload.email,
            name=payload.name,
            password_hash=hashed,
            is_active=True,
        )
        self.db.add(new_user)
        await self.db.commit()
        await self.db.refresh(new_user)
        return new_user

    async def authenticate_user(self, payload: LoginRequest) -> User:
        """Validate email and password credentials, returning the active User record."""
        stmt = select(User).where(User.email == payload.email, User.deleted_at.is_(None))
        res = await self.db.execute(stmt)
        user = res.scalar_one_or_none()

        if user is None or user.password_hash is None:
            raise AuthenticationError("Invalid email or password.")

        if not user.is_active:
            raise AuthenticationError("User account has been deactivated.")

        if not verify_password(payload.password, user.password_hash):
            raise AuthenticationError("Invalid email or password.")

        return user

    async def create_session(
        self,
        user_id: UUID,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[str, str, UserSession]:
        """Generate a new secure session token and persist its hash for authentication."""
        raw_token = generate_session_token()
        hashed_token = hash_session_token(raw_token)
        expires_at = datetime.now(UTC) + timedelta(seconds=self.settings.session_max_age_seconds)

        session = UserSession(
            user_id=user_id,
            token_hash=hashed_token,
            user_agent=user_agent[:500] if user_agent else None,
            ip_address=ip_address[:45] if ip_address else None,
            expires_at=expires_at,
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)

        csrf_token = generate_csrf_token(str(session.id), self.settings.csrf_secret)
        return raw_token, csrf_token, session

    async def validate_session(self, raw_token: str) -> tuple[User, UserSession, str]:
        """Validate a session token, returning User, UserSession, and signed CSRF token."""
        hashed_token = hash_session_token(raw_token)
        stmt = (
            select(UserSession, User)
            .join(User, UserSession.user_id == User.id)
            .where(
                UserSession.token_hash == hashed_token,
                UserSession.revoked_at.is_(None),
                User.deleted_at.is_(None),
            )
        )
        res = await self.db.execute(stmt)
        row = res.first()

        if row is None:
            raise AuthenticationError("Invalid or expired session.")

        session, user = row[0], row[1]

        if not user.is_active:
            raise AuthenticationError("User account has been deactivated.")

        # Ensure timezone-aware datetime comparison
        now = datetime.now(UTC)
        session_expires = session.expires_at
        if session_expires.tzinfo is None:
            session_expires = session_expires.replace(tzinfo=UTC)

        if session_expires <= now:
            raise AuthenticationError("Session has expired.")

        csrf_token = generate_csrf_token(str(session.id), self.settings.csrf_secret)
        return user, session, csrf_token

    async def revoke_session(self, raw_token: str) -> None:
        """Mark an active session as revoked (sign out)."""
        hashed_token = hash_session_token(raw_token)
        stmt = select(UserSession).where(
            UserSession.token_hash == hashed_token,
            UserSession.revoked_at.is_(None),
        )
        res = await self.db.execute(stmt)
        session = res.scalar_one_or_none()
        if session is not None:
            session.revoked_at = datetime.now(UTC)
            await self.db.commit()

    async def get_current_user_context(self, user_id: UUID) -> CurrentUserResponse:
        """Fetch user profile and all associated workspace memberships."""
        stmt = select(User).where(User.id == user_id, User.deleted_at.is_(None))
        res = await self.db.execute(stmt)
        user = res.scalar_one_or_none()
        if user is None:
            raise ResourceNotFoundError("User not found.")

        # Retrieve workspace memberships
        member_stmt = (
            select(WorkspaceMember.role, Workspace.id, Workspace.name, Workspace.slug)
            .join(Workspace, WorkspaceMember.workspace_id == Workspace.id)
            .where(
                WorkspaceMember.user_id == user_id,
                Workspace.deleted_at.is_(None),
            )
        )
        member_res = await self.db.execute(member_stmt)
        memberships = [
            WorkspaceMembershipSummary(
                workspace_id=row[1],
                name=row[2],
                slug=row[3],
                role=row[0],
            )
            for row in member_res.all()
        ]

        return CurrentUserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            avatar_url=user.avatar_url,
            is_active=user.is_active,
            created_at=user.created_at,
            workspaces=memberships,
        )
