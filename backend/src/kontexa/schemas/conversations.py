"""Pydantic schemas for conversations, chat messages, and thread history."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MessageRole(str):
    """Allowed roles in a conversation thread."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageCreateRequest(BaseModel):
    """Payload to send a message within a conversation."""

    content: str = Field(min_length=1, max_length=50000, description="Message text content")
    idempotency_key: str | None = Field(
        default=None,
        max_length=128,
        description="Optional client idempotency token to prevent double-submission.",
    )


class MessageResponse(BaseModel):
    """Public representation of a single message."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    user_id: uuid.UUID | None
    role: str
    content: str
    metadata_: dict[str, Any] | None = Field(default=None, serialization_alias="metadata")
    created_at: datetime


class ConversationCreateRequest(BaseModel):
    """Payload to initialize a new conversation thread."""

    project_id: uuid.UUID | None = Field(
        default=None,
        description="Optional project ID to associate thread within the workspace.",
    )
    title: str | None = Field(
        default=None,
        max_length=200,
        description="Optional title; auto-generated from first message if omitted.",
    )


class ConversationUpdateRequest(BaseModel):
    """Payload to rename or update conversation metadata."""

    title: str = Field(min_length=1, max_length=200, description="Updated conversation title")


class ConversationResponse(BaseModel):
    """Public representation of a conversation thread."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    project_id: uuid.UUID | None
    title: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ConversationDetailResponse(ConversationResponse):
    """Conversation summary including latest messages."""

    messages: list[MessageResponse] = Field(default_factory=list)
