"""
Agent Host WebSocket Protocol v1.0.0 - System Messages

System-level message payloads for connection lifecycle.
"""

from typing import Any

from pydantic import BaseModel, Field

from .enums import ConnectionCloseReason, ErrorCategory

# =============================================================================
# CONNECTION LIFECYCLE
# =============================================================================


class SystemConnectionEstablishedPayload(BaseModel):
    """Sent by server immediately after WebSocket connection.

    Includes server capabilities to inform client of supported message types.
    This enables capability negotiation between client and server.
    Also includes model configuration for UI to display model selector.
    """

    connection_id: str = Field(..., alias="connectionId")
    conversation_id: str = Field(..., alias="conversationId")
    user_id: str = Field(..., alias="userId")
    definition_id: str | None = Field(default=None, alias="definitionId")
    resuming: bool = False
    server_time: str = Field(..., alias="serverTime")
    server_capabilities: list[str] = Field(default_factory=list, alias="serverCapabilities", description="List of message types the server can send")
    # Model configuration for UI
    current_model: str | None = Field(default=None, alias="currentModel", description="Currently active model ID (from definition or default)")
    available_models: list[dict[str, Any]] = Field(default_factory=list, alias="availableModels", description="List of available models for selection")
    allow_model_selection: bool = Field(default=False, alias="allowModelSelection", description="Whether user can change the model")
    # Tools configuration for UI
    tool_count: int = Field(default=0, alias="toolCount", description="Number of tools available to the agent")

    model_config = {"populate_by_name": True}


class ClientState(BaseModel):
    """Client state for resume requests."""

    pending_widget_ids: list[str] = Field(default_factory=list, alias="pendingWidgetIds")
    input_content: str | None = Field(default=None, alias="inputContent")

    model_config = {"populate_by_name": True}


class SystemConnectionResumePayload(BaseModel):
    """Client request to resume after reconnection."""

    conversation_id: str = Field(..., alias="conversationId")
    last_message_id: str = Field(..., alias="lastMessageId")
    last_item_index: int = Field(..., alias="lastItemIndex")
    client_state: ClientState = Field(..., alias="clientState")

    model_config = {"populate_by_name": True}


class SystemConnectionResumedPayload(BaseModel):
    """Server confirmation of successful resume."""

    conversation_id: str = Field(..., alias="conversationId")
    resumed_from_message_id: str = Field(..., alias="resumedFromMessageId")
    current_item_index: int = Field(..., alias="currentItemIndex")
    missed_messages: int = Field(..., alias="missedMessages")
    state_valid: bool = Field(..., alias="stateValid")

    model_config = {"populate_by_name": True}


class SystemConnectionClosePayload(BaseModel):
    """Graceful connection closure."""

    reason: ConnectionCloseReason
    code: int


# =============================================================================
# KEEPALIVE
# =============================================================================


class SystemPingPongPayload(BaseModel):
    """Bidirectional keepalive mechanism."""

    timestamp: str


# =============================================================================
# ERROR HANDLING
# =============================================================================


class SystemErrorPayload(BaseModel):
    """Error notification from server."""

    category: ErrorCategory
    code: str
    message: str
    details: dict[str, Any] | None = None
    is_retryable: bool = Field(..., alias="isRetryable")
    retry_after_ms: int | None = Field(default=None, alias="retryAfterMs")

    model_config = {"populate_by_name": True}
