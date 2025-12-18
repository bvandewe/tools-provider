"""WebSocket Protocol v2 Implementation.

This package implements the WebSocket Protocol Specification v1.0.0 as defined in
/docs/specs/websocket-protocol-v1.md

The protocol is organized into:
- envelope.py: Base message envelope (CloudEvent-inspired)
- control_plane.py: Control plane messages (conversation/item/widget/canvas control)
- data_plane.py: Data plane messages (content streaming, widget rendering, responses)
- canvas.py: 2D Canvas system messages (connections, groups, layers, etc.)
- iframe.py: IFRAME widget protocol messages
- handlers.py: Message dispatching and handling

## Design Principles

1. **CloudEvent-Aligned**: Message envelope inspired by CloudEvents specification
2. **Three Planes**: System (lifecycle), Control (UI state), Data (content)
3. **Bidirectional**: Both client and server can send control signals
4. **Versioned**: Protocol version in every message for evolution
5. **Extensible**: New message types can be added without breaking changes

## Message Type Hierarchy

    {plane}.{category}.{action}

Examples:
- system.connection.established
- control.conversation.config
- control.canvas.viewport
- data.widget.render
- data.iframe.event
"""

from .control_plane import (
    # Conversation-level
    ConversationConfigPayload,
    ConversationDeadlinePayload,
    ConversationDisplayPayload,
    # Item-level
    ItemContextPayload,
    ItemScorePayload,
    ItemTimeoutPayload,
    WidgetConditionPayload,
    WidgetFocusPayload,
    WidgetLayoutPayload,
    # Widget-level
    WidgetStatePayload,
    WidgetValidationPayload,
)
from .data_plane import (
    ContentChunkPayload,
    ContentCompletePayload,
    MessageSendPayload,
    ResponseSubmitPayload,
    WidgetRenderPayload,
)
from .envelope import ProtocolMessage, create_message, parse_message

__all__ = [
    # Envelope
    "ProtocolMessage",
    "create_message",
    "parse_message",
    # Control plane - conversation
    "ConversationConfigPayload",
    "ConversationDisplayPayload",
    "ConversationDeadlinePayload",
    # Control plane - item
    "ItemContextPayload",
    "ItemScorePayload",
    "ItemTimeoutPayload",
    # Control plane - widget
    "WidgetStatePayload",
    "WidgetFocusPayload",
    "WidgetValidationPayload",
    "WidgetLayoutPayload",
    "WidgetConditionPayload",
    # Data plane
    "ContentChunkPayload",
    "ContentCompletePayload",
    "WidgetRenderPayload",
    "ResponseSubmitPayload",
    "MessageSendPayload",
]
