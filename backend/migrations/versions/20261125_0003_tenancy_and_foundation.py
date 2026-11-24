"""Add tenancy hardening, composite constraints, and foundational schema entities.

Revision ID: 20261125_0003
Revises: 20260904_0002
Create Date: 2026-11-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261125_0003"
down_revision: str | None = "20260904_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def uuid_pk_column(name: str = "id") -> sa.Column[sa.UUID]:
    """Build a UUID primary key column with server-side generation default."""
    return sa.Column(
        name,
        sa.UUID(),
        primary_key=True,
        nullable=False,
        server_default=sa.text("gen_random_uuid()"),
    )


def created_at_column(name: str = "created_at") -> sa.Column[sa.TIMESTAMP]:
    """Build a non-null timestamp initialized by the database."""
    return sa.Column(
        name,
        sa.TIMESTAMP(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
    )


def timestamp_columns() -> tuple[sa.Column[sa.TIMESTAMP], sa.Column[sa.TIMESTAMP]]:
    """Build created_at and updated_at timestamp columns."""
    return (
        created_at_column(),
        created_at_column("updated_at"),
    )


def upgrade() -> None:
    """Apply tenancy hardening, composite keys, and new platform tables."""
    # 1. User account authentication additions
    op.add_column("users", sa.Column("password_hash", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("avatar_url", sa.String(length=500), nullable=True))

    # 2. User sessions table for token lifecycle management
    op.create_table(
        "user_sessions",
        uuid_pk_column(),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.TIMESTAMP(timezone=True), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index("idx_user_sessions_token_hash", "user_sessions", ["token_hash"], unique=True)
    op.create_index("idx_user_sessions_expires", "user_sessions", ["expires_at"])

    # 3. Workspace invitations table
    op.create_table(
        "workspace_invitations",
        uuid_pk_column(),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False, server_default="member"),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("invited_by_user_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invited_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "idx_workspace_invitations_workspace_email",
        "workspace_invitations",
        ["workspace_id", "email"],
    )
    op.create_index(
        "idx_workspace_invitations_token_hash",
        "workspace_invitations",
        ["token_hash"],
        unique=True,
    )

    # 4. Enforce composite project key for child tenant scoping
    op.create_unique_constraint(
        "uq_projects_id_workspace_id",
        "projects",
        ["id", "workspace_id"],
    )

    # 5. Conversations composite tenant constraint
    op.create_foreign_key(
        "fk_conversations_project_workspace",
        "conversations",
        "projects",
        ["project_id", "workspace_id"],
        ["id", "workspace_id"],
        ondelete="SET NULL",
    )

    # 6. Messages role addition
    op.add_column(
        "messages",
        sa.Column("role", sa.String(length=20), nullable=False, server_default="user"),
    )

    # 7. Documents workspace tenant scoping and composite key
    op.add_column("documents", sa.Column("workspace_id", sa.UUID(), nullable=False))
    op.create_foreign_key(
        "fk_documents_workspace_id_workspaces",
        "documents",
        "workspaces",
        ["workspace_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_documents_project_workspace",
        "documents",
        "projects",
        ["project_id", "workspace_id"],
        ["id", "workspace_id"],
        ondelete="CASCADE",
    )
    op.create_index("idx_documents_workspace", "documents", ["workspace_id"])

    # 8. Tools workspace tenant scoping and composite key
    op.add_column("tools", sa.Column("workspace_id", sa.UUID(), nullable=False))
    op.create_foreign_key(
        "fk_tools_workspace_id_workspaces",
        "tools",
        "workspaces",
        ["workspace_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_tools_project_workspace",
        "tools",
        "projects",
        ["project_id", "workspace_id"],
        ["id", "workspace_id"],
        ondelete="CASCADE",
    )
    op.create_index("idx_tools_workspace", "tools", ["workspace_id"])

    # 9. Agent runs workspace and project scoping
    op.add_column("agent_runs", sa.Column("workspace_id", sa.UUID(), nullable=False))
    op.add_column("agent_runs", sa.Column("project_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_agent_runs_workspace_id_workspaces",
        "agent_runs",
        "workspaces",
        ["workspace_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_agent_runs_project_id_projects",
        "agent_runs",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("idx_agent_runs_workspace", "agent_runs", ["workspace_id"])
    op.create_index("idx_agent_runs_project", "agent_runs", ["project_id"])

    # 10. Sync jobs table for background connector synchronization
    op.create_table(
        "sync_jobs",
        uuid_pk_column(),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=True),
        sa.Column("integration_id", sa.UUID(), nullable=True),
        sa.Column("job_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("trigger", sa.String(length=20), nullable=False, server_default="manual"),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("ended_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("records_processed", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["integration_id"], ["integrations.id"], ondelete="SET NULL"),
    )
    op.create_index("idx_sync_jobs_workspace", "sync_jobs", ["workspace_id"])
    op.create_index("idx_sync_jobs_status", "sync_jobs", ["status"])

    # 11. Approvals table for gated agent actions
    op.create_table(
        "approvals",
        uuid_pk_column(),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("agent_run_id", sa.UUID(), nullable=True),
        sa.Column("requested_by_user_id", sa.UUID(), nullable=True),
        sa.Column("approved_by_user_id", sa.UUID(), nullable=True),
        sa.Column("tool_name", sa.String(length=100), nullable=False),
        sa.Column("action_summary", sa.Text(), nullable=False),
        sa.Column("action_payload", postgresql.JSONB(), nullable=False),
        sa.Column("plan_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("idx_approvals_workspace", "approvals", ["workspace_id"])
    op.create_index("idx_approvals_project", "approvals", ["project_id"])
    op.create_index("idx_approvals_status", "approvals", ["status"])
    op.create_index("idx_approvals_plan_hash", "approvals", ["plan_hash"])

    # 12. Repositories table for GitHub connector & code intelligence
    op.create_table(
        "repositories",
        uuid_pk_column(),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("integration_id", sa.UUID(), nullable=True),
        sa.Column("remote_id", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("default_branch", sa.String(length=50), nullable=False, server_default="main"),
        sa.Column("clone_url", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="not_indexed"),
        sa.Column("last_synced_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("index_metadata", postgresql.JSONB(), nullable=True),
        *timestamp_columns(),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["integration_id"], ["integrations.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("project_id", "full_name", name="uq_repositories_project_full_name"),
    )
    op.create_index("idx_repositories_workspace", "repositories", ["workspace_id"])
    op.create_index("idx_repositories_project", "repositories", ["project_id"])
    op.create_index(
        "idx_repositories_deleted",
        "repositories",
        ["deleted_at"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # 13. Audit logs foreign key constraints
    op.create_foreign_key(
        "fk_audit_logs_workspace_id_workspaces",
        "audit_logs",
        "workspaces",
        ["workspace_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_audit_logs_user_id_users",
        "audit_logs",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Revert tenancy hardening, composite constraints, and added tables."""
    # 13. Drop audit logs foreign keys
    op.drop_constraint("fk_audit_logs_user_id_users", "audit_logs", type_="foreignkey")
    op.drop_constraint("fk_audit_logs_workspace_id_workspaces", "audit_logs", type_="foreignkey")

    # 12. Drop repositories table
    op.drop_index("idx_repositories_deleted", table_name="repositories")
    op.drop_index("idx_repositories_project", table_name="repositories")
    op.drop_index("idx_repositories_workspace", table_name="repositories")
    op.drop_table("repositories")

    # 11. Drop approvals table
    op.drop_index("idx_approvals_plan_hash", table_name="approvals")
    op.drop_index("idx_approvals_status", table_name="approvals")
    op.drop_index("idx_approvals_project", table_name="approvals")
    op.drop_index("idx_approvals_workspace", table_name="approvals")
    op.drop_table("approvals")

    # 10. Drop sync jobs table
    op.drop_index("idx_sync_jobs_status", table_name="sync_jobs")
    op.drop_index("idx_sync_jobs_workspace", table_name="sync_jobs")
    op.drop_table("sync_jobs")

    # 9. Drop agent runs scoping additions
    op.drop_index("idx_agent_runs_project", table_name="agent_runs")
    op.drop_index("idx_agent_runs_workspace", table_name="agent_runs")
    op.drop_constraint("fk_agent_runs_project_id_projects", "agent_runs", type_="foreignkey")
    op.drop_constraint("fk_agent_runs_workspace_id_workspaces", "agent_runs", type_="foreignkey")
    op.drop_column("agent_runs", "project_id")
    op.drop_column("agent_runs", "workspace_id")

    # 8. Drop tools workspace scoping and composite key
    op.drop_index("idx_tools_workspace", table_name="tools")
    op.drop_constraint("fk_tools_project_workspace", "tools", type_="foreignkey")
    op.drop_constraint("fk_tools_workspace_id_workspaces", "tools", type_="foreignkey")
    op.drop_column("tools", "workspace_id")

    # 7. Drop documents workspace scoping and composite key
    op.drop_index("idx_documents_workspace", table_name="documents")
    op.drop_constraint("fk_documents_project_workspace", "documents", type_="foreignkey")
    op.drop_constraint("fk_documents_workspace_id_workspaces", "documents", type_="foreignkey")
    op.drop_column("documents", "workspace_id")

    # 6. Drop messages role
    op.drop_column("messages", "role")

    # 5. Drop conversations composite key
    op.drop_constraint("fk_conversations_project_workspace", "conversations", type_="foreignkey")

    # 4. Drop projects composite unique constraint
    op.drop_constraint("uq_projects_id_workspace_id", "projects", type_="unique")

    # 3. Drop workspace invitations table
    op.drop_index("idx_workspace_invitations_token_hash", table_name="workspace_invitations")
    op.drop_index("idx_workspace_invitations_workspace_email", table_name="workspace_invitations")
    op.drop_table("workspace_invitations")

    # 2. Drop user sessions table
    op.drop_index("idx_user_sessions_expires", table_name="user_sessions")
    op.drop_index("idx_user_sessions_token_hash", table_name="user_sessions")
    op.drop_index("idx_user_sessions_user_id", table_name="user_sessions")
    op.drop_table("user_sessions")

    # 1. Drop user account additions
    op.drop_column("users", "avatar_url")
    op.drop_column("users", "password_hash")
