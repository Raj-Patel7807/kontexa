"""MemoryEntry model — long-term agent memory storage."""

import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, ForeignKey, Index, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from kontexa.database.models.base import UUIDPrimaryKeyMixin
from kontexa.database.session import Base


class MemoryEntry(UUIDPrimaryKeyMixin, Base):
    """Persistent memory entry for long-term agent context, scoped to a workspace."""

    __tablename__ = "memory_entries"
    __table_args__ = (Index("idx_memory_workspace", "workspace_id"),)

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    key: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
