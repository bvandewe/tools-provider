"""
Agent Host WebSocket Protocol v1.0.0 - Data Plane Messages

Data plane payloads for content, tools, messages, and responses.
"""

from typing import Any

from pydantic import BaseModel, Field

from .enums import ContentRole

# =============================================================================
# CONTENT STREAMING
# =============================================================================


class ContentChunkPayload(BaseModel):
    """Streaming text content from LLM."""

    content: str
    message_id: str = Field(..., alias="messageId")
    final: bool = False

    model_config = {"populate_by_name": True}


class ContentCompletePayload(BaseModel):
    """Marks a content message as complete."""

    message_id: str = Field(..., alias="messageId")
    role: ContentRole
    full_content: str = Field(..., alias="fullContent")

    model_config = {"populate_by_name": True}


# =============================================================================
# TOOL EXECUTION
# =============================================================================


class ToolCallPayload(BaseModel):
    """Notification that a tool is being called."""

    call_id: str = Field(..., alias="callId")
    tool_name: str = Field(..., alias="toolName")
    arguments: dict[str, Any]

    model_config = {"populate_by_name": True}


class ToolResultPayload(BaseModel):
    """Result of tool execution."""

    call_id: str = Field(..., alias="callId")
    tool_name: str = Field(..., alias="toolName")
    success: bool
    result: Any
    execution_time_ms: int | None = Field(default=None, alias="executionTimeMs")

    model_config = {"populate_by_name": True}


# =============================================================================
# USER MESSAGES
# =============================================================================


class MessageSendPayload(BaseModel):
    """User sends a free-text message."""

    content: str
    attachments: list[Any] | None = None


class MessageAckPayload(BaseModel):
    """Server acknowledges receipt of user message."""

    message_id: str = Field(..., alias="messageId")

    model_config = {"populate_by_name": True}


# =============================================================================
# WIDGET RESPONSES
# =============================================================================


class ResponseMetadata(BaseModel):
    """Optional metadata for widget responses."""

    selection_index: int | None = Field(default=None, alias="selectionIndex")
    time_spent_ms: int | None = Field(default=None, alias="timeSpentMs")
    change_count: int | None = Field(default=None, alias="changeCount")

    model_config = {"populate_by_name": True, "extra": "allow"}


class BatchResponseItem(BaseModel):
    """A single widget response in a batch."""

    widget_type: str = Field(..., alias="widgetType")
    value: Any

    model_config = {"populate_by_name": True}


class ResponseSubmitPayload(BaseModel):
    """Generic widget response submission.

    Supports both single widget responses and batch submissions (confirmation mode).
    When `responses` is provided, it contains all widget responses for the item.
    """

    item_id: str = Field(..., alias="itemId")
    widget_id: str = Field(..., alias="widgetId")
    widget_type: str = Field(..., alias="widgetType")
    value: Any
    metadata: ResponseMetadata | None = None
    # Batch responses for confirmation mode: map of widgetId -> { widgetType, value }
    responses: dict[str, BatchResponseItem] | None = None

    model_config = {"populate_by_name": True}
