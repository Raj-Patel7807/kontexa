"""FastAPI route handlers for conversations and persistent messages."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from kontexa.api.deps import (
    get_conversation_service,
    get_current_user,
    require_csrf,
)
from kontexa.database.models.users import User
from kontexa.schemas.conversations import (
    ConversationCreateRequest,
    ConversationResponse,
    ConversationUpdateRequest,
    MessageCreateRequest,
    MessageResponse,
)
from kontexa.services.conversations import ConversationService

router = APIRouter(
    prefix="/workspaces/{workspace_id}/conversations",
    tags=["Conversations & Chat"],
)


@router.get(
    "",
    response_model=list[ConversationResponse],
    summary="List workspace conversations",
)
async def list_conversations(
    workspace_id: Annotated[uuid.UUID, Path(description="Target workspace identifier")],
    user: Annotated[User, Depends(get_current_user)],
    conv_service: Annotated[ConversationService, Depends(get_conversation_service)],
    project_id: Annotated[uuid.UUID | None, Query(description="Filter by project")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ConversationResponse]:
    """List conversations scoped to a workspace with optional project filtering."""
    conversations = await conv_service.list_conversations(
        workspace_id=workspace_id,
        user_id=user.id,
        project_id=project_id,
        limit=limit,
        offset=offset,
    )
    return [ConversationResponse.model_validate(c) for c in conversations]


@router.post(
    "",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
    summary="Create conversation thread",
)
async def create_conversation(
    workspace_id: Annotated[uuid.UUID, Path(description="Target workspace identifier")],
    payload: ConversationCreateRequest,
    user: Annotated[User, Depends(get_current_user)],
    conv_service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> ConversationResponse:
    """Initialize a new conversation thread within the workspace."""
    conversation = await conv_service.create_conversation(
        workspace_id=workspace_id,
        user_id=user.id,
        payload=payload,
    )
    return ConversationResponse.model_validate(conversation)


@router.get(
    "/{conversation_id}",
    response_model=ConversationResponse,
    summary="Get conversation details",
)
async def get_conversation(
    workspace_id: Annotated[uuid.UUID, Path(description="Target workspace identifier")],
    conversation_id: Annotated[uuid.UUID, Path(description="Target conversation identifier")],
    user: Annotated[User, Depends(get_current_user)],
    conv_service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> ConversationResponse:
    """Get conversation metadata ensuring strict workspace ownership."""
    conversation = await conv_service.get_conversation(
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        user_id=user.id,
    )
    return ConversationResponse.model_validate(conversation)


@router.patch(
    "/{conversation_id}",
    response_model=ConversationResponse,
    dependencies=[Depends(require_csrf)],
    summary="Rename conversation",
)
async def update_conversation(
    workspace_id: Annotated[uuid.UUID, Path(description="Target workspace identifier")],
    conversation_id: Annotated[uuid.UUID, Path(description="Target conversation identifier")],
    payload: ConversationUpdateRequest,
    user: Annotated[User, Depends(get_current_user)],
    conv_service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> ConversationResponse:
    """Rename conversation."""
    conversation = await conv_service.update_conversation(
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        user_id=user.id,
        payload=payload,
    )
    return ConversationResponse.model_validate(conversation)


@router.delete(
    "/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
    summary="Delete conversation",
)
async def delete_conversation(
    workspace_id: Annotated[uuid.UUID, Path(description="Target workspace identifier")],
    conversation_id: Annotated[uuid.UUID, Path(description="Target conversation identifier")],
    user: Annotated[User, Depends(get_current_user)],
    conv_service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> None:
    """Soft delete conversation thread."""
    await conv_service.delete_conversation(
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        user_id=user.id,
    )


@router.get(
    "/{conversation_id}/messages",
    response_model=list[MessageResponse],
    summary="List messages in conversation",
)
async def list_messages(
    workspace_id: Annotated[uuid.UUID, Path(description="Target workspace identifier")],
    conversation_id: Annotated[uuid.UUID, Path(description="Target conversation identifier")],
    user: Annotated[User, Depends(get_current_user)],
    conv_service: Annotated[ConversationService, Depends(get_conversation_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[MessageResponse]:
    """Retrieve chronologically ordered messages in a conversation."""
    messages = await conv_service.list_messages(
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        user_id=user.id,
        limit=limit,
        offset=offset,
    )
    return [MessageResponse.model_validate(m) for m in messages]


@router.post(
    "/{conversation_id}/messages",
    response_model=list[MessageResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
    summary="Send message and receive assistant response",
)
async def send_message(
    workspace_id: Annotated[uuid.UUID, Path(description="Target workspace identifier")],
    conversation_id: Annotated[uuid.UUID, Path(description="Target conversation identifier")],
    payload: MessageCreateRequest,
    user: Annotated[User, Depends(get_current_user)],
    conv_service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> list[MessageResponse]:
    """Post user message and receive the persisted user message and assistant reply."""
    user_msg, assistant_msg = await conv_service.send_message(
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        user_id=user.id,
        payload=payload,
    )
    return [
        MessageResponse.model_validate(user_msg),
        MessageResponse.model_validate(assistant_msg),
    ]
