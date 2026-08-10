"""Message and MessagePart models — chat message storage."""

import uuid

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from kontexa.database.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from kontexa.database.session import Base


class Message(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single message in a conversation, sent by a user or an AI assistant."""

    __tablename__ = "messages"
    __table_args__ = (Index("idx_messages_conversation", "conversation_id"),)

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, nullable=True, default=None
    )


class MessagePart(UUIDPrimaryKeyMixin, Base):
    """Sub-part of a large message, allowing chunked storage with MIME type tagging."""

    __tablename__ = "message_parts"
    __table_args__ = (Index("idx_message_parts_msg", "message_id"),)

    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
    )
    part_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
