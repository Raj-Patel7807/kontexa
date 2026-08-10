"""Tool and AgentRun models — tool definitions and execution history."""

import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from kontexa.database.models.base import UUIDPrimaryKeyMixin
from kontexa.database.session import Base


class Tool(UUIDPrimaryKeyMixin, Base):
    """Custom action or tool defined per project (e.g. web search, code executor)."""

    __tablename__ = "tools"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    config: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )


class AgentRun(UUIDPrimaryKeyMixin, Base):
    """Log of a single tool or AI agent execution run."""

    __tablename__ = "agent_runs"
    __table_args__ = (Index("idx_agent_runs_tool", "tool_id"),)

    tool_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tools.id", ondelete="SET NULL"),
        nullable=True,
    )
    inputs: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)
    outputs: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)
    status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True, default=None
    )
