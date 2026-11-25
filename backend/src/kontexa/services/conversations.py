"""Domain service for managing conversations, message persistence, and chat interactions."""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from kontexa.core.exceptions import ResourceNotFoundError
from kontexa.database.models.conversations import Conversation
from kontexa.database.models.messages import Message
from kontexa.database.models.projects import Project
from kontexa.schemas.conversations import (
    ConversationCreateRequest,
    ConversationUpdateRequest,
    MessageCreateRequest,
    MessageRole,
)
from kontexa.services.workspaces import WorkspaceRole, WorkspaceService

logger = logging.getLogger(__name__)


def generate_title_from_content(content: str) -> str:
    """Derive a clean conversation title from the first message content."""
    clean_text = " ".join(content.strip().split())
    if len(clean_text) <= 50:
        return clean_text
    return clean_text[:47].rstrip() + "..."


class ConversationService:
    """Service encapsulating conversation and message persistence with workspace scoping."""

    def __init__(self, db: AsyncSession, ws_service: WorkspaceService) -> None:
        self.db = db
        self.ws_service = ws_service

    async def list_conversations(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        project_id: uuid.UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Conversation]:
        """List active conversations for a workspace, optionally filtered by project."""
        await self.ws_service.require_workspace_access(
            workspace_id=workspace_id,
            user_id=user_id,
            required_role=WorkspaceRole.VIEWER,
        )

        query = (
            select(Conversation)
            .where(
                Conversation.workspace_id == workspace_id,
                Conversation.deleted_at.is_(None),
            )
            .order_by(desc(Conversation.updated_at))
            .limit(limit)
            .offset(offset)
        )

        if project_id:
            query = query.where(Conversation.project_id == project_id)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_conversation(
        self,
        workspace_id: uuid.UUID,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Conversation:
        """Fetch conversation, enforcing workspace scoping and membership."""
        await self.ws_service.require_workspace_access(
            workspace_id=workspace_id,
            user_id=user_id,
            required_role=WorkspaceRole.VIEWER,
        )

        query = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.workspace_id == workspace_id,
            Conversation.deleted_at.is_(None),
        )
        result = await self.db.execute(query)
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise ResourceNotFoundError(
                f"Conversation {conversation_id} not found in workspace {workspace_id}."
            )
        return conversation

    async def create_conversation(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: ConversationCreateRequest,
    ) -> Conversation:
        """Initialize a new conversation thread within the workspace."""
        await self.ws_service.require_workspace_access(
            workspace_id=workspace_id,
            user_id=user_id,
            required_role=WorkspaceRole.MEMBER,
        )

        # If project_id is provided, verify it belongs to this workspace
        if payload.project_id:
            prj_query = select(Project.id).where(
                Project.id == payload.project_id,
                Project.workspace_id == workspace_id,
                Project.deleted_at.is_(None),
            )
            prj_res = await self.db.execute(prj_query)
            if not prj_res.scalar_one_or_none():
                raise ResourceNotFoundError(
                    f"Project {payload.project_id} not found in workspace {workspace_id}."
                )

        conversation = Conversation(
            workspace_id=workspace_id,
            project_id=payload.project_id,
            title=payload.title or "New Conversation",
            is_active=True,
        )
        self.db.add(conversation)
        await self.db.commit()
        await self.db.refresh(conversation)
        return conversation

    async def update_conversation(
        self,
        workspace_id: uuid.UUID,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: ConversationUpdateRequest,
    ) -> Conversation:
        """Rename an existing conversation."""
        await self.ws_service.require_workspace_access(
            workspace_id=workspace_id,
            user_id=user_id,
            required_role=WorkspaceRole.MEMBER,
        )

        conversation = await self.get_conversation(
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            user_id=user_id,
        )
        conversation.title = payload.title
        conversation.updated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(conversation)
        return conversation

    async def delete_conversation(
        self,
        workspace_id: uuid.UUID,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Soft delete a conversation thread."""
        await self.ws_service.require_workspace_access(
            workspace_id=workspace_id,
            user_id=user_id,
            required_role=WorkspaceRole.MEMBER,
        )

        conversation = await self.get_conversation(
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            user_id=user_id,
        )
        conversation.deleted_at = datetime.now(UTC)
        await self.db.commit()

    async def list_messages(
        self,
        workspace_id: uuid.UUID,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Message]:
        """Fetch all messages for a conversation in chronological order."""
        # Validates membership & conversation workspace scoping
        await self.get_conversation(
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            user_id=user_id,
        )

        query = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def send_message(
        self,
        workspace_id: uuid.UUID,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: MessageCreateRequest,
    ) -> tuple[Message, Message]:
        """Post a user message, perform title derivation, and generate a dev response."""
        await self.ws_service.require_workspace_access(
            workspace_id=workspace_id,
            user_id=user_id,
            required_role=WorkspaceRole.MEMBER,
        )

        conversation = await self.get_conversation(
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            user_id=user_id,
        )

        # Idempotency check: if client provided an idempotency key, check if already recorded
        metadata: dict[str, Any] = {}
        if payload.idempotency_key:
            metadata["idempotency_key"] = payload.idempotency_key
            # Check for existing message with matching idempotency key in this conversation
            existing_query = select(Message).where(
                Message.conversation_id == conversation_id,
                Message.role == MessageRole.USER,
            )
            existing_res = await self.db.execute(existing_query)
            for msg in existing_res.scalars().all():
                if (
                    msg.metadata_
                    and msg.metadata_.get("idempotency_key") == payload.idempotency_key
                ):
                    # Return existing user message and subsequent assistant response
                    assist_query = (
                        select(Message)
                        .where(
                            Message.conversation_id == conversation_id,
                            Message.role == MessageRole.ASSISTANT,
                            Message.created_at >= msg.created_at,
                        )
                        .order_by(Message.created_at.asc())
                        .limit(1)
                    )
                    assist_res = await self.db.execute(assist_query)
                    assist_msg = assist_res.scalar_one_or_none()
                    if assist_msg:
                        return msg, assist_msg

        # Persist user message
        user_msg = Message(
            conversation_id=conversation_id,
            user_id=user_id,
            role=MessageRole.USER,
            content=payload.content,
            metadata_=metadata if metadata else None,
        )
        self.db.add(user_msg)

        # Update title if still generic "New Conversation"
        if not conversation.title or conversation.title == "New Conversation":
            conversation.title = generate_title_from_content(payload.content)

        conversation.updated_at = datetime.now(UTC)

        # Deterministic assistant response for Sprint 10 (labelled development adapter)
        assistant_content = (
            f"**[Development AI Adapter]** Received query:\n\n"
            f"> {payload.content}\n\n"
            f"Conversation is active under workspace `{workspace_id}`. "
            f"Full LLM provider streaming gateway will be connected in Sprint 11–12."
        )

        assistant_msg = Message(
            conversation_id=conversation_id,
            user_id=None,
            role=MessageRole.ASSISTANT,
            content=assistant_content,
            metadata_={"adapter": "deterministic_sprint10", "is_mock": True},
        )
        self.db.add(assistant_msg)

        await self.db.commit()
        await self.db.refresh(user_msg)
        await self.db.refresh(assistant_msg)

        return user_msg, assistant_msg
