"""AI provider, model, and usage tracking models."""

import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, BigInteger, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from kontexa.database.models.base import UUIDPrimaryKeyMixin
from kontexa.database.session import Base


class AIProvider(UUIDPrimaryKeyMixin, Base):
    """Registered AI provider (e.g. OpenAI, Anthropic)."""

    __tablename__ = "ai_providers"

    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    config: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )


class AIModel(UUIDPrimaryKeyMixin, Base):
    """Supported model under an AI provider (e.g. gpt-4o, claude-3-5-sonnet)."""

    __tablename__ = "ai_models"
    __table_args__ = (Index("idx_ai_models_provider", "provider_id"),)

    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_providers.id", ondelete="CASCADE"),
        nullable=False,
    )
    model_name: Mapped[str] = mapped_column(String, nullable=False)
    max_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )


class AIUsage(UUIDPrimaryKeyMixin, Base):
    """Token consumption and cost log per user / workspace / model."""

    __tablename__ = "ai_usage"
    __table_args__ = (Index("idx_ai_usage_model", "model_id"),)

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_models.id", ondelete="CASCADE"),
        nullable=False,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    tokens_used: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text("0"))
    cost_cents: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text("0"))
    timestamp: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
