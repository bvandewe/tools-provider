"""Chat controller for conversation management.

Note: Message streaming is handled via WebSocket (see websocket_controller.py).
This controller manages conversation CRUD operations and tools retrieval only.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from classy_fastapi.decorators import delete, get, post, put
from fastapi import Depends, HTTPException, Query, status
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
    require_admin,
    require_session,
)
from application.commands import CreateConversationCommand, DeleteConversationCommand, DeleteConversationsCommand
from application.queries import GetConversationQuery, GetConversationsQuery
from application.queries.definition.get_definitions_query import GetAllDefinitionsQuery
from application.services.chat_service import ChatService
from application.services.tool_provider_client import ToolProviderClient
from domain.entities.conversation import Conversation
from infrastructure.session_store import RedisSessionStore

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class RenameConversationRequest(BaseModel):
    """Request body for renaming a conversation."""

    title: str = Field(..., min_length=1, max_length=200, description="New conversation title")


class DeleteConversationsRequest(BaseModel):
    """Request body for deleting multiple conversations."""

    conversation_ids: list[str] = Field(..., min_length=1, description="List of conversation IDs to delete")


class CreateConversationRequest(BaseModel):
    """Request body for creating a new conversation."""

    definition_id: str | None = Field(None, description="Optional agent definition ID for the conversation")
    client_capabilities: list[str] | None = Field(
        None,
        description="List of client-supported protocol message types (e.g., 'data.widget.render', 'control.item.context')",
    )


class ConversationResponse(BaseModel):
    """Response containing conversation information."""

    id: str
    title: str | None
    created_at: str
    updated_at: str
    message_count: int


class ConversationCreatedResponse(BaseModel):
    """Response for newly created conversation with WebSocket URL."""

    model_config = {"populate_by_name": True}

    id: str = Field(..., alias="conversation_id")
    definition_id: str | None
    definition_name: str | None
    definition_icon: str | None
    title: str | None
    message_count: int
    created_at: str
    updated_at: str
    ws_url: str = Field(..., description="WebSocket URL to connect for this conversation")
    server_capabilities: list[str] = Field(
        default_factory=list,
        description="List of server-supported protocol message types",
    )


class ToolResponse(BaseModel):
    """Response containing tool information."""

    name: str
    description: str
    parameters: list[dict[str, Any]]


class ChatController(ControllerBase):
    """Controller for chat and conversation endpoints with CQRS pattern.

    Note: Message streaming is handled via WebSocket (see websocket_controller.py).
    This controller manages conversation CRUD operations only.
    """

    def __init__(self, service_provider: ServiceProviderBase, mapper: Mapper, mediator: Mediator):
        super().__init__(service_provider, mapper, mediator)
        self._session_store: RedisSessionStore | None = None

    @property
    def session_store(self) -> RedisSessionStore:
        """Lazy-load RedisSessionStore from DI container."""
        if self._session_store is None:
            self._session_store = self.service_provider.get_required_service(RedisSessionStore)
        return self._session_store

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
    ) -> ConversationCreatedResponse:
        """
        Start a new conversation and return WebSocket connection details.

        This is the first step in the two-phase conversation initiation:
        1. Client calls POST /chat/new with definition_id → receives conversation_id + ws_url
        2. Client opens WebSocket to ws_url → server initializes agent and starts flow

        **Input:**
        - `definition_id`: Optional agent definition ID for the conversation
        - `client_capabilities`: Optional list of client-supported protocol message types

        **Admission Control (applied before creation):**
        - Authorization: User must be authenticated
        - Rate limiting: Max conversations per user per time window
        - Quota: Max concurrent active conversations per user
        - Validation: definition_id must exist (if provided)

        **Output:**
        Returns conversation info with WebSocket URL:
        - `id`: The conversation ID (UUID)
        - `ws_url`: WebSocket URL to connect (includes conversation_id as query param)
        - `server_capabilities`: List of protocol message types the server supports
        - `definition_id`, `definition_name`, `definition_icon`: Agent info
        - `created_at`, `updated_at`: Timestamps

        The client should immediately connect to `ws_url` after receiving this response.
        """

        from application.settings import app_settings

        definition_id = body.definition_id if body else None
        client_capabilities = body.client_capabilities if body else None

        # =====================================================================
        # ADMISSION CONTROL (Placeholders - implement as needed)
        # =====================================================================

        # 1. Rate Limiting - prevent conversation spam
        # TODO: Implement rate limiting (e.g., max 10 conversations per minute per user)
        # rate_limiter = self.service_provider.get_service(RateLimiter)
        # if rate_limiter and not await rate_limiter.check("conversation_create", user.get("sub")):
        #     raise HTTPException(status_code=429, detail="Rate limit exceeded")

        # 2. Quota Check - limit concurrent active conversations
        # TODO: Implement quota check (e.g., max 5 active conversations per user)
        # quota_service = self.service_provider.get_service(QuotaService)
        # if quota_service and not await quota_service.check_conversation_quota(user.get("sub")):
        #     raise HTTPException(status_code=403, detail="Conversation quota exceeded")

        # 3. Definition Validation - ensure definition exists and is active
        if definition_id:
            definitions_result = await self.mediator.execute_async(GetAllDefinitionsQuery(include_system=True))
            if definitions_result.is_success and definitions_result.data:
                definition = next((d for d in definitions_result.data if d.id == definition_id), None)
                if not definition:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Agent definition '{definition_id}' not found",
                    )

        # 4. Feature Flags - check if conversation feature is enabled
        # TODO: Implement feature flag check
        # if not feature_flags.is_enabled("conversations", user):
        #     raise HTTPException(status_code=403, detail="Conversations are disabled")

        # =====================================================================
        # CREATE CONVERSATION
        # =====================================================================

        command = CreateConversationCommand(
            system_prompt=app_settings.system_prompt,
            definition_id=definition_id,
            user_info=user,
        )
        result = await self.mediator.execute_async(command)

        if not result.is_success or not result.data:
            return self.process(result)

        conv = result.data

        # Update session with new conversation ID
        self.session_store.set_conversation_id(session_id, conv.id)

        # =====================================================================
        # BUILD WEBSOCKET URL
        # =====================================================================

        # Build WebSocket URL with conversation_id
        # Use app_url from settings as base, convert http(s) to ws(s)
        base_url = app_settings.app_url.rstrip("/")
        if base_url.startswith("https://"):
            ws_base = base_url.replace("https://", "wss://", 1)
        else:
            ws_base = base_url.replace("http://", "ws://", 1)

        ws_url = f"{ws_base}/api/chat/ws?conversationId={conv.id}"

        # =====================================================================
        # SERVER CAPABILITIES
        # =====================================================================
        # CAPABILITY NEGOTIATION
        # =====================================================================

        # Import centralized server capabilities from protocol module
        from application.protocol.enums import SERVER_CAPABILITIES

        # Log client capabilities for debugging/analytics
        if client_capabilities:
            logger.debug(f"Client capabilities for conversation {conv.id}: {client_capabilities}")

        # =====================================================================
        # RETURN RESPONSE
        # =====================================================================

        # Fetch definition details for response
        definition_name = None
        definition_icon = None
        if definition_id:
            definitions_map: dict[str, dict[str, str]] = {}
            definitions_result = await self.mediator.execute_async(GetAllDefinitionsQuery(include_system=True))
            if definitions_result.is_success and definitions_result.data:
                definitions_map = {d.id: {"name": d.name, "icon": d.icon or "bi-robot"} for d in definitions_result.data}
            if definition_id in definitions_map:
                definition_name = definitions_map[definition_id]["name"]
                definition_icon = definitions_map[definition_id]["icon"]

        return ConversationCreatedResponse(
            conversation_id=conv.id,
            definition_id=conv.definition_id or None,
            definition_name=definition_name,
            definition_icon=definition_icon,
            title=conv.title,
            message_count=len([m for m in conv.messages if m.get("role") != "system"]) if conv.messages else 0,
            created_at=conv.created_at.isoformat() if conv.created_at else datetime.now(UTC).isoformat(),
            updated_at=conv.updated_at.isoformat() if conv.updated_at else datetime.now(UTC).isoformat(),
            ws_url=ws_url,
            server_capabilities=SERVER_CAPABILITIES,
        )

    @post("/conversations/{conversation_id}/connect")
    async def connect_to_conversation(
        self,
        conversation_id: str,
        user: dict[str, Any] = Depends(get_current_user),
        session_id: str = Depends(require_session),
    ) -> ConversationCreatedResponse:
        """
        Get WebSocket connection details for an existing conversation.

        This endpoint allows resuming an existing conversation by returning
        the WebSocket URL needed to establish a real-time connection.

        **Flow:**
        1. Client selects an existing conversation from sidebar
        2. Client calls POST /chat/conversations/{id}/connect
        3. Server validates ownership and returns ws_url
        4. Client opens WebSocket to ws_url → server restores context

        **Admission Control (applied before connection):**
        - Authorization: User must own the conversation
        - Rate limiting: Max reconnection attempts per user per time window
        - Validation: Conversation must exist and not be deleted

        **Output:**
        Returns conversation info with WebSocket URL:
        - `id`: The conversation ID (UUID)
        - `ws_url`: WebSocket URL to connect (includes conversation_id as query param)
        - `server_capabilities`: List of protocol message types the server supports
        - `definition_id`, `definition_name`, `definition_icon`: Agent info
        - `created_at`, `updated_at`: Timestamps

        The client should immediately connect to `ws_url` after receiving this response.
        """
        from application.settings import app_settings

        # =====================================================================
        # ADMISSION CONTROL
        # =====================================================================

        # 1. Fetch the conversation (validates existence and ownership)
        query = GetConversationQuery(conversation_id=conversation_id, user_info=user)
        result = await self.mediator.execute_async(query)

        if not result.is_success or not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation '{conversation_id}' not found",
            )

        conv = result.data

        # 2. Rate Limiting - prevent reconnection spam
        # TODO: Implement rate limiting (e.g., max 30 reconnects per minute per user)
        # rate_limiter = self.service_provider.get_service(RateLimiter)
        # if rate_limiter and not await rate_limiter.check("conversation_connect", user.get("sub")):
        #     raise HTTPException(status_code=429, detail="Rate limit exceeded")

        # Update session with conversation ID
        self.session_store.set_conversation_id(session_id, conv.id)

        # =====================================================================
        # BUILD WEBSOCKET URL
        # =====================================================================

        base_url = app_settings.app_url.rstrip("/")
        if base_url.startswith("https://"):
            ws_base = base_url.replace("https://", "wss://", 1)
        else:
            ws_base = base_url.replace("http://", "ws://", 1)

        ws_url = f"{ws_base}/api/chat/ws?conversationId={conv.id}"

        # =====================================================================
        # SERVER CAPABILITIES
        # =====================================================================

        from application.protocol.enums import SERVER_CAPABILITIES

        # =====================================================================
        # RETURN RESPONSE
        # =====================================================================

        # Fetch definition details for response
        definition_name = None
        definition_icon = None
        if conv.definition_id:
            definitions_result = await self.mediator.execute_async(GetAllDefinitionsQuery(include_system=True))
            if definitions_result.is_success and definitions_result.data:
                definitions_map = {d.id: {"name": d.name, "icon": d.icon or "bi-robot"} for d in definitions_result.data}
                if conv.definition_id in definitions_map:
                    definition_name = definitions_map[conv.definition_id]["name"]
                    definition_icon = definitions_map[conv.definition_id]["icon"]

        return ConversationCreatedResponse(
            conversation_id=conv.id,
            definition_id=conv.definition_id or None,
            definition_name=definition_name,
            definition_icon=definition_icon,
            title=conv.title,
            message_count=len([m for m in conv.messages if m.get("role") != "system"]) if conv.messages else 0,
            created_at=conv.created_at.isoformat() if conv.created_at else datetime.now(UTC).isoformat(),
            updated_at=conv.updated_at.isoformat() if conv.updated_at else datetime.now(UTC).isoformat(),
            ws_url=ws_url,
            server_capabilities=SERVER_CAPABILITIES,
        )
