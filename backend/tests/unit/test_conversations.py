"""Tests for Conversation and Message persistence, auto-titling, and isolation."""

import uuid
from datetime import UTC, datetime

import pytest

from kontexa.core.exceptions import ResourceNotFoundError
from kontexa.database.models.conversations import Conversation
from kontexa.database.models.messages import Message
from kontexa.database.models.projects import Project
from kontexa.database.models.users import User
from kontexa.database.models.workspaces import Workspace, WorkspaceMember
from kontexa.schemas.conversations import (
    ConversationCreateRequest,
    MessageCreateRequest,
    MessageRole,
)
from kontexa.services.conversations import ConversationService, generate_title_from_content
from kontexa.services.workspaces import WorkspaceRole, WorkspaceService


class InMemorySession:
    """Mock database session supporting conversations, messages, and cross-tenant checks."""

    def __init__(self) -> None:
        self.users: dict[uuid.UUID, User] = {}
        self.workspaces: dict[uuid.UUID, Workspace] = {}
        self.workspace_members: list[WorkspaceMember] = []
        self.projects: dict[uuid.UUID, Project] = {}
        self.conversations: dict[uuid.UUID, Conversation] = {}
        self.messages: dict[uuid.UUID, Message] = {}

    def add(self, instance: object) -> None:
        now = datetime.now(UTC)
        if isinstance(instance, User):
            if not getattr(instance, "id", None):
                instance.id = uuid.uuid4()
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
            instance.deleted_at = None
            self.projects[instance.id] = instance
        elif isinstance(instance, Conversation):
            if not getattr(instance, "id", None):
                instance.id = uuid.uuid4()
            instance.created_at = getattr(instance, "created_at", None) or now
            instance.updated_at = getattr(instance, "updated_at", None) or now
            instance.deleted_at = None
            self.conversations[instance.id] = instance
        elif isinstance(instance, Message):
            if not getattr(instance, "id", None):
                instance.id = uuid.uuid4()
            instance.created_at = getattr(instance, "created_at", None) or now
            instance.updated_at = getattr(instance, "updated_at", None) or now
            self.messages[instance.id] = instance

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
                    raise ResourceNotFoundError("Item not found")
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

        # 2. Workspace by ID query
        if "FROM workspaces" in stmt_str:
            ws_id = params.get("id_1")
            ws = self.workspaces.get(ws_id)
            if ws and ws.deleted_at is None:
                return Result([ws])
            return Result([])

        # 3. Project query
        if "FROM projects" in stmt_str:
            p_id = params.get("id_1")
            p = self.projects.get(p_id)
            if p and p.deleted_at is None:
                return Result([p])
            return Result([])

        # 4. Conversation queries
        if "FROM conversations" in stmt_str:
            c_id = params.get("id_1")
            ws_id = params.get("workspace_id_1")
            p_id = params.get("project_id_1")

            matched = []
            for c in self.conversations.values():
                if c.deleted_at is not None:
                    continue
                if ws_id and c.workspace_id != ws_id:
                    continue
                if c_id and c.id != c_id:
                    continue
                if p_id and c.project_id != p_id:
                    continue
                matched.append(c)
            return Result(matched)

        # 5. Message queries
        if "FROM messages" in stmt_str:
            c_id = params.get("conversation_id_1")
            role = params.get("role_1")

            matched = []
            for m in self.messages.values():
                if c_id and m.conversation_id != c_id:
                    continue
                if role and m.role != role:
                    continue
                matched.append(m)

            # Order by created_at asc
            matched.sort(key=lambda m: m.created_at)
            return Result(matched)

        return Result([])


@pytest.fixture
def mock_db() -> InMemorySession:
    return InMemorySession()


@pytest.fixture
def chat_env(mock_db: InMemorySession) -> dict:
    """Setup isolated workspaces A and B with users and conversations."""
    user_a = User(id=uuid.uuid4(), email="alice@corp-a.com", name="Alice")
    user_b = User(id=uuid.uuid4(), email="bob@corp-b.com", name="Bob")

    mock_db.add(user_a)
    mock_db.add(user_b)

    ws_a = Workspace(id=uuid.uuid4(), name="Corp A", slug="corp-a")
    ws_b = Workspace(id=uuid.uuid4(), name="Corp B", slug="corp-b")

    mock_db.add(ws_a)
    mock_db.add(ws_b)

    # Memberships: Alice in Corp A (member), Bob in Corp B (member)
    mock_db.add(WorkspaceMember(workspace_id=ws_a.id, user_id=user_a.id, role=WorkspaceRole.MEMBER))
    mock_db.add(WorkspaceMember(workspace_id=ws_b.id, user_id=user_b.id, role=WorkspaceRole.MEMBER))

    ws_service = WorkspaceService(db=mock_db)  # type: ignore[arg-type]
    conv_service = ConversationService(db=mock_db, ws_service=ws_service)  # type: ignore[arg-type]

    # Pre-existing conversation in Corp A
    conv_a = Conversation(
        id=uuid.uuid4(),
        workspace_id=ws_a.id,
        title="Architecture Discussion",
        is_active=True,
    )
    mock_db.add(conv_a)

    return {
        "user_a": user_a,
        "user_b": user_b,
        "ws_a": ws_a,
        "ws_b": ws_b,
        "conv_a": conv_a,
        "conv_service": conv_service,
    }


def test_title_generation() -> None:
    assert generate_title_from_content("Short title") == "Short title"
    long_msg = (
        "This is a very long message that describes an engineering problem in excessive detail"
    )
    assert len(generate_title_from_content(long_msg)) <= 50
    assert generate_title_from_content(long_msg).endswith("...")


@pytest.mark.asyncio
async def test_create_and_list_conversations(chat_env: dict) -> None:
    conv_service: ConversationService = chat_env["conv_service"]
    user_a = chat_env["user_a"]
    ws_a = chat_env["ws_a"]

    req = ConversationCreateRequest(title="Initial Conversation")
    conv = await conv_service.create_conversation(
        workspace_id=ws_a.id,
        user_id=user_a.id,
        payload=req,
    )

    assert conv.title == "Initial Conversation"
    assert conv.workspace_id == ws_a.id

    convs = await conv_service.list_conversations(workspace_id=ws_a.id, user_id=user_a.id)
    assert len(convs) >= 2


@pytest.mark.asyncio
async def test_send_message_and_auto_titling(chat_env: dict) -> None:
    conv_service: ConversationService = chat_env["conv_service"]
    user_a = chat_env["user_a"]
    ws_a = chat_env["ws_a"]

    # Create thread with default title
    conv = await conv_service.create_conversation(
        workspace_id=ws_a.id,
        user_id=user_a.id,
        payload=ConversationCreateRequest(title="New Conversation"),
    )

    # Send first user message
    user_msg, assistant_msg = await conv_service.send_message(
        workspace_id=ws_a.id,
        conversation_id=conv.id,
        user_id=user_a.id,
        payload=MessageCreateRequest(content="How do we optimize the database queries?"),
    )

    assert user_msg.role == MessageRole.USER
    assert user_msg.content == "How do we optimize the database queries?"
    assert assistant_msg.role == MessageRole.ASSISTANT
    assert "[Development AI Adapter]" in assistant_msg.content

    # Title should have been derived from content
    assert conv.title == "How do we optimize the database queries?"


@pytest.mark.asyncio
async def test_cross_tenant_conversation_isolation(chat_env: dict) -> None:
    """Bob (Corp B) must be rejected with 404 when querying Alice's conversation in Corp A."""
    conv_service: ConversationService = chat_env["conv_service"]
    user_b = chat_env["user_b"]
    ws_a = chat_env["ws_a"]
    conv_a = chat_env["conv_a"]

    with pytest.raises(ResourceNotFoundError):
        await conv_service.get_conversation(
            workspace_id=ws_a.id,
            conversation_id=conv_a.id,
            user_id=user_b.id,
        )

    with pytest.raises(ResourceNotFoundError):
        await conv_service.list_messages(
            workspace_id=ws_a.id,
            conversation_id=conv_a.id,
            user_id=user_b.id,
        )

    with pytest.raises(ResourceNotFoundError):
        await conv_service.send_message(
            workspace_id=ws_a.id,
            conversation_id=conv_a.id,
            user_id=user_b.id,
            payload=MessageCreateRequest(content="Malicious cross-tenant post"),
        )


@pytest.mark.asyncio
async def test_message_idempotency_protection(chat_env: dict) -> None:
    """Duplicate submissions with the same idempotency key return the cached message pair."""
    conv_service: ConversationService = chat_env["conv_service"]
    user_a = chat_env["user_a"]
    ws_a = chat_env["ws_a"]
    conv_a = chat_env["conv_a"]

    req = MessageCreateRequest(
        content="Idempotent query submission",
        idempotency_key="unique_request_key_123",
    )

    # First send
    u1, a1 = await conv_service.send_message(
        workspace_id=ws_a.id,
        conversation_id=conv_a.id,
        user_id=user_a.id,
        payload=req,
    )

    # Duplicate send with same idempotency key
    u2, a2 = await conv_service.send_message(
        workspace_id=ws_a.id,
        conversation_id=conv_a.id,
        user_id=user_a.id,
        payload=req,
    )

    assert u1.id == u2.id
    assert a1.id == a2.id
