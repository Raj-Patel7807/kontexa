"""Create the initial Kontexa database schema.

Revision ID: 20260811_0001
Revises:
Create Date: 2026-08-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "20260811_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def uuid_column(name: str = "id") -> sa.Column[sa.UUID]:
    """Build a UUID primary key column backed by PostgreSQL's UUID generator."""
    return sa.Column(
        name,
        sa.UUID(),
        primary_key=True,
        nullable=False,
        server_default=sa.text("gen_random_uuid()"),
    )


def created_at_column(name: str = "created_at") -> sa.Column[sa.TIMESTAMP]:
    """Build a non-null timestamp initialized by PostgreSQL."""
    return sa.Column(
        name,
        sa.TIMESTAMP(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
    )


def timestamp_columns() -> tuple[sa.Column[sa.TIMESTAMP], sa.Column[sa.TIMESTAMP]]:
    """Build the standard creation and update timestamps for mutable records."""
    return (
        created_at_column(),
        created_at_column("updated_at"),
    )


def upgrade() -> None:
    """Create PostgreSQL extensions, tables, constraints, and query indexes."""
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        uuid_column(),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *timestamp_columns(),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index(
        "idx_users_deleted",
        "users",
        ["deleted_at"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "workspaces",
        uuid_column(),
        sa.Column("name", sa.String(), nullable=False, unique=True),
        sa.Column("slug", sa.String(), nullable=False, unique=True),
        *timestamp_columns(),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index(
        "idx_workspaces_deleted",
        "workspaces",
        ["deleted_at"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "workspace_members",
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("workspace_id", "user_id"),
    )
    op.create_index("idx_workspace_members_user", "workspace_members", ["user_id"])

    op.create_table(
        "projects",
        uuid_column(),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        *timestamp_columns(),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "idx_projects_workspace_slug",
        "projects",
        ["workspace_id", "slug"],
        unique=True,
    )
    op.create_index(
        "idx_projects_deleted",
        "projects",
        ["deleted_at"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "conversations",
        uuid_column(),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        *timestamp_columns(),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_conversations_workspace", "conversations", ["workspace_id"])
    op.create_index(
        "idx_conversations_deleted",
        "conversations",
        ["deleted_at"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "messages",
        uuid_column(),
        sa.Column("conversation_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("idx_messages_conversation", "messages", ["conversation_id"])

    op.create_table(
        "message_parts",
        uuid_column(),
        sa.Column("message_id", sa.UUID(), nullable=False),
        sa.Column("part_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("mime_type", sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_message_parts_msg", "message_parts", ["message_id"])

    op.create_table(
        "documents",
        uuid_column(),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        created_at_column(),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "document_versions",
        uuid_column(),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        created_at_column(),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "document_chunks",
        uuid_column(),
        sa.Column("document_version_id", sa.UUID(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=True),
        created_at_column(),
        sa.ForeignKeyConstraint(
            ["document_version_id"],
            ["document_versions.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index("idx_chunks_doc_version", "document_chunks", ["document_version_id"])
    op.execute(
        "CREATE INDEX idx_chunks_embedding ON document_chunks "
        "USING ivfflat (embedding vector_l2_ops) WITH (lists = 100)"
    )

    op.create_table(
        "integrations",
        uuid_column(),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("config", postgresql.JSONB(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        *timestamp_columns(),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_integrations_workspace", "integrations", ["workspace_id"])

    op.create_table(
        "memory_entries",
        uuid_column(),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("key", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        created_at_column(),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_memory_workspace", "memory_entries", ["workspace_id"])

    op.create_table(
        "tools",
        uuid_column(),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("config", postgresql.JSONB(), nullable=True),
        created_at_column(),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "agent_runs",
        uuid_column(),
        sa.Column("tool_id", sa.UUID(), nullable=True),
        sa.Column("inputs", postgresql.JSONB(), nullable=True),
        sa.Column("outputs", postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=True),
        created_at_column("started_at"),
        sa.Column("ended_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tool_id"], ["tools.id"], ondelete="SET NULL"),
    )
    op.create_index("idx_agent_runs_tool", "agent_runs", ["tool_id"])

    op.create_table(
        "ai_providers",
        uuid_column(),
        sa.Column("name", sa.String(), nullable=False, unique=True),
        sa.Column("config", postgresql.JSONB(), nullable=True),
        created_at_column(),
    )

    op.create_table(
        "ai_models",
        uuid_column(),
        sa.Column("provider_id", sa.UUID(), nullable=False),
        sa.Column("model_name", sa.String(), nullable=False),
        sa.Column("max_tokens", sa.Integer(), nullable=True),
        created_at_column(),
        sa.ForeignKeyConstraint(["provider_id"], ["ai_providers.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_ai_models_provider", "ai_models", ["provider_id"])

    op.create_table(
        "ai_usage",
        uuid_column(),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("model_id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("tokens_used", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("cost_cents", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        created_at_column("timestamp"),
        sa.ForeignKeyConstraint(["model_id"], ["ai_models.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_ai_usage_model", "ai_usage", ["model_id"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("table_name", sa.String(length=50), nullable=True),
        sa.Column("record_id", sa.UUID(), nullable=True),
        sa.Column("changes", postgresql.JSONB(), nullable=True),
        created_at_column(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_audit_workspace", "audit_logs", ["workspace_id"])
    op.create_index("idx_audit_time", "audit_logs", ["created_at"])


def downgrade() -> None:
    """Drop application objects in dependency order while retaining shared extensions."""
    op.drop_index("idx_audit_time", table_name="audit_logs")
    op.drop_index("idx_audit_workspace", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index("idx_ai_usage_model", table_name="ai_usage")
    op.drop_table("ai_usage")
    op.drop_index("idx_ai_models_provider", table_name="ai_models")
    op.drop_table("ai_models")
    op.drop_table("ai_providers")
    op.drop_index("idx_agent_runs_tool", table_name="agent_runs")
    op.drop_table("agent_runs")
    op.drop_table("tools")
    op.drop_index("idx_memory_workspace", table_name="memory_entries")
    op.drop_table("memory_entries")
    op.drop_index("idx_integrations_workspace", table_name="integrations")
    op.drop_table("integrations")
    op.execute("DROP INDEX idx_chunks_embedding")
    op.drop_index("idx_chunks_doc_version", table_name="document_chunks")
    op.drop_table("document_chunks")
    op.drop_table("document_versions")
    op.drop_table("documents")
    op.drop_index("idx_message_parts_msg", table_name="message_parts")
    op.drop_table("message_parts")
    op.drop_index("idx_messages_conversation", table_name="messages")
    op.drop_table("messages")
    op.drop_index("idx_conversations_deleted", table_name="conversations")
    op.drop_index("idx_conversations_workspace", table_name="conversations")
    op.drop_table("conversations")
    op.drop_index("idx_projects_deleted", table_name="projects")
    op.drop_index("idx_projects_workspace_slug", table_name="projects")
    op.drop_table("projects")
    op.drop_index("idx_workspace_members_user", table_name="workspace_members")
    op.drop_table("workspace_members")
    op.drop_index("idx_workspaces_deleted", table_name="workspaces")
    op.drop_table("workspaces")
    op.drop_index("idx_users_deleted", table_name="users")
    op.drop_table("users")
