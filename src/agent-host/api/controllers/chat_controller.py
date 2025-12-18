"""Chat controller for the conversational AI interface."""

import json
import logging
import time
from collections.abc import AsyncIterator
from datetime import UTC
from typing import Any
from uuid import uuid4

from classy_fastapi.decorators import delete, get, post, put
from fastapi import Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from fastapi.responses import StreamingResponse
from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from neuroglia.mvc import ControllerBase
from opentelemetry import trace
from pydantic import BaseModel, Field

from api.dependencies import (
    get_access_token,
    get_chat_service,
    get_current_user,
    get_ws_access_token,
    get_ws_current_user,
    get_ws_service_provider,
    require_admin,
    require_session,
)
from application.commands import CreateConversationCommand, DeleteConversationCommand, DeleteConversationsCommand
from application.queries import GetConversationQuery, GetConversationsQuery
from application.queries.definition.get_definitions_query import GetAllDefinitionsQuery
from application.services.chat_service import ChatService
from application.services.tool_provider_client import ToolProviderClient
from domain.entities import AgentDefinition
from domain.entities.conversation import Conversation
from infrastructure.rate_limiter import RateLimiter, get_rate_limiter
from infrastructure.session_store import RedisSessionStore
from observability import chat_messages_received, chat_messages_sent, chat_session_duration

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class SendMessageRequest(BaseModel):
    """Request body for sending a chat message."""

    message: str = Field("", max_length=10000, description="User message (empty for proactive agent start)")
    conversation_id: str | None = Field(None, description="Optional conversation ID to continue")
    model_id: str | None = Field(None, description="Optional model override for this request (e.g., 'openai:gpt-4o')")
    definition_id: str | None = Field(None, description="Optional agent definition ID for the conversation")


class RenameConversationRequest(BaseModel):
    """Request body for renaming a conversation."""

    title: str = Field(..., min_length=1, max_length=200, description="New conversation title")


class DeleteConversationsRequest(BaseModel):
    """Request body for deleting multiple conversations."""

    conversation_ids: list[str] = Field(..., min_length=1, description="List of conversation IDs to delete")


class CreateConversationRequest(BaseModel):
    """Request body for creating a new conversation."""

    definition_id: str | None = Field(None, description="Optional agent definition ID for the conversation")


class ConversationResponse(BaseModel):
    """Response containing conversation information."""

    id: str
    title: str | None
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
        self._session_store: RedisSessionStore | None = None
        self._rate_limiter: RateLimiter | None = None

    @property
    def session_store(self) -> RedisSessionStore:
        """Lazy-load RedisSessionStore from DI container."""
        if self._session_store is None:
            self._session_store = self.service_provider.get_required_service(RedisSessionStore)
        return self._session_store

    @property
    def rate_limiter(self) -> RateLimiter | None:
        """Get rate limiter instance."""
        if self._rate_limiter is None:
            self._rate_limiter = get_rate_limiter()
        return self._rate_limiter

    @post("/send")
    async def send_message(
        self,
        body: SendMessageRequest,
        user: dict[str, Any] = Depends(get_current_user),
        access_token: str = Depends(get_access_token),
        session_id: str = Depends(require_session),
        chat_service: ChatService = Depends(get_chat_service),
    ) -> StreamingResponse:
        """
        Send a message to the AI agent and stream the response.

        **Input:**
        - `message`: The user's text message (1-10,000 characters)
        - `conversation_id`: Optional - continue an existing conversation
        - `model_id`: Optional - override the default LLM model (e.g., 'openai:gpt-4o')

        **Side Effects:**
        - Creates a new conversation if no conversation_id is provided
        - Stores user message and AI response in conversation history
        - Executes tool calls requested by the AI agent
        - Records chat metrics for observability

        **Output (SSE Stream):**
        Returns a Server-Sent Events stream with these event types:
        - `stream_started`: Connection established with request_id and conversation_id
        - `content`: AI-generated text chunks
        - `tool_call`: Notification when a tool is being called
        - `tool_result`: Result of tool execution
        - `error`: Error details if processing fails

        **Rate Limiting:** Applied per user to prevent abuse (configurable).
        """
        user_id = user.get("sub", "unknown")
        request_id = str(uuid4())

        # Record message received metric
        chat_messages_received.add(1, {"user_id": user_id})

        # Start tracing span for the entire chat request
        with tracer.start_as_current_span("chat.send_message") as span:
            span.set_attribute("chat.user_id", user_id)
            span.set_attribute("chat.request_id", request_id)
            span.set_attribute("chat.message_length", len(body.message))

            # Check rate limits
            if self.rate_limiter:
                # Check requests per minute
                allowed, error_msg = await self.rate_limiter.check_rate_limit(user_id)
                if not allowed:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=error_msg,
                    )

                # Check concurrent requests
                allowed, error_msg = await self.rate_limiter.check_concurrent_limit(user_id)
                if not allowed:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=error_msg,
                    )

            # Get or create conversation
            # If definition_id is provided without a specific conversation_id,
            # always create a new conversation (proactive agent start)
            if body.definition_id and not body.conversation_id:
                # Force new conversation for proactive agent start
                conversation_id = None
            else:
                conversation_id = body.conversation_id or self.session_store.get_conversation_id(session_id)
            conversation = await chat_service.get_or_create_conversation(user_id, conversation_id, definition_id=body.definition_id)
            span.set_attribute("chat.conversation_id", conversation.id())

            # Update session with conversation ID
            self.session_store.set_conversation_id(session_id, conversation.id())

            # Track the request for rate limiting
            if self.rate_limiter:
                await self.rate_limiter.start_request(
                    request_id=request_id,
                    user_id=user_id,
                    conversation_id=conversation.id(),
                )

            async def event_generator() -> AsyncIterator[str]:
                """Generate SSE events from chat stream."""
                stream_start = time.time()
                event_count = 0
                tool_call_count = 0

                try:
                    # Send request_id and conversation_id to client so it can track the conversation
                    yield f"event: stream_started\ndata: {json.dumps({'request_id': request_id, 'conversation_id': conversation.id()})}\n\n"

                    async for event in chat_service.send_message(
                        conversation=conversation,
                        user_message=body.message,
                        access_token=access_token,
                        model_id=body.model_id,
                    ):
                        # Check if request was cancelled
                        if self.rate_limiter and self.rate_limiter.is_cancelled(request_id, user_id):
                            logger.info(f"Request {request_id} was cancelled by user")
                            yield f"event: cancelled\ndata: {json.dumps({'message': 'Request cancelled by user'})}\n\n"
                            break

                        event_type = event.get("event", "message")
                        data = event.get("data", {})
                        event_count += 1

                        # Track tool calls
                        if event_type == "tool_call":
                            tool_call_count += 1

                        yield f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

                    # Record metrics on successful completion
                    duration_ms = (time.time() - stream_start) * 1000
                    chat_session_duration.record(duration_ms, {"user_id": user_id, "event_count": str(event_count)})
                    chat_messages_sent.add(1, {"user_id": user_id, "tool_calls": str(tool_call_count)})

                except Exception as e:
                    logger.error(f"Error in chat stream: {e}")
                    yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
                finally:
                    # Clean up request tracking
                    if self.rate_limiter:
                        await self.rate_limiter.end_request(request_id, user_id)

            return StreamingResponse(
                event_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )

    @post("/cancel/{request_id}")
    async def cancel_request(
        self,
        request_id: str,
        user: dict[str, Any] = Depends(get_current_user),
    ) -> dict[str, Any]:
        """
        Cancel an active streaming chat request.

        **Input:**
        - `request_id`: The request_id returned in the `stream_started` SSE event

        **Side Effects:**
        - Marks the request as cancelled in the rate limiter
        - The streaming generator will stop and emit a `cancelled` event
        - No further tool calls will be executed for this request

        **Output:**
        - `cancelled`: Boolean indicating success
        - `request_id`: Echo of the cancelled request ID

        **Note:** Only the user who initiated the request can cancel it.
        """
        user_id = user.get("sub", "unknown")

        if not self.rate_limiter:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Request cancellation not available",
            )

        cancelled = await self.rate_limiter.cancel_request(request_id, user_id)

        if cancelled:
            return {"cancelled": True, "request_id": request_id}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Request not found or already completed",
            )

    @get("/conversations")
    async def list_conversations(self, user: dict[str, Any] = Depends(get_current_user)) -> Any:
        """
        List all conversations for the current user.

        **Output:**
        Returns an array of conversation summaries containing:
        - `id`: Unique conversation identifier
        - `title`: Conversation title (auto-generated or user-defined)
        - `message_count`: Number of messages (excluding system prompt)
        - `definition_id`: Agent definition ID used for this conversation
        - `definition_name`: Agent definition name
        - `definition_icon`: Agent definition icon class
        - `created_at`: ISO timestamp of creation
        - `updated_at`: ISO timestamp of last activity

        Conversations are returned in reverse chronological order (newest first).
        """
        query = GetConversationsQuery(user_info=user)
        result = await self.mediator.execute_async(query)

        if result.is_success and result.data:
            # Fetch all definitions to build a lookup map for icons/names
            definitions_map: dict[str, dict[str, str]] = {}
            definitions_result = await self.mediator.execute_async(GetAllDefinitionsQuery(include_system=True))
            if definitions_result.is_success and definitions_result.data:
                definitions_map = {d.id: {"name": d.name, "icon": d.icon or "bi-robot"} for d in definitions_result.data}

            # Transform ConversationDto to UI-friendly format
            conversations = [
                {
                    "id": conv.id,
                    "title": conv.title or "New conversation",
                    "message_count": len([m for m in conv.messages if m.get("role") != "system"]),
                    "definition_id": conv.definition_id or "",
                    "definition_name": definitions_map.get(conv.definition_id or "", {}).get("name", "Unknown"),
                    "definition_icon": definitions_map.get(conv.definition_id or "", {}).get("icon", "bi-robot"),
                    "created_at": conv.created_at.isoformat() if conv.created_at else None,
                    "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
                }
                for conv in result.data
            ]
            return conversations

        return self.process(result)

    @get("/conversations/{conversation_id}")
    async def get_conversation(
        self,
        conversation_id: str,
        user: dict[str, Any] = Depends(get_current_user),
    ) -> Any:
        """
        Get a specific conversation with full message history.

        **Input:**
        - `conversation_id`: The unique conversation identifier

        **Output:**
        Returns the conversation with:
        - `id`, `title`, `message_count`, `created_at`, `updated_at`
        - `messages`: Array of messages with role, content, tool_calls, and tool_results

        **Authorization:** Users can only access their own conversations.
        """
        query = GetConversationQuery(conversation_id=conversation_id, user_info=user)
        result = await self.mediator.execute_async(query)

        if result.is_success and result.data:
            conv = result.data
            # Transform ConversationDto to UI-friendly format with messages
            return {
                "id": conv.id,
                "title": conv.title or "New conversation",
                "definition_id": conv.definition_id or "",
                "message_count": len([m for m in conv.messages if m.get("role") != "system"]),
                "created_at": conv.created_at.isoformat() if conv.created_at else None,
                "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
                "messages": [
                    {
                        "id": m.get("id"),
                        "role": m.get("role"),
                        "content": m.get("content", ""),
                        "created_at": m.get("created_at"),
                        "status": m.get("status"),
                        "tool_calls": m.get("tool_calls", []),
                        "tool_results": m.get("tool_results", []),
                    }
                    for m in conv.messages
                    if m.get("role") != "system"  # Don't expose system messages
                ],
            }

        return self.process(result)

    @delete("/conversations/{conversation_id}")
    async def delete_conversation(
        self,
        conversation_id: str,
        user: dict[str, Any] = Depends(get_current_user),
    ) -> Any:
        """
        Delete a conversation and all its messages.

        **Input:**
        - `conversation_id`: The unique conversation identifier

        **Side Effects:**
        - Permanently removes the conversation from the database
        - All associated messages are deleted
        - Emits a ConversationDeleted domain event

        **Authorization:** Users can only delete their own conversations.
        """
        command = DeleteConversationCommand(conversation_id=conversation_id, user_info=user)
        result = await self.mediator.execute_async(command)
        return self.process(result)

    @delete("/conversations")
    async def delete_conversations(
        self,
        body: DeleteConversationsRequest,
        user: dict[str, Any] = Depends(get_current_user),
    ) -> Any:
        """
        Delete multiple conversations by their IDs.

        **Input:**
        - `conversation_ids`: List of conversation IDs to delete

        **Side Effects:**
        - Permanently removes the specified conversations from the database
        - All associated messages are deleted for each conversation
        - Emits ConversationDeleted domain events

        **Output:**
        - `deleted_count`: Number of successfully deleted conversations
        - `failed_ids`: List of conversation IDs that failed to delete

        **Authorization:** Users can only delete their own conversations.
        """
        command = DeleteConversationsCommand(conversation_ids=body.conversation_ids, user_info=user)
        result = await self.mediator.execute_async(command)

        if result.is_success and result.data:
            return {
                "deleted_count": result.data.deleted_count,
                "failed_ids": result.data.failed_ids,
            }

        return self.process(result)

    @put("/conversations/{conversation_id}/rename")
    async def rename_conversation(
        self,
        conversation_id: str,
        body: RenameConversationRequest,
        user: dict[str, Any] = Depends(get_current_user),
        chat_service: ChatService = Depends(get_chat_service),
    ) -> Any:
        """
        Rename a conversation.

        **Input:**
        - `conversation_id`: The unique conversation identifier
        - `title`: New title for the conversation (1-200 characters)

        **Side Effects:**
        - Updates the conversation title in the database
        - Updates the conversation's `updated_at` timestamp

        **Output:**
        - `id`: The conversation ID
        - `title`: The new title
        - `renamed`: Boolean indicating success

        **Authorization:** Users can only rename their own conversations.
        """
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
        user: dict[str, Any] = Depends(get_current_user),
        chat_service: ChatService = Depends(get_chat_service),
    ) -> Any:
        """
        Clear all messages from a conversation while preserving the system prompt.

        **Input:**
        - `conversation_id`: The unique conversation identifier

        **Side Effects:**
        - Removes all user and assistant messages from the conversation
        - Preserves the system prompt for continued context
        - Useful for starting fresh within the same conversation

        **Output:**
        - `cleared`: Boolean indicating success
        - `message_count`: Number of remaining messages (usually 1 for system prompt)

        **Authorization:** Users can only clear their own conversations.
        """
        # For now, use the chat service directly
        # TODO: Create a ClearConversationCommand
        conversation = await chat_service._conversation_repo.get_async(conversation_id)
        if conversation is None:
            return self.not_found(Conversation, conversation_id)

        user_id = user.get("sub", "unknown")
        if conversation.state.user_id != user_id:
            return self.forbidden("Access denied")

        conversation.clear_messages(keep_system=True)
        await chat_service._conversation_repo.update_async(conversation)

        return {"cleared": True, "message_count": len(conversation)}

    @post("/conversations/{conversation_id}/navigate-back")
    async def navigate_backward(
        self,
        conversation_id: str,
        user: dict[str, Any] = Depends(get_current_user),
        chat_service: ChatService = Depends(get_chat_service),
    ) -> Any:
        """
        Navigate backward to the previous template item.

        **Input:**
        - `conversation_id`: The unique conversation identifier

        **Side Effects:**
        - Decrements the current template index
        - Resets the previous answer (last attempt score is retained)
        - Emits a backward navigation event to event store

        **Output:**
        - `success`: Boolean indicating if navigation was successful
        - `previous_index`: The index we navigated from
        - `current_index`: The new current index
        - `error`: Error message if navigation failed

        **Authorization:** Users can only navigate their own conversations.
        **Constraints:** Only works for templated conversations with allow_backward_navigation enabled.
        """
        conversation = await chat_service._conversation_repo.get_async(conversation_id)
        if conversation is None:
            return self.not_found(Conversation, conversation_id)

        user_id = user.get("sub", "unknown")
        if conversation.state.user_id != user_id:
            return self.forbidden("Access denied")

        # Check if this is a templated conversation
        template_config = conversation.get_template_config()
        if not template_config:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Backward navigation is only available for templated conversations",
            )

        # Check if backward navigation is allowed
        if not template_config.get("allow_backward_navigation", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Backward navigation is not enabled for this template",
            )

        # Get current index
        current_index = conversation.get_current_template_index()
        if current_index <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Already at the first item, cannot navigate backward",
            )

        # Navigate backward
        previous_index = current_index
        new_index = current_index - 1
        conversation.navigate_backward(from_index=previous_index, to_index=new_index)
        await chat_service._conversation_repo.update_async(conversation)

        logger.info(f"⬅️ Navigated backward in conversation {conversation_id}: {previous_index} -> {new_index}")

        return {
            "success": True,
            "previous_index": previous_index,
            "current_index": new_index,
            "message": "Successfully navigated to previous item",
        }

    @post("/conversations/{conversation_id}/pause")
    async def pause_conversation(
        self,
        conversation_id: str,
        user: dict[str, Any] = Depends(get_current_user),
        chat_service: ChatService = Depends(get_chat_service),
    ) -> Any:
        """
        Pause a templated conversation.

        **Input:**
        - `conversation_id`: The unique conversation identifier

        **Side Effects:**
        - Marks the conversation as paused
        - Stores the pause timestamp for deadline adjustment on resume
        - For timed templates, the countdown timer should stop

        **Output:**
        - `success`: Boolean indicating if pause was successful
        - `paused_at`: ISO timestamp when paused
        - `deadline`: Current deadline (if applicable)

        **Authorization:** Users can only pause their own conversations.
        **Constraints:** Only works for active templated conversations with allow_navigation enabled.
        """
        conversation = await chat_service._conversation_repo.get_async(conversation_id)
        if conversation is None:
            return self.not_found(Conversation, conversation_id)

        user_id = user.get("sub", "unknown")
        if conversation.state.user_id != user_id:
            return self.forbidden("Access denied")

        # Check if this is a templated conversation with navigation allowed
        template_config = conversation.get_template_config()
        if not template_config:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pause is only available for templated conversations",
            )

        if not template_config.get("allow_navigation", True):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pause is not enabled for this template (navigation is disabled)",
            )

        # Check if already paused
        if conversation.state.is_paused:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Conversation is already paused",
            )

        # Pause the conversation
        from datetime import datetime

        conversation.pause()
        await chat_service._conversation_repo.update_async(conversation)

        logger.info(f"⏸️ Paused conversation {conversation_id}")

        return {
            "success": True,
            "paused_at": conversation.state.paused_at.isoformat() if conversation.state.paused_at else datetime.now(UTC).isoformat(),
            "deadline": conversation.get_deadline().isoformat() if conversation.get_deadline() else None,
        }

    @post("/conversations/{conversation_id}/resume")
    async def resume_conversation(
        self,
        conversation_id: str,
        user: dict[str, Any] = Depends(get_current_user),
        chat_service: ChatService = Depends(get_chat_service),
    ) -> Any:
        """
        Resume a paused templated conversation.

        **Input:**
        - `conversation_id`: The unique conversation identifier

        **Side Effects:**
        - Marks the conversation as active
        - For timed templates, adjusts the deadline by the pause duration
        - Clears the paused_at timestamp

        **Output:**
        - `success`: Boolean indicating if resume was successful
        - `resumed_at`: ISO timestamp when resumed
        - `new_deadline`: Adjusted deadline (if applicable)
        - `pause_duration_ms`: How long the conversation was paused

        **Authorization:** Users can only resume their own conversations.
        """
        conversation = await chat_service._conversation_repo.get_async(conversation_id)
        if conversation is None:
            return self.not_found(Conversation, conversation_id)

        user_id = user.get("sub", "unknown")
        if conversation.state.user_id != user_id:
            return self.forbidden("Access denied")

        # Check if actually paused
        if not conversation.state.is_paused:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Conversation is not paused",
            )

        # Calculate pause duration before resuming
        from datetime import datetime

        pause_duration_ms = 0
        if conversation.state.paused_at:
            pause_duration = datetime.now(UTC) - conversation.state.paused_at
            pause_duration_ms = int(pause_duration.total_seconds() * 1000)

        # Resume the conversation (this will adjust the deadline if applicable)
        conversation.resume()
        await chat_service._conversation_repo.update_async(conversation)

        new_deadline = conversation.get_deadline()
        logger.info(f"▶️ Resumed conversation {conversation_id}, pause_duration={pause_duration_ms}ms, new_deadline={new_deadline}")

        return {
            "success": True,
            "resumed_at": datetime.now(UTC).isoformat(),
            "new_deadline": new_deadline.isoformat() if new_deadline else None,
            "pause_duration_ms": pause_duration_ms,
        }

    @get("/tools")
    async def list_tools(
        self,
        access_token: str = Depends(get_access_token),
        refresh: bool = Query(False, description="Force refresh from Tools Provider"),
        chat_service: ChatService = Depends(get_chat_service),
    ) -> list[ToolResponse]:
        """
        List tools available to the authenticated user.

        **Input:**
        - `refresh`: Force re-fetch from Tools Provider (bypasses cache)

        **Output:**
        Returns an array of tools with:
        - `name`: Tool name for calling
        - `description`: Human-readable description of what the tool does
        - `parameters`: JSON Schema of required/optional input parameters

        Tools are fetched from the Tools Provider service based on user access policies.
        Results are cached for performance; use `refresh=true` to get latest changes.
        """
        tools = await chat_service.get_tools(access_token, force_refresh=refresh)

        return [
            ToolResponse(
                name=t.name,
                description=t.description,
                parameters=[p.to_dict() for p in t.parameters],
            )
            for t in tools
        ]

    @get("/tools/{tool_name}/source")
    async def get_tool_source(
        self,
        tool_name: str,
        user: dict = Depends(require_admin),
        access_token: str = Depends(get_access_token),
    ) -> dict:
        """
        Get source information for a specific tool.

        **Input:**
        - `tool_name`: The name of the tool to look up

        **Output:**
        Returns upstream service details:
        - `source_id`: Unique identifier of the source
        - `source_name`: Human-readable name
        - `source_url`: Base URL of the upstream service
        - `openapi_url`: URL to the OpenAPI specification

        **RBAC Protected:** Only users with 'admin' role can view source details.
        """
        tool_provider = self.service_provider.get_required_service(ToolProviderClient)

        try:
            source_info = await tool_provider.get_tool_source_info(tool_name, access_token)
            return source_info
        except Exception as e:
            logger.error(f"Failed to get source info for tool '{tool_name}': {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get source information: {str(e)}",
            )

    @post("/new")
    async def start_new_conversation(
        self,
        body: CreateConversationRequest | None = None,
        user: dict[str, Any] = Depends(get_current_user),
        session_id: str = Depends(require_session),
    ) -> Any:
        """
        Start a new conversation with the default system prompt.

        **Input:**
        - `definition_id`: Optional agent definition ID for the conversation

        **Side Effects:**
        - Creates a new conversation in the database
        - Associates the conversation with the user's session
        - Previous active conversation is preserved but no longer active in session

        **Output:**
        - Full conversation DTO for optimistic UI rendering:
          - `id`: The conversation ID
          - `title`: Display title (or null for new conversations)
          - `definition_id`, `definition_name`, `definition_icon`: Agent info
          - `message_count`: Number of messages (0 for new)
          - `created_at`, `updated_at`: Timestamps

        Use this endpoint to start fresh without clearing an existing conversation.
        """
        from application.settings import app_settings

        definition_id = body.definition_id if body else None

        command = CreateConversationCommand(
            system_prompt=app_settings.system_prompt,
            definition_id=definition_id,
            user_info=user,
        )
        result = await self.mediator.execute_async(command)

        if result.is_success and result.data:
            # Update session with new conversation ID
            self.session_store.set_conversation_id(session_id, result.data.id)
            # Return full DTO for optimistic UI (avoids race condition with reconciliator)
            return result.data

        return self.process(result)


# =============================================================================
# WebSocket Endpoint (Outside of classy-fastapi controller)
# =============================================================================

# Note: FastAPI's WebSocket decorator doesn't work with classy-fastapi's
# decorator-based approach, so we define this as a standalone function
# that gets registered to the router in main.py


async def websocket_chat(
    websocket: WebSocket,
    definition_id: str | None = Query(None, description="Agent definition ID to start a template conversation"),
    conversation_id: str | None = Query(None, description="Existing conversation ID to continue"),
    user: dict = Depends(get_ws_current_user),
    access_token: str = Depends(get_ws_access_token),
    service_provider=Depends(get_ws_service_provider),
) -> None:
    """
    WebSocket endpoint for bidirectional chat communication.

    This endpoint provides a persistent connection for template-based conversations,
    allowing the server to push content and widgets while receiving user responses
    through the same connection.

    **Query Parameters:**
    - `definition_id`: Start a new conversation with this agent definition
    - `conversation_id`: Continue an existing conversation
    - `token`: JWT access token (alternative to session cookie)

    **Message Protocol (Client → Server):**
    ```json
    {"type": "start"}                           // Start template flow
    {"type": "message", "content": "..."}       // User message/widget response
    {"type": "ping"}                            // Keepalive
    ```

    **Message Protocol (Server → Client):**
    ```json
    {"type": "connected", "conversation_id": "..."}
    {"type": "content", "data": {"content": "..."}}
    {"type": "widget", "data": {...}}
    {"type": "progress", "data": {"current": 1, "total": 3}}
    {"type": "complete"}
    {"type": "error", "message": "..."}
    {"type": "pong"}
    ```
    """
    await websocket.accept()
    logger.info(f"WebSocket connected: user={user.get('sub', 'unknown')}, definition_id={definition_id}")

    user_id = user.get("sub", "unknown")
    conversation = None
    definition_model: str | None = None

    # Create a scope for the WebSocket connection to get scoped services
    scope = service_provider.create_scope()
    try:
        chat_service = scope.get_required_service(ChatService)

        # Fetch definition to get its model override (if any)
        if definition_id:
            try:
                from neuroglia.data.infrastructure.abstractions import Repository

                definition_repo = scope.get_required_service(Repository[AgentDefinition, str])
                definition = await definition_repo.get_async(definition_id)
                if definition and definition.state.model:
                    definition_model = definition.state.model
                    logger.debug(f"WebSocket using definition model override: {definition_model}")
            except Exception as e:
                logger.warning(f"Failed to fetch definition {definition_id}: {e}")

        # Get or create conversation
        if definition_id and not conversation_id:
            # New templated conversation
            conversation = await chat_service.get_or_create_conversation(
                user_id=user_id,
                definition_id=definition_id,
            )
        elif conversation_id:
            # Continue existing conversation
            conversation = await chat_service.get_or_create_conversation(
                user_id=user_id,
                conversation_id=conversation_id,
            )
        else:
            # New regular conversation
            conversation = await chat_service.get_or_create_conversation(user_id=user_id)

        # Send connected message with conversation ID
        await websocket.send_json(
            {
                "type": "connected",
                "conversation_id": conversation.id(),
                "definition_id": definition_id,
            }
        )

        # Main message loop
        while True:
            try:
                message = await websocket.receive_json()
                msg_type = message.get("type", "message")

                if msg_type == "ping":
                    await websocket.send_json({"type": "pong"})
                    continue

                elif msg_type == "start":
                    # Start template flow (proactive agent)
                    async for event in chat_service.run_websocket_template(
                        conversation=conversation,
                        user_message="",  # Empty for proactive start
                        access_token=access_token,
                        websocket=websocket,
                        model_id=definition_model,
                    ):
                        await websocket.send_json(event)

                elif msg_type == "message":
                    # User message or widget response
                    content = message.get("content", "")
                    if not content:
                        await websocket.send_json({"type": "error", "message": "Empty message"})
                        continue

                    async for event in chat_service.run_websocket_template(
                        conversation=conversation,
                        user_message=content,
                        access_token=access_token,
                        websocket=websocket,
                        model_id=definition_model,
                    ):
                        await websocket.send_json(event)

                else:
                    await websocket.send_json({"type": "error", "message": f"Unknown message type: {msg_type}"})

            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: user={user_id}")
    except Exception as e:
        logger.exception(f"WebSocket error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
            await websocket.close(code=1011, reason=str(e))
        except Exception:  # nosec B110
            pass  # WebSocket already closed, nothing we can do
    finally:
        # Dispose the scope to clean up scoped services
        if hasattr(scope, "dispose_async"):
            await scope.dispose_async()
        elif hasattr(scope, "dispose"):
            scope.dispose()
