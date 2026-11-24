"""SyncJob model — external connector synchronization execution history."""

import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from kontexa.database.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from kontexa.database.session import Base


class SyncJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Execution record for connector data synchronization (e.g. GitHub repos, documents)."""

    __tablename__ = "sync_jobs"
    __table_args__ = (
        Index("idx_sync_jobs_workspace", "workspace_id"),
        Index("idx_sync_jobs_status", "status"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
    )
    integration_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("integrations.id", ondelete="SET NULL"),
        nullable=True,
    )
    job_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    trigger: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    started_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True, default=None
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True, default=None
    )
    records_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True, default=None)
