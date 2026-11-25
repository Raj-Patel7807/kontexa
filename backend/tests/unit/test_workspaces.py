"""Tests for Workspace, Project, RBAC, and cross-tenant authorization isolation."""

import uuid
from datetime import UTC, datetime

import pytest

from kontexa.core.exceptions import ConflictError, PermissionDeniedError, ResourceNotFoundError
from kontexa.database.models.conversations import Conversation
from kontexa.database.models.projects import Project
from kontexa.database.models.users import User
from kontexa.database.models.workspaces import Workspace, WorkspaceMember
from kontexa.schemas.workspaces import (
    AddMemberRequest,
    ProjectCreateRequest,
    WorkspaceCreateRequest,
    WorkspaceRole,
)
from kontexa.services.workspaces import WorkspaceService


class InMemorySession:
    """In-memory mock session supporting basic models and cross-tenant query patterns."""

    def __init__(self) -> None:
        self.users: dict[uuid.UUID, User] = {}
        self.workspaces: dict[uuid.UUID, Workspace] = {}
        self.workspace_members: list[WorkspaceMember] = []
        self.projects: dict[uuid.UUID, Project] = {}
        self.conversations: dict[uuid.UUID, Conversation] = {}

    def add(self, instance: object) -> None:
        now = datetime.now(UTC)
        if isinstance(instance, User):
            if not getattr(instance, "id", None):
                instance.id = uuid.uuid4()
            instance.created_at = getattr(instance, "created_at", None) or now
            instance.updated_at = getattr(instance, "updated_at", None) or now
            self.users[instance.id] = instance
        elif isinstance(instance, Workspace):
            if not getattr(instance, "id", None):
                instance.id = uuid.uuid4()
            instance.created_at = getattr(instance, "created_at", None) or now
            instance.updated_at = getattr(instance, "updated_at", None) or now
            instance.deleted_at = None
            self.workspaces[instance.id] = instance
        elif isinstance(instance, WorkspaceMember):
            self.workspace_members.append(instance)
        elif isinstance(instance, Project):
            if not getattr(instance, "id", None):
                instance.id = uuid.uuid4()
            instance.created_at = getattr(instance, "created_at", None) or now
            instance.updated_at = getattr(instance, "updated_at", None) or now
            instance.deleted_at = None
            self.projects[instance.id] = instance
        elif isinstance(instance, Conversation):
            if not getattr(instance, "id", None):
                instance.id = uuid.uuid4()
            instance.created_at = getattr(instance, "created_at", None) or now
            instance.updated_at = getattr(instance, "updated_at", None) or now
            instance.deleted_at = None
            self.conversations[instance.id] = instance

    async def flush(self) -> None:
        pass

    async def commit(self) -> None:
        pass

    async def refresh(self, instance: object) -> None:
        pass

    async def execute(self, stmt: object) -> object:
        compiled = stmt.compile()  # type: ignore[attr-defined]
        stmt_str = str(compiled)
        params = compiled.params

        class Result:
            def __init__(self, data: list) -> None:
                self._data = data

            def scalar_one_or_none(self):
                return self._data[0] if self._data else None

            def scalar_one(self):
                if not self._data:
                    raise ResourceNotFoundError("Item not found in result")
                return self._data[0]

            def scalars(self):
                class Scalars:
                    def __init__(self, data: list) -> None:
                        self._data = data

                    def all(self) -> list:
                        return self._data

                return Scalars(self._data)

            def all(self) -> list:
                return self._data

        # 1. Workspace member role query
        if (
            "FROM workspace_members" in stmt_str
            and "workspace_members.role" in stmt_str
            and "count" not in stmt_str.lower()
        ):
            ws_id = params.get("workspace_id_1")
            u_id = params.get("user_id_1")
            for m in self.workspace_members:
                if m.workspace_id == ws_id and m.user_id == u_id:
                    return Result([m.role])
            return Result([])

        # 2. Workspace member count query
        if "count" in stmt_str.lower() and "workspace_members" in stmt_str.lower():
            ws_id = None
            role = None
            for k, v in params.items():
                if "workspace_id" in k:
                    ws_id = v
                if "role" in k:
                    role = v
            count = sum(
                1
                for m in self.workspace_members
                if (ws_id is None or m.workspace_id == ws_id) and (role is None or m.role == role)
            )
            return Result([count])

        # 3. List workspace members with join on User
        if "FROM workspace_members JOIN users" in stmt_str:
            ws_id = params.get("workspace_id_1")
            matched = []
            for m in self.workspace_members:
                if m.workspace_id == ws_id:
                    u = self.users.get(m.user_id)
                    if u:
                        matched.append(
                            type(
                                "Row",
                                (),
                                {
                                    "workspace_id": m.workspace_id,
                                    "user_id": m.user_id,
                                    "role": m.role,
                                    "email": u.email,
                                    "name": u.name,
                                },
                            )()
                        )
            return Result(matched)

        # 4. List workspaces for user query
        if "FROM workspaces JOIN workspace_members" in stmt_str:
            u_id = params.get("user_id_1")
            matched = []
            for m in self.workspace_members:
                if m.user_id == u_id:
                    ws = self.workspaces.get(m.workspace_id)
                    if ws and ws.deleted_at is None:
                        matched.append((ws, m.role))
            return Result(matched)

        # 5. Workspace by slug / id query
        if "FROM workspaces" in stmt_str:
            slug = params.get("slug_1")
            ws_id = params.get("id_1")
            for ws in self.workspaces.values():
                if ws.deleted_at is not None:
                    continue
                if slug and ws.slug == slug:
                    return Result([ws])
                if ws_id and ws.id == ws_id:
                    return Result([ws])
            return Result([])

        # 6. User by email query
        if "FROM users" in stmt_str and "users.email" in stmt_str:
            email = params.get("email_1")
            for u in self.users.values():
                if u.email == email:
                    return Result([u])
            return Result([])

        # 7. User by ID query
        if "FROM users" in stmt_str and "users.id" in stmt_str:
            u_id = params.get("id_1")
            u = self.users.get(u_id)
            return Result([u] if u else [])

        # 8. Project query
        if "FROM projects" in stmt_str:
            ws_id = params.get("workspace_id_1")
            p_id = params.get("id_1")
            p_slug = params.get("slug_1")

            matched = []
            for p in self.projects.values():
                if p.deleted_at is not None:
                    continue
                if ws_id and p.workspace_id != ws_id:
                    continue
                if p_id and p.id != p_id:
                    continue
                if p_slug and p.slug != p_slug:
                    continue
                matched.append(p)
            return Result(matched)

        # 9. Update workspace member role
        if "UPDATE workspace_members" in stmt_str:
            ws_id = params.get("workspace_id_1")
            u_id = params.get("user_id_1")
            new_role = params.get("role")
            for m in self.workspace_members:
                if m.workspace_id == ws_id and m.user_id == u_id:
                    m.role = new_role
                    return Result([])
            return Result([])

        # 10. Delete workspace member
        if "DELETE FROM workspace_members" in stmt_str:
            ws_id = params.get("workspace_id_1")
            u_id = params.get("user_id_1")
            self.workspace_members = [
                m
                for m in self.workspace_members
                if not (m.workspace_id == ws_id and m.user_id == u_id)
            ]
            return Result([])

        return Result([])


@pytest.fixture
def mock_db() -> InMemorySession:
    return InMemorySession()


@pytest.fixture
def ws_service(mock_db: InMemorySession) -> WorkspaceService:
    return WorkspaceService(db=mock_db)  # type: ignore[arg-type]


@pytest.fixture
def seeded_env(mock_db: InMemorySession) -> dict:
    """Set up two isolated workspaces with distinct users and projects."""
    user_a = User(id=uuid.uuid4(), email="alice@corp-a.com", name="Alice", password_hash="h1")
    user_b = User(id=uuid.uuid4(), email="bob@corp-b.com", name="Bob", password_hash="h2")
    user_c = User(id=uuid.uuid4(), email="charlie@corp-a.com", name="Charlie", password_hash="h3")

    mock_db.add(user_a)
    mock_db.add(user_b)
    mock_db.add(user_c)

    ws_a = Workspace(id=uuid.uuid4(), name="Corp A", slug="corp-a")
    ws_b = Workspace(id=uuid.uuid4(), name="Corp B", slug="corp-b")

    mock_db.add(ws_a)
    mock_db.add(ws_b)

    # Alice is Owner of Corp A; Charlie is Viewer of Corp A
    mock_db.add(WorkspaceMember(workspace_id=ws_a.id, user_id=user_a.id, role=WorkspaceRole.OWNER))
    mock_db.add(WorkspaceMember(workspace_id=ws_a.id, user_id=user_c.id, role=WorkspaceRole.VIEWER))

    # Bob is Owner of Corp B
    mock_db.add(WorkspaceMember(workspace_id=ws_b.id, user_id=user_b.id, role=WorkspaceRole.OWNER))

    # Project in Corp A
    prj_a = Project(
        id=uuid.uuid4(),
        workspace_id=ws_a.id,
        name="Project A1",
        slug="project-a1",
        description="Internal A",
        status="active",
    )
    # Project in Corp B
    prj_b = Project(
        id=uuid.uuid4(),
        workspace_id=ws_b.id,
        name="Project B1",
        slug="project-b1",
        description="Internal B",
        status="active",
    )

    mock_db.add(prj_a)
    mock_db.add(prj_b)

    return {
        "user_a": user_a,
        "user_b": user_b,
        "user_c": user_c,
        "ws_a": ws_a,
        "ws_b": ws_b,
        "prj_a": prj_a,
        "prj_b": prj_b,
    }


@pytest.mark.asyncio
async def test_workspace_creation_assigns_owner(
    ws_service: WorkspaceService, mock_db: InMemorySession
) -> None:
    user = User(id=uuid.uuid4(), email="dev@example.com", name="Dev", password_hash="h")
    mock_db.add(user)

    req = WorkspaceCreateRequest(name="Dev Org", slug="dev-org")
    ws = await ws_service.create_workspace(user_id=user.id, payload=req)

    assert ws.name == "Dev Org"
    assert ws.slug == "dev-org"
    role = await ws_service.get_member_role(ws.id, user.id)
    assert role == WorkspaceRole.OWNER


@pytest.mark.asyncio
async def test_duplicate_workspace_slug_rejected(
    ws_service: WorkspaceService, seeded_env: dict
) -> None:
    user_a = seeded_env["user_a"]
    req = WorkspaceCreateRequest(name="Corp A Duplicate", slug="corp-a")
    with pytest.raises(ConflictError, match="already exists"):
        await ws_service.create_workspace(user_id=user_a.id, payload=req)


@pytest.mark.asyncio
async def test_cross_tenant_workspace_access_rejected(
    ws_service: WorkspaceService, seeded_env: dict
) -> None:
    """User B (Bob) must not be able to read or access Workspace A (Corp A)."""
    user_b = seeded_env["user_b"]
    ws_a = seeded_env["ws_a"]

    # Bob attempts to get Workspace A details -> Should raise 404 (prevents tenant probing)
    with pytest.raises(ResourceNotFoundError):
        await ws_service.get_workspace(workspace_id=ws_a.id, user_id=user_b.id)


@pytest.mark.asyncio
async def test_cross_tenant_project_read_rejected(
    ws_service: WorkspaceService, seeded_env: dict
) -> None:
    """Bob cannot access Project A1 belonging to Workspace A, even with valid IDs."""
    user_b = seeded_env["user_b"]
    ws_a = seeded_env["ws_a"]
    prj_a = seeded_env["prj_a"]

    with pytest.raises(ResourceNotFoundError):
        await ws_service.get_project(workspace_id=ws_a.id, project_id=prj_a.id, user_id=user_b.id)


@pytest.mark.asyncio
async def test_cross_workspace_project_id_manipulation_rejected(
    ws_service: WorkspaceService, seeded_env: dict
) -> None:
    """Alice (Corp A) attempts to access Project B1 under Workspace A -> Rejected."""
    user_a = seeded_env["user_a"]
    ws_a = seeded_env["ws_a"]
    prj_b = seeded_env["prj_b"]

    with pytest.raises(ResourceNotFoundError):
        await ws_service.get_project(workspace_id=ws_a.id, project_id=prj_b.id, user_id=user_a.id)


@pytest.mark.asyncio
async def test_viewer_cannot_create_project(ws_service: WorkspaceService, seeded_env: dict) -> None:
    """Charlie is a Viewer in Corp A; creating a project requires MEMBER role."""
    user_c = seeded_env["user_c"]
    ws_a = seeded_env["ws_a"]

    req = ProjectCreateRequest(name="Forbidden Project")
    with pytest.raises(PermissionDeniedError, match="Action requires role 'member'"):
        await ws_service.create_project(workspace_id=ws_a.id, user_id=user_c.id, payload=req)


@pytest.mark.asyncio
async def test_member_management_and_role_escalation_guard(
    ws_service: WorkspaceService, seeded_env: dict, mock_db: InMemorySession
) -> None:
    """Admin cannot promote a user to Owner; only Owner can do so."""
    ws_a = seeded_env["ws_a"]
    user_a = seeded_env["user_a"]

    # Add user_d as admin
    user_d = User(id=uuid.uuid4(), email="dan@corp-a.com", name="Dan", password_hash="h4")
    mock_db.add(user_d)

    await ws_service.add_workspace_member(
        workspace_id=ws_a.id,
        user_id=user_a.id,
        payload=AddMemberRequest(email="dan@corp-a.com", role=WorkspaceRole.ADMIN),
    )

    # User D (Admin) tries to promote Charlie to Owner -> Rejected
    with pytest.raises(PermissionDeniedError, match="Only owners can promote"):
        await ws_service.update_member_role(
            workspace_id=ws_a.id,
            user_id=user_d.id,
            target_user_id=seeded_env["user_c"].id,
            new_role=WorkspaceRole.OWNER,
        )


@pytest.mark.asyncio
async def test_prevent_demoting_or_removing_last_owner(
    ws_service: WorkspaceService, seeded_env: dict
) -> None:
    """Workspace A has only one owner (Alice). Demoting or removing her must fail."""
    ws_a = seeded_env["ws_a"]
    user_a = seeded_env["user_a"]

    with pytest.raises(ConflictError, match="Cannot demote the last owner"):
        await ws_service.update_member_role(
            workspace_id=ws_a.id,
            user_id=user_a.id,
            target_user_id=user_a.id,
            new_role=WorkspaceRole.ADMIN,
        )

    with pytest.raises(ConflictError, match="Cannot remove the last owner"):
        await ws_service.remove_workspace_member(
            workspace_id=ws_a.id,
            user_id=user_a.id,
            target_user_id=user_a.id,
        )
