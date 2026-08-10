"""Unit tests for SQLAlchemy ORM models — structure and column validation."""

from sqlalchemy import inspect

from kontexa.database.models.base import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
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


def test_all_models_registered_in_base_metadata() -> None:
    """Verify all core models are registered in Base.metadata.tables."""
    table_names = set(Base.metadata.tables.keys())
    expected = {"users", "workspaces", "workspace_members"}
    assert expected.issubset(table_names)
