"""User account model."""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kontexa.database.models.base import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from kontexa.database.session import Base

if TYPE_CHECKING:
    from kontexa.database.models.sessions import UserSession


class User(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Global user account. Not workspace-scoped — users can belong to multiple workspaces."""

    __tablename__ = "users"
    __table_args__ = (
        Index("idx_users_deleted", "deleted_at", postgresql_where="deleted_at IS NULL"),
    )

    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    sessions: Mapped[list["UserSession"]] = relationship(
        "UserSession", back_populates="user", cascade="all, delete-orphan"
    )
