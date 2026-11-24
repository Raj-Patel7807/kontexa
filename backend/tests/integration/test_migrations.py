"""Integration test suite for Alembic migrations, revision linearity, and offline DDL."""

import io
from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

from kontexa.database.session import Base


def _get_alembic_config(buffer: io.StringIO | None = None) -> Config:
    """Instantiate an Alembic Config pointing to backend/alembic.ini."""
    backend_dir = Path(__file__).resolve().parents[2]
    ini_path = backend_dir / "alembic.ini"
    cfg = Config(str(ini_path), stdout=buffer)
    cfg.set_main_option("script_location", str(backend_dir / "migrations"))
    return cfg


def test_alembic_migration_chain_is_strictly_linear() -> None:
    """Verify the migration chain has a single head and zero orphaned branches."""
    cfg = _get_alembic_config()
    script = ScriptDirectory.from_config(cfg)

    # 1. Ensure exactly one head revision
    heads = script.get_heads()
    assert len(heads) == 1, f"Expected exactly 1 migration head, found: {heads}"
    assert heads[0] == "20261125_0003"

    # 2. Walk revision chain from head back to base
    revisions: list[str] = []
    current = script.get_revision("20261125_0003")
    while current is not None:
        revisions.append(current.revision)
        down = current.down_revision
        if down is None:
            break
        assert isinstance(down, str), "Multiple down_revisions detected; branching is forbidden"
        current = script.get_revision(down)

    expected_chain = [
        "20261125_0003",
        "20260904_0002",
        "20260811_0001",
    ]
    assert revisions == expected_chain


def test_alembic_offline_upgrade_compiles_all_revisions(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify Alembic offline SQL upgrade compiles from empty DB to latest head."""
    from alembic import command

    cfg = _get_alembic_config()

    # Compile SQL from base to head
    command.upgrade(cfg, "head", sql=True)
    captured = capsys.readouterr()
    generated_sql = captured.out

    assert "CREATE TABLE users" in generated_sql
    assert "CREATE TABLE user_sessions" in generated_sql
    assert "CREATE TABLE workspace_invitations" in generated_sql
    assert "CREATE TABLE sync_jobs" in generated_sql
    assert "CREATE TABLE approvals" in generated_sql
    assert "CREATE TABLE repositories" in generated_sql
    assert "uq_projects_id_workspace_id" in generated_sql
    assert "fk_conversations_project_workspace" in generated_sql
    assert "fk_documents_project_workspace" in generated_sql
    assert "fk_tools_project_workspace" in generated_sql
    assert "UPDATE alembic_version SET version_num='20261125_0003'" in generated_sql


def test_alembic_offline_downgrade_compiles_cleanly(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify Alembic offline SQL downgrade rolls back cleanly from head to base."""
    from alembic import command

    cfg = _get_alembic_config()

    command.downgrade(cfg, "20261125_0003:base", sql=True)
    captured = capsys.readouterr()
    generated_sql = captured.out

    assert "DROP TABLE repositories" in generated_sql
    assert "DROP TABLE approvals" in generated_sql
    assert "DROP TABLE sync_jobs" in generated_sql
    assert "DROP TABLE workspace_invitations" in generated_sql
    assert "DROP TABLE user_sessions" in generated_sql
    assert "DROP TABLE users" in generated_sql


def test_tenant_scoping_invariant_across_all_workspace_tables() -> None:
    """Verify every tenant-owned table explicitly includes a workspace_id foreign key."""
    # Global tables that intentionally cross workspaces
    global_tables = {
        "users",
        "user_sessions",
        "workspaces",
        "ai_providers",
        "ai_models",
    }

    # Child tables whose scoping is inherited from an immediate parent
    indirectly_scoped_tables = {
        "workspace_members",  # composite primary key (workspace_id, user_id)
        "messages",  # scoped through conversation_id
        "message_parts",  # scoped through message_id
        "document_versions",  # scoped through document_id
        "document_chunks",  # scoped through document_version_id
    }

    for table_name, table in Base.metadata.tables.items():
        if table_name in global_tables or table_name in indirectly_scoped_tables:
            continue

        # Every other table MUST have an explicit workspace_id column
        assert "workspace_id" in table.columns, (
            f"Tenant invariant violation: table '{table_name}' lacks explicit workspace_id scoping"
        )
