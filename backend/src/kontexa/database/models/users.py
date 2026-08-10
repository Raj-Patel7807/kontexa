"""User account model."""

from sqlalchemy import Boolean, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from kontexa.database.models.base import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from kontexa.database.session import Base


class User(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Global user account. Not workspace-scoped — users can belong to multiple workspaces."""

    __tablename__ = "users"
    __table_args__ = (
        Index("idx_users_deleted", "deleted_at", postgresql_where="deleted_at IS NULL"),
    )

    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
