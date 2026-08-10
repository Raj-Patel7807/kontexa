"""Document, DocumentVersion, and DocumentChunk models for RAG knowledge storage."""

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import TIMESTAMP, ForeignKey, Index, Integer, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from kontexa.database.models.base import UUIDPrimaryKeyMixin
from kontexa.database.session import Base

# Embedding dimension — 1536 matches OpenAI text-embedding-ada-002.
EMBEDDING_DIMENSION = 1536


class Document(UUIDPrimaryKeyMixin, Base):
    """A high-level knowledge document (e.g. a Notion page, GitHub PR, Slack thread)."""

    __tablename__ = "documents"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, nullable=True, default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )


class DocumentVersion(UUIDPrimaryKeyMixin, Base):
    """An immutable snapshot of a document's content, enabling version tracking."""

    __tablename__ = "document_versions"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )


class DocumentChunk(UUIDPrimaryKeyMixin, Base):
    """A text chunk of a document version with an embedding vector for similarity search."""

    __tablename__ = "document_chunks"
    __table_args__ = (
        Index("idx_chunks_doc_version", "document_version_id"),
    )

    document_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding = mapped_column(Vector(EMBEDDING_DIMENSION), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
