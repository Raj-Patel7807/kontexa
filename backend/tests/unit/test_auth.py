"""Unit and integration tests for authentication endpoints, session cookies, and CSRF protection."""

import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from kontexa.api.deps import get_db
from kontexa.core.config import Settings
from kontexa.core.security import hash_password
from kontexa.database.models.sessions import UserSession
from kontexa.database.models.users import User
from kontexa.database.models.workspaces import Workspace, WorkspaceMember
from kontexa.main import create_app


class InMemoryAuthDatabase:
    """Mock database backing session for unit tests without a live PostgreSQL server."""

    def __init__(self) -> None:
        self.users: dict[uuid.UUID, User] = {}
        self.sessions: dict[uuid.UUID, UserSession] = {}
        self.workspaces: dict[uuid.UUID, Workspace] = {}
        self.members: list[WorkspaceMember] = []

    def add(self, obj: object) -> None:
        from datetime import UTC, datetime

        if isinstance(obj, User):
            if not hasattr(obj, "id") or obj.id is None:
                obj.id = uuid.uuid4()
            if not getattr(obj, "created_at", None):
                obj.created_at = datetime.now(UTC)
            self.users[obj.id] = obj
        elif isinstance(obj, UserSession):
            if not hasattr(obj, "id") or obj.id is None:
                obj.id = uuid.uuid4()
            if not getattr(obj, "created_at", None):
                obj.created_at = datetime.now(UTC)
            self.sessions[obj.id] = obj
        elif isinstance(obj, Workspace):
            if not hasattr(obj, "id") or obj.id is None:
                obj.id = uuid.uuid4()
            self.workspaces[obj.id] = obj
        elif isinstance(obj, WorkspaceMember):
            self.members.append(obj)

    async def commit(self) -> None:
        pass

    async def refresh(self, obj: object) -> None:
        pass

    async def execute(self, stmt: object) -> "MockResult":
        # Compile statement to reliably inspect params
        compiled = stmt.compile()  # type: ignore[attr-defined]
        params = compiled.params
        stmt_str = str(compiled)

        # Handle User queries
        if "FROM users" in stmt_str and "JOIN" not in stmt_str:
            # Query by email
            if "users.email = :email" in stmt_str:
                target_email = next((v for k, v in params.items() if "email" in k), None)
                matches = [u for u in self.users.values() if u.email == target_email]
                return MockResult(matches)

            # Query by user ID
            if "users.id = :id" in stmt_str:
                target_id = next((v for k, v in params.items() if "id" in k), None)
                matches = [u for u in self.users.values() if u.id == target_id]
                return MockResult(matches)

        # Handle UserSession queries
        if "FROM user_sessions" in stmt_str:
            target_hash = next((v for k, v in params.items() if "token_hash" in k), None)
            matches_sessions = [s for s in self.sessions.values() if s.token_hash == target_hash]
            if "JOIN users" in stmt_str:
                results = []
                for s in matches_sessions:
                    u = self.users.get(s.user_id)
                    if u and u.deleted_at is None and s.revoked_at is None:
                        results.append((s, u))
                return MockResult(results)
            return MockResult(matches_sessions)

        # Handle WorkspaceMember queries
        if "FROM workspace_members" in stmt_str:
            target_user_id = next((v for k, v in params.items() if "user_id" in k), None)
            results = []
            for m in self.members:
                if m.user_id == target_user_id:
                    ws = self.workspaces.get(m.workspace_id)
                    if ws and ws.deleted_at is None:
                        results.append((m.role, ws.id, ws.name, ws.slug))
            return MockResult(results)

        return MockResult([])


class MockResult:
    """Mock query execution result matching SQLAlchemy's Result interface."""

    def __init__(self, items: list) -> None:
        self.items = items

    def scalar_one_or_none(self) -> object | None:
        return self.items[0] if self.items else None

    def first(self) -> object | None:
        return self.items[0] if self.items else None

    def all(self) -> list:
        return self.items


@pytest.fixture
def mock_db() -> InMemoryAuthDatabase:
    return InMemoryAuthDatabase()


@pytest.fixture
def auth_app(mock_db: InMemoryAuthDatabase):
    """Create a test application instance with injected in-memory database."""
    settings = Settings(
        _env_file=None,
        database_url="postgresql+asyncpg://test:test@localhost:5432/test_db",
        session_cookie_name="kontexa_test_session",
        csrf_secret="test-csrf-secret-key-32-bytes-long!",
    )
    app = create_app(settings_override=settings)

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield mock_db  # type: ignore[misc]

    app.dependency_overrides[get_db] = override_get_db
    return app


@pytest.mark.asyncio
async def test_register_creates_new_user(auth_app: object, mock_db: InMemoryAuthDatabase) -> None:
    """Verify POST /api/v1/auth/register creates an account with hashed credentials."""
    async with AsyncClient(transport=ASGITransport(app=auth_app), base_url="http://test") as client:  # type: ignore[arg-type]
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "alice@example.com",
                "password": "ValidPassword123!",
                "name": "Alice Developer",
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "alice@example.com"
    assert data["name"] == "Alice Developer"
    assert data["is_active"] is True
    assert "password" not in data
    assert "password_hash" not in data

    # Verify user stored in DB with hashed password
    user_id = uuid.UUID(data["id"])
    assert user_id in mock_db.users
    assert mock_db.users[user_id].password_hash is not None
    assert mock_db.users[user_id].password_hash.startswith("pbkdf2:sha256:")


@pytest.mark.asyncio
async def test_register_rejects_duplicate_email(
    auth_app: object, mock_db: InMemoryAuthDatabase
) -> None:
    """Verify POST /api/v1/auth/register rejects existing email addresses."""
    existing_user = User(
        id=uuid.uuid4(),
        email="existing@example.com",
        name="Existing User",
        password_hash=hash_password("Pass1234!"),
        is_active=True,
    )
    mock_db.add(existing_user)

    async with AsyncClient(transport=ASGITransport(app=auth_app), base_url="http://test") as client:  # type: ignore[arg-type]
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "existing@example.com",
                "password": "AnotherPassword123!",
                "name": "Imposter",
            },
        )

    assert response.status_code == 409
    data = response.json()
    assert data["code"] == "CONFLICT"
    assert "already exists" in data["detail"]


@pytest.mark.asyncio
async def test_login_success_sets_httponly_cookie(
    auth_app: object, mock_db: InMemoryAuthDatabase
) -> None:
    """Verify POST /api/v1/auth/login sets HttpOnly, SameSite cookie and returns CSRF token."""
    user = User(
        id=uuid.uuid4(),
        email="bob@example.com",
        name="Bob Builder",
        password_hash=hash_password("CorrectHorseBattery99!"),
        is_active=True,
    )
    mock_db.add(user)

    async with AsyncClient(transport=ASGITransport(app=auth_app), base_url="http://test") as client:  # type: ignore[arg-type]
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "bob@example.com",
                "password": "CorrectHorseBattery99!",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["user"]["email"] == "bob@example.com"
    assert "csrf_token" in data
    assert len(data["csrf_token"]) > 0

    # Verify cookie attributes
    set_cookie = response.headers.get("set-cookie")
    assert set_cookie is not None
    assert "kontexa_test_session=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "SameSite=lax" in set_cookie
    assert "Path=/" in set_cookie


@pytest.mark.asyncio
async def test_login_fails_with_invalid_credentials(
    auth_app: object, mock_db: InMemoryAuthDatabase
) -> None:
    """Verify POST /api/v1/auth/login rejects wrong passwords without leaking account existence."""
    user = User(
        id=uuid.uuid4(),
        email="charlie@example.com",
        name="Charlie Brown",
        password_hash=hash_password("RealPassword123!"),
        is_active=True,
    )
    mock_db.add(user)

    async with AsyncClient(transport=ASGITransport(app=auth_app), base_url="http://test") as client:  # type: ignore[arg-type]
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "charlie@example.com",
                "password": "WrongPassword!",
            },
        )

    assert response.status_code == 401
    data = response.json()
    assert data["code"] == "UNAUTHORIZED"
    assert data["detail"] == "Invalid email or password."


@pytest.mark.asyncio
async def test_me_endpoint_requires_authentication(auth_app: object) -> None:
    """Verify GET /api/v1/auth/me rejects unauthenticated requests with 401."""
    async with AsyncClient(transport=ASGITransport(app=auth_app), base_url="http://test") as client:  # type: ignore[arg-type]
        response = await client.get("/api/v1/auth/me")

    assert response.status_code == 401
    data = response.json()
    assert data["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_logout_revokes_session_and_clears_cookie(
    auth_app: object, mock_db: InMemoryAuthDatabase
) -> None:
    """Verify POST /api/v1/auth/logout requires CSRF, revokes session, and deletes cookie."""
    user = User(
        id=uuid.uuid4(),
        email="dave@example.com",
        name="Dave Smith",
        password_hash=hash_password("Password999!"),
        is_active=True,
    )
    mock_db.add(user)

    async with AsyncClient(transport=ASGITransport(app=auth_app), base_url="http://test") as client:  # type: ignore[arg-type]
        # 1. Login to obtain cookie and CSRF token
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": "dave@example.com", "password": "Password999!"},
        )
        assert login_res.status_code == 200
        csrf_token = login_res.json()["csrf_token"]

        # 2. Attempt logout without CSRF header -> 403 Forbidden
        logout_no_csrf = await client.post("/api/v1/auth/logout")
        assert logout_no_csrf.status_code == 403
        assert logout_no_csrf.json()["code"] == "PERMISSION_DENIED"

        # 3. Successful logout with CSRF header -> 200 OK
        logout_res = await client.post(
            "/api/v1/auth/logout",
            headers={"X-CSRF-Token": csrf_token},
        )
        assert logout_res.status_code == 200
        assert logout_res.json()["status"] == "ok"

        # 4. Confirm cookie deletion command in response headers
        set_cookie = logout_res.headers.get("set-cookie")
        assert set_cookie is not None
        assert 'kontexa_test_session=""' in set_cookie or "Max-Age=0" in set_cookie
