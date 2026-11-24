"""Repository model — tracked code repositories and indexing state."""

import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from kontexa.database.models.base import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from kontexa.database.session import Base


class Repository(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """External code repository connected to a project with indexation metadata."""

    __tablename__ = "repositories"
    __table_args__ = (
        UniqueConstraint("project_id", "full_name", name="uq_repositories_project_full_name"),
        Index("idx_repositories_workspace", "workspace_id"),
        Index("idx_repositories_project", "project_id"),
        Index("idx_repositories_deleted", "deleted_at", postgresql_where="deleted_at IS NULL"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    integration_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("integrations.id", ondelete="SET NULL"),
        nullable=True,
    )
    remote_id: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    default_branch: Mapped[str] = mapped_column(String(50), nullable=False, default="main")
    clone_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="not_indexed")
    last_synced_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True, default=None
    )
    index_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)
