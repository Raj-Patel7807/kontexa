"""Integration test for database session factory initialization."""

from pathlib import Path

import pytest

import kontexa.database.models  # noqa: F401 - importing the registry populates Base metadata
from kontexa.database.session import AsyncSessionLocal, Base, engine


@pytest.mark.asyncio
async def test_database_engine_and_session_initialization() -> None:
    """Verify SQLAlchemy engine and session factory are instantiated properly."""
    assert engine is not None
    async with AsyncSessionLocal() as session:
        assert session is not None


def test_all_schema_tables_are_registered() -> None:
    """Verify Alembic can discover every table through the central model registry."""
    assert set(Base.metadata.tables) == {
        "users",
        "workspaces",
        "workspace_members",
        "projects",
        "conversations",
        "messages",
        "message_parts",
        "documents",
        "document_versions",
        "document_chunks",
        "integrations",
        "memory_entries",
        "tools",
        "agent_runs",
        "ai_providers",
        "ai_models",
        "ai_usage",
        "audit_logs",
    }


def test_aiven_schema_includes_every_registered_table() -> None:
    """Verify manual Aiven provisioning stays aligned with the ORM model registry."""
    schema_path = Path(__file__).resolve().parents[3] / "infrastructure" / "database" / "schema.sql"
    schema = schema_path.read_text(encoding="utf-8")

    assert "CREATE EXTENSION IF NOT EXISTS vector;" in schema
    for table_name in Base.metadata.tables:
        assert f"CREATE TABLE {table_name} (" in schema
