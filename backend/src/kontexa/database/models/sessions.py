"""User session and token lifecycle tracking models."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import TIMESTAMP, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kontexa.database.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from kontexa.database.session import Base

if TYPE_CHECKING:
    from kontexa.database.models.users import User


class UserSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Active user session tracking for authentication, refresh tokens, and revocation."""

    __tablename__ = "user_sessions"
    __table_args__ = (
        Index("idx_user_sessions_user_id", "user_id"),
        Index("idx_user_sessions_token_hash", "token_hash", unique=True),
        Index("idx_user_sessions_expires", "expires_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True, default=None
    )

    user: Mapped["User"] = relationship("User", back_populates="sessions")
