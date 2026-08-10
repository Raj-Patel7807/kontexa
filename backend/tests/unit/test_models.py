"""Unit tests for SQLAlchemy ORM models — structure and column validation."""

from sqlalchemy import BigInteger, String, inspect
from sqlalchemy.dialects.postgresql import JSONB

from kontexa.database.models.ai import AIModel, AIProvider, AIUsage
from kontexa.database.models.audit import AuditLog
from kontexa.database.models.base import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from kontexa.database.models.conversations import Conversation
from kontexa.database.models.documents import Document, DocumentChunk, DocumentVersion
from kontexa.database.models.integrations import Integration
from kontexa.database.models.memory import MemoryEntry
from kontexa.database.models.messages import Message, MessagePart
from kontexa.database.models.projects import Project
from kontexa.database.models.tools import AgentRun, Tool
from kontexa.database.models.users import User
from kontexa.database.models.workspaces import Workspace, WorkspaceMember
from kontexa.database.session import Base

# ---------------------------------------------------------------------------
# Base mixin tests
# ---------------------------------------------------------------------------


def test_uuid_primary_key_mixin_defines_id_column() -> None:
    """Verify UUIDPrimaryKeyMixin contributes an 'id' mapped column."""
    assert hasattr(UUIDPrimaryKeyMixin, "id")


def test_timestamp_mixin_defines_created_and_updated() -> None:
    """Verify TimestampMixin contributes created_at and updated_at columns."""
    assert hasattr(TimestampMixin, "created_at")
    assert hasattr(TimestampMixin, "updated_at")


def test_soft_delete_mixin_defines_deleted_at() -> None:
    """Verify SoftDeleteMixin contributes a nullable deleted_at column."""
    assert hasattr(SoftDeleteMixin, "deleted_at")


# ---------------------------------------------------------------------------
# User model tests
# ---------------------------------------------------------------------------


def test_user_table_name_is_users() -> None:
    """Verify the User model maps to the 'users' table."""
    assert User.__tablename__ == "users"


def test_user_inherits_base() -> None:
    """Verify User inherits from the declarative Base."""
    assert issubclass(User, Base)


def test_user_has_expected_columns() -> None:
    """Verify User model declares all required columns."""
    mapper = inspect(User)
    column_names = {col.key for col in mapper.column_attrs}
    expected = {"id", "email", "name", "is_active", "created_at", "updated_at", "deleted_at"}
    assert expected.issubset(column_names)


def test_user_id_column_is_uuid() -> None:
    """Verify User.id column uses UUID type."""
    mapper = inspect(User)
    id_col = mapper.columns["id"]
    assert isinstance(id_col.type, type(User.__table__.c.id.type))


def test_user_email_is_unique() -> None:
    """Verify User.email column has a unique constraint."""
    email_col = User.__table__.c.email
    assert email_col.unique is True


# ---------------------------------------------------------------------------
# Workspace model tests
# ---------------------------------------------------------------------------


def test_workspace_table_name_is_workspaces() -> None:
    """Verify the Workspace model maps to the 'workspaces' table."""
    assert Workspace.__tablename__ == "workspaces"


def test_workspace_has_expected_columns() -> None:
    """Verify Workspace model declares all required columns."""
    mapper = inspect(Workspace)
    column_names = {col.key for col in mapper.column_attrs}
    expected = {"id", "name", "slug", "created_at", "updated_at", "deleted_at"}
    assert expected.issubset(column_names)


def test_workspace_name_is_unique() -> None:
    """Verify Workspace.name has a unique constraint."""
    assert Workspace.__table__.c.name.unique is True


def test_workspace_slug_is_unique() -> None:
    """Verify Workspace.slug has a unique constraint."""
    assert Workspace.__table__.c.slug.unique is True


# ---------------------------------------------------------------------------
# WorkspaceMember model tests
# ---------------------------------------------------------------------------


def test_workspace_member_table_name() -> None:
    """Verify the WorkspaceMember model maps to 'workspace_members'."""
    assert WorkspaceMember.__tablename__ == "workspace_members"


def test_workspace_member_has_composite_primary_key() -> None:
    """Verify WorkspaceMember uses (workspace_id, user_id) as composite PK."""
    pk_cols = {col.name for col in WorkspaceMember.__table__.primary_key.columns}
    assert pk_cols == {"workspace_id", "user_id"}


def test_workspace_member_has_role_column() -> None:
    """Verify WorkspaceMember has a role column."""
    mapper = inspect(WorkspaceMember)
    column_names = {col.key for col in mapper.column_attrs}
    assert "role" in column_names


def test_workspace_member_workspace_fk_cascades_on_delete() -> None:
    """Verify workspace_id FK uses ON DELETE CASCADE."""
    fk = next(iter(WorkspaceMember.__table__.c.workspace_id.foreign_keys))
    assert fk.ondelete == "CASCADE"


def test_workspace_member_user_fk_cascades_on_delete() -> None:
    """Verify user_id FK uses ON DELETE CASCADE."""
    fk = next(iter(WorkspaceMember.__table__.c.user_id.foreign_keys))
    assert fk.ondelete == "CASCADE"


# ---------------------------------------------------------------------------
# Project model tests
# ---------------------------------------------------------------------------


def test_project_table_name() -> None:
    """Verify the Project model maps to 'projects'."""
    assert Project.__tablename__ == "projects"


def test_project_has_expected_columns() -> None:
    """Verify Project model declares all required columns."""
    mapper = inspect(Project)
    column_names = {col.key for col in mapper.column_attrs}
    expected = {
        "id", "workspace_id", "name", "slug", "description",
        "status", "created_at", "updated_at", "deleted_at",
    }
    assert expected.issubset(column_names)


def test_project_workspace_fk_cascades_on_delete() -> None:
    """Verify Project.workspace_id FK uses ON DELETE CASCADE."""
    fk = next(iter(Project.__table__.c.workspace_id.foreign_keys))
    assert fk.ondelete == "CASCADE"


def test_project_has_unique_workspace_slug_index() -> None:
    """Verify projects has a unique composite index on (workspace_id, slug)."""
    index_names = {idx.name for idx in Project.__table__.indexes}
    assert "idx_projects_workspace_slug" in index_names


# ---------------------------------------------------------------------------
# Conversation model tests
# ---------------------------------------------------------------------------


def test_conversation_table_name() -> None:
    """Verify the Conversation model maps to 'conversations'."""
    assert Conversation.__tablename__ == "conversations"


def test_conversation_has_expected_columns() -> None:
    """Verify Conversation model declares all required columns."""
    mapper = inspect(Conversation)
    column_names = {col.key for col in mapper.column_attrs}
    expected = {
        "id", "workspace_id", "project_id", "title",
        "is_active", "metadata_", "created_at", "updated_at", "deleted_at",
    }
    assert expected.issubset(column_names)


def test_conversation_workspace_fk_cascades() -> None:
    """Verify Conversation.workspace_id FK uses ON DELETE CASCADE."""
    fk = next(iter(Conversation.__table__.c.workspace_id.foreign_keys))
    assert fk.ondelete == "CASCADE"


def test_conversation_project_fk_sets_null() -> None:
    """Verify Conversation.project_id FK uses ON DELETE SET NULL."""
    fk = next(iter(Conversation.__table__.c.project_id.foreign_keys))
    assert fk.ondelete == "SET NULL"


# ---------------------------------------------------------------------------
# Message model tests
# ---------------------------------------------------------------------------


def test_message_table_name() -> None:
    """Verify the Message model maps to 'messages'."""
    assert Message.__tablename__ == "messages"


def test_message_has_expected_columns() -> None:
    """Verify Message model declares all required columns."""
    mapper = inspect(Message)
    column_names = {col.key for col in mapper.column_attrs}
    expected = {
        "id", "conversation_id", "user_id", "content",
        "metadata_", "created_at", "updated_at",
    }
    assert expected.issubset(column_names)


def test_message_conversation_fk_cascades() -> None:
    """Verify Message.conversation_id FK uses ON DELETE CASCADE."""
    fk = next(iter(Message.__table__.c.conversation_id.foreign_keys))
    assert fk.ondelete == "CASCADE"


def test_message_user_fk_sets_null() -> None:
    """Verify Message.user_id FK uses ON DELETE SET NULL."""
    fk = next(iter(Message.__table__.c.user_id.foreign_keys))
    assert fk.ondelete == "SET NULL"


# ---------------------------------------------------------------------------
# MessagePart model tests
# ---------------------------------------------------------------------------


def test_message_part_table_name() -> None:
    """Verify the MessagePart model maps to 'message_parts'."""
    assert MessagePart.__tablename__ == "message_parts"


def test_message_part_has_expected_columns() -> None:
    """Verify MessagePart declares all required columns."""
    mapper = inspect(MessagePart)
    column_names = {col.key for col in mapper.column_attrs}
    expected = {"id", "message_id", "part_index", "content", "mime_type"}
    assert expected.issubset(column_names)


def test_message_part_message_fk_cascades() -> None:
    """Verify MessagePart.message_id FK uses ON DELETE CASCADE."""
    fk = next(iter(MessagePart.__table__.c.message_id.foreign_keys))
    assert fk.ondelete == "CASCADE"


# ---------------------------------------------------------------------------
# Document model tests
# ---------------------------------------------------------------------------


def test_document_table_name() -> None:
    """Verify the Document model maps to 'documents'."""
    assert Document.__tablename__ == "documents"


def test_document_has_expected_columns() -> None:
    """Verify Document model declares all required columns."""
    mapper = inspect(Document)
    column_names = {col.key for col in mapper.column_attrs}
    expected = {"id", "project_id", "title", "metadata_", "created_at"}
    assert expected.issubset(column_names)


def test_document_project_fk_cascades() -> None:
    """Verify Document.project_id FK uses ON DELETE CASCADE."""
    fk = next(iter(Document.__table__.c.project_id.foreign_keys))
    assert fk.ondelete == "CASCADE"


def test_document_version_table_name() -> None:
    """Verify the DocumentVersion model maps to 'document_versions'."""
    assert DocumentVersion.__tablename__ == "document_versions"


def test_document_version_document_fk_cascades() -> None:
    """Verify DocumentVersion.document_id FK uses ON DELETE CASCADE."""
    fk = next(iter(DocumentVersion.__table__.c.document_id.foreign_keys))
    assert fk.ondelete == "CASCADE"


def test_document_chunk_table_name() -> None:
    """Verify the DocumentChunk model maps to 'document_chunks'."""
    assert DocumentChunk.__tablename__ == "document_chunks"


def test_document_chunk_has_embedding_column() -> None:
    """Verify DocumentChunk has an embedding column."""
    col_names = {c.name for c in DocumentChunk.__table__.columns}
    assert "embedding" in col_names


def test_document_chunk_version_fk_cascades() -> None:
    """Verify DocumentChunk.document_version_id FK uses ON DELETE CASCADE."""
    fk = next(iter(DocumentChunk.__table__.c.document_version_id.foreign_keys))
    assert fk.ondelete == "CASCADE"


# ---------------------------------------------------------------------------
# Integration model tests
# ---------------------------------------------------------------------------


def test_integration_table_name() -> None:
    """Verify the Integration model maps to 'integrations'."""
    assert Integration.__tablename__ == "integrations"


def test_integration_has_expected_columns() -> None:
    """Verify Integration model declares all required columns."""
    mapper = inspect(Integration)
    column_names = {col.key for col in mapper.column_attrs}
    expected = {
        "id", "workspace_id", "type", "config",
        "enabled", "created_at", "updated_at", "deleted_at",
    }
    assert expected.issubset(column_names)


def test_integration_workspace_fk_cascades() -> None:
    """Verify Integration.workspace_id FK uses ON DELETE CASCADE."""
    fk = next(iter(Integration.__table__.c.workspace_id.foreign_keys))
    assert fk.ondelete == "CASCADE"


# ---------------------------------------------------------------------------
# MemoryEntry model tests
# ---------------------------------------------------------------------------


def test_memory_entry_table_name() -> None:
    """Verify the MemoryEntry model maps to 'memory_entries'."""
    assert MemoryEntry.__tablename__ == "memory_entries"


def test_memory_entry_has_expected_columns() -> None:
    """Verify MemoryEntry model declares all required columns."""
    mapper = inspect(MemoryEntry)
    column_names = {col.key for col in mapper.column_attrs}
    expected = {"id", "workspace_id", "user_id", "key", "content", "created_at"}
    assert expected.issubset(column_names)


def test_memory_entry_workspace_fk_cascades() -> None:
    """Verify MemoryEntry.workspace_id FK uses ON DELETE CASCADE."""
    fk = next(iter(MemoryEntry.__table__.c.workspace_id.foreign_keys))
    assert fk.ondelete == "CASCADE"


# ---------------------------------------------------------------------------
# Tool and AgentRun model tests
# ---------------------------------------------------------------------------


def test_tool_table_name() -> None:
    """Verify the Tool model maps to 'tools'."""
    assert Tool.__tablename__ == "tools"


def test_tool_has_expected_columns() -> None:
    """Verify Tool model declares all required columns."""
    mapper = inspect(Tool)
    column_names = {col.key for col in mapper.column_attrs}
    expected = {"id", "project_id", "name", "config", "created_at"}
    assert expected.issubset(column_names)


def test_tool_project_fk_cascades() -> None:
    """Verify Tool.project_id FK uses ON DELETE CASCADE."""
    fk = next(iter(Tool.__table__.c.project_id.foreign_keys))
    assert fk.ondelete == "CASCADE"


def test_agent_run_table_name() -> None:
    """Verify the AgentRun model maps to 'agent_runs'."""
    assert AgentRun.__tablename__ == "agent_runs"


def test_agent_run_has_expected_columns() -> None:
    """Verify AgentRun model declares all required columns."""
    mapper = inspect(AgentRun)
    column_names = {col.key for col in mapper.column_attrs}
    expected = {"id", "tool_id", "inputs", "outputs", "status", "started_at", "ended_at"}
    assert expected.issubset(column_names)


def test_agent_run_tool_fk_sets_null() -> None:
    """Verify AgentRun.tool_id FK uses ON DELETE SET NULL."""
    fk = next(iter(AgentRun.__table__.c.tool_id.foreign_keys))
    assert fk.ondelete == "SET NULL"


def test_agent_run_records_structured_input_and_output() -> None:
    """Verify executions retain structured data needed to reproduce a run."""
    assert isinstance(AgentRun.__table__.c.inputs.type, JSONB)
    assert isinstance(AgentRun.__table__.c.outputs.type, JSONB)
    assert AgentRun.__table__.c.status.type.length == 20
    assert {index.name for index in AgentRun.__table__.indexes} == {"idx_agent_runs_tool"}


# ---------------------------------------------------------------------------
# AI models tests
# ---------------------------------------------------------------------------


def test_ai_provider_table_name() -> None:
    """Verify the AIProvider model maps to 'ai_providers'."""
    assert AIProvider.__tablename__ == "ai_providers"


def test_ai_provider_name_is_unique() -> None:
    """Verify AIProvider.name column has a unique constraint."""
    assert AIProvider.__table__.c.name.unique is True


def test_ai_model_table_name() -> None:
    """Verify the AIModel model maps to 'ai_models'."""
    assert AIModel.__tablename__ == "ai_models"


def test_ai_model_provider_fk_cascades() -> None:
    """Verify AIModel.provider_id FK uses ON DELETE CASCADE."""
    fk = next(iter(AIModel.__table__.c.provider_id.foreign_keys))
    assert fk.ondelete == "CASCADE"


def test_ai_provider_and_model_keep_provider_configuration_and_lookup_index() -> None:
    """Verify providers retain structured configuration and models remain provider-queryable."""
    assert isinstance(AIProvider.__table__.c.config.type, JSONB)
    assert {index.name for index in AIModel.__table__.indexes} == {"idx_ai_models_provider"}


def test_ai_usage_table_name() -> None:
    """Verify the AIUsage model maps to 'ai_usage'."""
    assert AIUsage.__tablename__ == "ai_usage"


def test_ai_usage_has_expected_columns() -> None:
    """Verify AIUsage model declares all required columns."""
    mapper = inspect(AIUsage)
    column_names = {col.key for col in mapper.column_attrs}
    expected = {
        "id", "user_id", "model_id", "workspace_id",
        "tokens_used", "cost_cents", "timestamp",
    }
    assert expected.issubset(column_names)


def test_ai_usage_foreign_keys_preserve_usage_history_semantics() -> None:
    """Verify model deletion removes usage while user deletion only anonymizes it."""
    user_fk = next(iter(AIUsage.__table__.c.user_id.foreign_keys))
    model_fk = next(iter(AIUsage.__table__.c.model_id.foreign_keys))
    workspace_fk = next(iter(AIUsage.__table__.c.workspace_id.foreign_keys))
    assert user_fk.ondelete == "SET NULL"
    assert model_fk.ondelete == "CASCADE"
    assert workspace_fk.ondelete == "CASCADE"


def test_ai_usage_counts_and_costs_use_large_integer_columns() -> None:
    """Verify usage counters do not overflow during long-running workspace reporting."""
    assert isinstance(AIUsage.__table__.c.tokens_used.type, BigInteger)
    assert isinstance(AIUsage.__table__.c.cost_cents.type, BigInteger)
    assert {index.name for index in AIUsage.__table__.indexes} == {"idx_ai_usage_model"}


# ---------------------------------------------------------------------------
# AuditLog model tests
# ---------------------------------------------------------------------------


def test_audit_log_table_name() -> None:
    """Verify the AuditLog model maps to 'audit_logs'."""
    assert AuditLog.__tablename__ == "audit_logs"


def test_audit_log_has_expected_columns() -> None:
    """Verify AuditLog model declares all required columns."""
    mapper = inspect(AuditLog)
    column_names = {col.key for col in mapper.column_attrs}
    expected = {
        "id", "workspace_id", "user_id", "action",
        "table_name", "record_id", "changes", "created_at",
    }
    assert expected.issubset(column_names)


def test_audit_log_uses_append_only_identifier_and_structured_changes() -> None:
    """Verify audit records use scalable identifiers and retain structured change details."""
    assert isinstance(AuditLog.__table__.c.id.type, BigInteger)
    assert AuditLog.__table__.c.id.primary_key is True
    assert isinstance(AuditLog.__table__.c.changes.type, JSONB)
    assert isinstance(AuditLog.__table__.c.action.type, String)
    assert {index.name for index in AuditLog.__table__.indexes} == {
        "idx_audit_time",
        "idx_audit_workspace",
    }


# ---------------------------------------------------------------------------
# Metadata registration
# ---------------------------------------------------------------------------


def test_all_models_registered_in_base_metadata() -> None:
    """Verify all models are registered in Base.metadata.tables."""
    table_names = set(Base.metadata.tables.keys())
    expected = {
        "users", "workspaces", "workspace_members",
        "projects", "conversations", "messages", "message_parts",
        "documents", "document_versions", "document_chunks",
        "integrations", "memory_entries",
        "tools", "agent_runs",
        "ai_providers", "ai_models", "ai_usage",
        "audit_logs",
    }
    assert expected.issubset(table_names)
