"""WebSocket Protocol Specification for Agent Host Chat.

This module defines the authoritative contract between backend and frontend
for all WebSocket communication. Both sides MUST implement this specification.

## Design Principles

1. **Server-Driven UI**: The backend owns all flow logic. Frontend is a dumb renderer.
2. **Declarative Events**: Server sends what to show, not how to show it.
3. **Stateless Frontend**: Frontend maintains only UI state, no business logic.
4. **Extensible Widgets**: New widget types can be added without protocol changes.

## Connection Lifecycle

1. Client connects to `/api/chat/ws?definition_id=X` or `?conversation_id=Y`
2. Server sends `connected` event with conversation metadata
3. Server may immediately send content/widgets (proactive) or wait for user input
4. Client sends `message` events with user input
5. Server responds with content/widgets/progress events
6. Either side can close the connection

## Message Flow

```
Client                                  Server
  |                                       |
  |--- connect(definition_id) ----------->|
  |                                       |
  |<-- connected(conversation_id) --------|
  |<-- config(template settings) ---------|  (if templated)
  |<-- content("Hello!") -----------------|  (if proactive)
  |<-- widget(multiple_choice) -----------|  (if proactive)
  |<-- input_state(enabled=true) ---------|
  |                                       |
  |--- message("Option A") -------------->|
  |                                       |
  |<-- message_received(id) --------------|
  |<-- thinking() ------------------------|
  |<-- content("Good choice!") -----------|
  |<-- progress(1/3) ---------------------|
  |<-- widget(next question) -------------|
  |<-- input_state(enabled=true) ---------|
  |                                       |
  ...
  |                                       |
  |<-- complete(score, summary) ----------|
  |<-- input_state(enabled=false) --------|
```
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Literal

# =============================================================================
# Event Types
# =============================================================================


class ServerEventType(str, Enum):
    """Events sent from server to client."""

    # Connection lifecycle
    CONNECTED = "connected"  # Connection established, conversation ready
    ERROR = "error"  # Error occurred
    PONG = "pong"  # Response to ping

    # Conversation configuration (sent once at start)
    CONFIG = "config"  # Template/conversation configuration

    # Content events (can be sent multiple times)
    CONTENT = "content"  # Text content to display (streaming or complete)
    WIDGET = "widget"  # Interactive widget to render
    THINKING = "thinking"  # Agent is processing (show indicator)

    # Progress events
    PROGRESS = "progress"  # Template progress update
    MESSAGE_RECEIVED = "message_received"  # Acknowledge user message

    # Tool events
    TOOL_CALL = "tool_call"  # Agent is calling a tool
    TOOL_RESULT = "tool_result"  # Tool execution completed

    # State control events
    INPUT_STATE = "input_state"  # Enable/disable chat input
    COMPLETE = "complete"  # Conversation/template completed


class ClientEventType(str, Enum):
    """Events sent from client to server."""

    MESSAGE = "message"  # User message or widget response
    PING = "ping"  # Keepalive ping
    CANCEL = "cancel"  # Cancel current operation


# =============================================================================
# Widget Types
# =============================================================================


class WidgetType(str, Enum):
    """Supported widget types for interactive content."""

    MESSAGE = "message"  # Plain text message (no interaction)
    MULTIPLE_CHOICE = "multiple_choice"  # Single/multi select options
    FREE_TEXT = "free_text"  # Text input field
    CODE_EDITOR = "code_editor"  # Code editor with syntax highlighting
    SLIDER = "slider"  # Numeric slider
    FILE_UPLOAD = "file_upload"  # File upload widget
    RATING = "rating"  # Star/numeric rating


# =============================================================================
# Server -> Client Events
# =============================================================================


@dataclass
class ConnectedEvent:
    """Sent when WebSocket connection is established.

    This is always the first event after connection.
    """

    type: Literal["connected"] = "connected"
    conversation_id: str = ""
    definition_id: str | None = None
    is_new: bool = True  # True if new conversation, False if resuming
    user_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "conversation_id": self.conversation_id,
            "definition_id": self.definition_id,
            "is_new": self.is_new,
            "user_id": self.user_id,
        }


@dataclass
class ConfigEvent:
    """Conversation/template configuration.

    Sent once after connected event if conversation has special configuration.
    Frontend uses this to set up UI (progress bar, navigation, etc.).
    """

    type: Literal["config"] = "config"

    # Template info (if templated conversation)
    title: str | None = None
    total_items: int | None = None

    # Navigation controls
    allow_navigation: bool = False  # Can user jump between items?
    allow_backward: bool = False  # Can user go back?

    # Display options
    show_progress: bool = True  # Show progress indicator?
    show_score: bool = False  # Show score during conversation?
    show_final_report: bool = False  # Show final score report?

    # Timing
    deadline: datetime | None = None  # Absolute deadline if timed
    time_limit_seconds: int | None = None  # Total time limit

    # Behavior
    continue_after_complete: bool = False  # Enable chat after template completes?

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "title": self.title,
            "total_items": self.total_items,
            "allow_navigation": self.allow_navigation,
            "allow_backward": self.allow_backward,
            "show_progress": self.show_progress,
            "show_score": self.show_score,
            "show_final_report": self.show_final_report,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "time_limit_seconds": self.time_limit_seconds,
            "continue_after_complete": self.continue_after_complete,
        }


@dataclass
class ContentEvent:
    """Text content to display.

    Can be sent as a single complete message or as streaming chunks.
    """

    type: Literal["content"] = "content"
    content: str = ""
    message_id: str | None = None  # Set on final/complete content
    is_streaming: bool = False  # True if more chunks coming
    role: Literal["assistant", "system"] = "assistant"

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "content": self.content,
            "message_id": self.message_id,
            "is_streaming": self.is_streaming,
            "role": self.role,
        }


@dataclass
class WidgetEvent:
    """Interactive widget to render.

    The frontend should render the appropriate widget based on widget_type
    and wait for user interaction.
    """

    type: Literal["widget"] = "widget"
    widget_id: str = ""  # Unique ID for this widget instance
    widget_type: str = "message"  # WidgetType value
    item_id: str | None = None  # Parent item ID (for templates)

    # Content
    stem: str = ""  # Question/prompt text
    options: list[str] | None = None  # For multiple_choice
    initial_value: Any = None  # Pre-filled value

    # Configuration
    config: dict[str, Any] = field(default_factory=dict)  # Widget-specific config
    required: bool = True  # Must be answered?
    skippable: bool = False  # Can be skipped?

    # Display
    show_response: bool = True  # Show user's response as chat bubble?

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "widget_id": self.widget_id,
            "widget_type": self.widget_type,
            "item_id": self.item_id,
            "stem": self.stem,
            "options": self.options,
            "initial_value": self.initial_value,
            "config": self.config,
            "required": self.required,
            "skippable": self.skippable,
            "show_response": self.show_response,
        }


@dataclass
class ThinkingEvent:
    """Agent is processing.

    Frontend should show a thinking indicator.
    """

    type: Literal["thinking"] = "thinking"
    message: str | None = None  # Optional status message

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "message": self.message,
        }


@dataclass
class ProgressEvent:
    """Template progress update.

    Sent after each item is completed in a templated conversation.
    """

    type: Literal["progress"] = "progress"
    current_item: int = 0  # 0-indexed current position
    total_items: int = 0
    item_id: str | None = None  # Current item ID
    item_title: str | None = None  # Current item title (if displayed)

    # Scoring (if enabled)
    current_score: float | None = None
    max_score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "current_item": self.current_item,
            "total_items": self.total_items,
            "item_id": self.item_id,
            "item_title": self.item_title,
            "current_score": self.current_score,
            "max_score": self.max_score,
        }


@dataclass
class MessageReceivedEvent:
    """Acknowledge receipt of user message.

    Sent immediately after receiving a user message.
    """

    type: Literal["message_received"] = "message_received"
    message_id: str = ""
    content: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "message_id": self.message_id,
            "content": self.content,
        }


@dataclass
class ToolCallEvent:
    """Agent is calling a server-side tool.

    Frontend may show a tool execution indicator.
    """

    type: Literal["tool_call"] = "tool_call"
    tool_name: str = ""
    tool_id: str = ""  # Unique ID for this call

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "tool_name": self.tool_name,
            "tool_id": self.tool_id,
        }


@dataclass
class ToolResultEvent:
    """Tool execution completed.

    Frontend may hide the tool execution indicator.
    """

    type: Literal["tool_result"] = "tool_result"
    tool_name: str = ""
    tool_id: str = ""
    success: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "tool_name": self.tool_name,
            "tool_id": self.tool_id,
            "success": self.success,
        }


@dataclass
class InputStateEvent:
    """Control chat input state.

    Frontend should enable/disable the chat input based on this.
    """

    type: Literal["input_state"] = "input_state"
    enabled: bool = True
    placeholder: str | None = None  # Optional placeholder text
    reason: str | None = None  # Why input is disabled (for UI)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "enabled": self.enabled,
            "placeholder": self.placeholder,
            "reason": self.reason,
        }


@dataclass
class CompleteEvent:
    """Conversation or template completed.

    For templated conversations, includes final score/summary.
    """

    type: Literal["complete"] = "complete"
    reason: Literal["finished", "timeout", "cancelled", "error"] = "finished"

    # Scoring (if applicable)
    total_score: float | None = None
    max_score: float | None = None
    passed: bool | None = None  # Met passing threshold?

    # Summary
    summary: str | None = None  # Completion message
    feedback: str | None = None  # Overall feedback

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "reason": self.reason,
            "total_score": self.total_score,
            "max_score": self.max_score,
            "passed": self.passed,
            "summary": self.summary,
            "feedback": self.feedback,
        }


@dataclass
class ErrorEvent:
    """Error occurred.

    Frontend should display error to user and optionally allow retry.
    """

    type: Literal["error"] = "error"
    message: str = ""
    code: str | None = None  # Error code for programmatic handling
    retryable: bool = False  # Can user retry the operation?

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "message": self.message,
            "code": self.code,
            "retryable": self.retryable,
        }


# =============================================================================
# Client -> Server Events
# =============================================================================


@dataclass
class MessageEvent:
    """User message or widget response.

    The content can be:
    - Plain text (user typed a message)
    - Widget response value (user interacted with widget)
    """

    type: Literal["message"] = "message"
    content: str = ""
    widget_id: str | None = None  # If responding to a widget

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MessageEvent":
        return cls(
            type=data.get("type", "message"),
            content=data.get("content", ""),
            widget_id=data.get("widget_id"),
        )


@dataclass
class PingEvent:
    """Keepalive ping."""

    type: Literal["ping"] = "ping"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PingEvent":
        return cls()


@dataclass
class CancelEvent:
    """Cancel current operation."""

    type: Literal["cancel"] = "cancel"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CancelEvent":
        return cls()


# =============================================================================
# Type Aliases
# =============================================================================

ServerEvent = (
    ConnectedEvent | ConfigEvent | ContentEvent | WidgetEvent | ThinkingEvent | ProgressEvent | MessageReceivedEvent | ToolCallEvent | ToolResultEvent | InputStateEvent | CompleteEvent | ErrorEvent
)

ClientEvent = MessageEvent | PingEvent | CancelEvent


def parse_client_event(data: dict[str, Any]) -> ClientEvent:
    """Parse a client event from JSON data.

    Args:
        data: Parsed JSON data from WebSocket message

    Returns:
        Typed client event

    Raises:
        ValueError: If event type is unknown
    """
    event_type = data.get("type", "message")

    if event_type == "message":
        return MessageEvent.from_dict(data)
    elif event_type == "ping":
        return PingEvent.from_dict(data)
    elif event_type == "cancel":
        return CancelEvent.from_dict(data)
    else:
        raise ValueError(f"Unknown client event type: {event_type}")
