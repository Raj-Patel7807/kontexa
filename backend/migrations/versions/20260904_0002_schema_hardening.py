"""Harden existing schema constraints and indexes.

Revision ID: 20260904_0002
Revises: 20260811_0001
Create Date: 2026-09-04
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260904_0002"
down_revision: str | None = "20260811_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add schema integrity constraints and targeted foreign-key indexes."""
    op.drop_constraint("workspaces_name_key", "workspaces", type_="unique")

    op.create_unique_constraint(
        "uq_message_parts_message_id_part_index",
        "message_parts",
        ["message_id", "part_index"],
    )
    op.create_unique_constraint(
        "uq_document_chunks_document_version_id_chunk_index",
        "document_chunks",
        ["document_version_id", "chunk_index"],
    )
    op.create_unique_constraint(
        "uq_ai_models_provider_id_model_name",
        "ai_models",
        ["provider_id", "model_name"],
    )

    op.create_foreign_key(
        "fk_memory_entries_user_id_users",
        "memory_entries",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_index("idx_conversations_project", "conversations", ["project_id"])
    op.create_index("idx_documents_project", "documents", ["project_id"])
    op.create_index("idx_document_versions_document", "document_versions", ["document_id"])
    op.create_index("idx_tools_project", "tools", ["project_id"])

    op.drop_index("idx_message_parts_msg", table_name="message_parts")
    op.drop_index("idx_chunks_doc_version", table_name="document_chunks")
    op.drop_index("idx_ai_models_provider", table_name="ai_models")


def downgrade() -> None:
    """Restore the prior schema indexes and constraints."""
    op.create_index("idx_message_parts_msg", "message_parts", ["message_id"])
    op.create_index("idx_chunks_doc_version", "document_chunks", ["document_version_id"])
    op.create_index("idx_ai_models_provider", "ai_models", ["provider_id"])

    op.drop_index("idx_tools_project", table_name="tools")
    op.drop_index("idx_document_versions_document", table_name="document_versions")
    op.drop_index("idx_documents_project", table_name="documents")
    op.drop_index("idx_conversations_project", table_name="conversations")

    op.drop_constraint("fk_memory_entries_user_id_users", "memory_entries", type_="foreignkey")
    op.drop_constraint("uq_ai_models_provider_id_model_name", "ai_models", type_="unique")
    op.drop_constraint(
        "uq_document_chunks_document_version_id_chunk_index",
        "document_chunks",
        type_="unique",
    )
    op.drop_constraint(
        "uq_message_parts_message_id_part_index",
        "message_parts",
        type_="unique",
    )
    op.create_unique_constraint("workspaces_name_key", "workspaces", ["name"])
