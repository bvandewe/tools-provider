"""Chat controller for the conversational AI interface."""

import json
import logging
from typing import Any, Optional

from classy_fastapi.decorators import delete, get, post, put
from fastapi import Depends, Query
from fastapi.responses import StreamingResponse
from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from neuroglia.mvc import ControllerBase
from pydantic import BaseModel, Field

from api.dependencies import get_access_token, get_chat_service, get_current_user, require_session
from application.commands import CreateConversationCommand, DeleteConversationCommand
from application.queries import GetConversationQuery, GetConversationsQuery
from application.services.chat_service import ChatService
from domain.entities.conversation import Conversation
from infrastructure.session_store import RedisSessionStore

logger = logging.getLogger(__name__)


class SendMessageRequest(BaseModel):
    """Request body for sending a chat message."""

    message: str = Field(..., min_length=1, max_length=10000, description="User message")
    conversation_id: Optional[str] = Field(None, description="Optional conversation ID to continue")


class RenameConversationRequest(BaseModel):
    """Request body for renaming a conversation."""

    title: str = Field(..., min_length=1, max_length=200, description="New conversation title")


class ConversationResponse(BaseModel):
    """Response containing conversation information."""

    id: str
    title: Optional[str]
    created_at: str
    updated_at: str
    message_count: int


class ToolResponse(BaseModel):
    """Response containing tool information."""

    name: str
    description: str
    parameters: list[dict[str, Any]]


class ChatController(ControllerBase):
    """Controller for chat and conversation endpoints with CQRS pattern."""

    def __init__(self, service_provider: ServiceProviderBase, mapper: Mapper, mediator: Mediator):
        super().__init__(service_provider, mapper, mediator)
        self._session_store: Optional[RedisSessionStore] = None

    @property
    def session_store(self) -> RedisSessionStore:
        """Lazy-load RedisSessionStore from DI container."""
        if self._session_store is None:
            self._session_store = self.service_provider.get_required_service(RedisSessionStore)
        return self._session_store

    @post("/send")
    async def send_message(
        self,
        body: SendMessageRequest,
        user: dict = Depends(get_current_user),
        access_token: str = Depends(get_access_token),
        session_id: str = Depends(require_session),
        chat_service: ChatService = Depends(get_chat_service),
    ):
        """
        Send a message and stream the AI response.

        Uses Server-Sent Events (SSE) to stream:
        - Content chunks as they're generated
        - Tool call notifications
        - Tool execution results
        - Final message completion
        """
        user_id = user.get("sub", "unknown")

        # Get or create conversation
        conversation_id = body.conversation_id or self.session_store.get_conversation_id(session_id)
        conversation = await chat_service.get_or_create_conversation(user_id, conversation_id)

        # Update session with conversation ID
        self.session_store.set_conversation_id(session_id, conversation.id())

        async def event_generator():
            """Generate SSE events from chat stream."""
            try:
                async for event in chat_service.send_message(
                    conversation=conversation,
                    user_message=body.message,
                    access_token=access_token,
                ):
                    event_type = event.get("event", "message")
                    data = event.get("data", {})
                    yield f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

            except Exception as e:
                logger.error(f"Error in chat stream: {e}")
                yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @get("/conversations")
    async def list_conversations(self, user: dict = Depends(get_current_user)):
        """List all conversations for the current user."""
        query = GetConversationsQuery(user_info=user)
        result = await self.mediator.execute_async(query)

        if result.is_success and result.data:
            # Transform Conversation aggregates to UI-friendly format
            conversations = [
                {
                    "id": conv.id(),
                    "title": conv.state.title or "New conversation",
                    "message_count": len([m for m in conv.state.messages if m.get("role") != "system"]),
                    "created_at": conv.state.created_at.isoformat() if conv.state.created_at else None,
                    "updated_at": conv.state.updated_at.isoformat() if conv.state.updated_at else None,
                }
                for conv in result.data
            ]
            return conversations

        return self.process(result)

    @get("/conversations/{conversation_id}")
    async def get_conversation(
        self,
        conversation_id: str,
        user: dict = Depends(get_current_user),
    ):
        """Get a specific conversation with messages."""
        query = GetConversationQuery(conversation_id=conversation_id, user_info=user)
        result = await self.mediator.execute_async(query)

        if result.is_success and result.data:
            conv = result.data
            # Transform to UI-friendly format with messages
            return {
                "id": conv.id(),
                "title": conv.state.title or "New conversation",
                "message_count": len([m for m in conv.state.messages if m.get("role") != "system"]),
                "created_at": conv.state.created_at.isoformat() if conv.state.created_at else None,
                "updated_at": conv.state.updated_at.isoformat() if conv.state.updated_at else None,
                "messages": [
                    {
                        "id": m.get("id"),
                        "role": m.get("role"),
                        "content": m.get("content", ""),
                        "created_at": m.get("created_at"),
                        "status": m.get("status"),
                    }
                    for m in conv.state.messages
                    if m.get("role") != "system"  # Don't expose system messages
                ],
            }

        return self.process(result)

    @delete("/conversations/{conversation_id}")
    async def delete_conversation(
        self,
        conversation_id: str,
        user: dict = Depends(get_current_user),
    ):
        """Delete a conversation."""
        command = DeleteConversationCommand(conversation_id=conversation_id, user_info=user)
        result = await self.mediator.execute_async(command)
        return self.process(result)

    @put("/conversations/{conversation_id}/rename")
    async def rename_conversation(
        self,
        conversation_id: str,
        body: RenameConversationRequest,
        user: dict = Depends(get_current_user),
        chat_service: ChatService = Depends(get_chat_service),
    ):
        """Rename a conversation."""
        conversation = await chat_service._conversation_repo.get_async(conversation_id)
        if conversation is None:
            return self.not_found(Conversation, conversation_id)

        user_id = user.get("sub", "unknown")
        if conversation.state.user_id != user_id:
            return self.forbidden("Access denied")

        conversation.update_title(body.title)
        await chat_service._conversation_repo.update_async(conversation)

        return {"id": conversation_id, "title": body.title, "renamed": True}

    @post("/conversations/{conversation_id}/clear")
    async def clear_conversation(
        self,
        conversation_id: str,
        user: dict = Depends(get_current_user),
        chat_service: ChatService = Depends(get_chat_service),
    ):
        """Clear messages from a conversation (keeps system prompt)."""
        # For now, use the chat service directly
        # TODO: Create a ClearConversationCommand
        conversation = await chat_service._conversation_repo.get_async(conversation_id)
        if conversation is None:
            return self.not_found(f"Conversation {conversation_id} not found")

        user_id = user.get("sub", "unknown")
        if conversation.state.user_id != user_id:
            return self.forbidden("Access denied")

        conversation.clear_messages(keep_system=True)
        await chat_service._conversation_repo.update_async(conversation)

        return {"cleared": True, "message_count": len(conversation)}

    @get("/tools")
    async def list_tools(
        self,
        access_token: str = Depends(get_access_token),
        refresh: bool = Query(False, description="Force refresh from Tools Provider"),
        chat_service: ChatService = Depends(get_chat_service),
    ):
        """List available tools from the Tools Provider."""
        tools = await chat_service.get_tools(access_token, force_refresh=refresh)

        return [
            ToolResponse(
                name=t.name,
                description=t.description,
                parameters=[p.to_dict() for p in t.parameters],
            )
            for t in tools
        ]

    @post("/new")
    async def start_new_conversation(
        self,
        user: dict = Depends(get_current_user),
        session_id: str = Depends(require_session),
    ):
        """Start a new conversation."""
        from application.settings import app_settings

        command = CreateConversationCommand(
            system_prompt=app_settings.system_prompt,
            user_info=user,
        )
        result = await self.mediator.execute_async(command)

        if result.is_success and result.data:
            # Update session with new conversation ID
            self.session_store.set_conversation_id(session_id, result.data.id)
            return {"conversation_id": result.data.id, "created": True}

        return self.process(result)
