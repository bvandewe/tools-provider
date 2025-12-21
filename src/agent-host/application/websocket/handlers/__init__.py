"""WebSocket Message Handlers Package.

Contains base handler class and concrete handler implementations for:
- System messages (ping, pong, connection resume)
- Control plane (conversation, widget, flow, navigation)
- Data plane (audit, messages, responses)
- Canvas (viewport, selection, connections, groups, layers, presentation)
"""

from application.websocket.handlers.base import BaseHandler, NoOpHandler
from application.websocket.handlers.canvas_handlers import (
    BookmarkNavigateHandler,
    ConnectionCreatedHandler,
    GroupToggledHandler,
    LayerToggledHandler,
    PresentationNavigatedHandler,
    SelectionChangedHandler,
    ViewportChangedHandler,
)
from application.websocket.handlers.control_handlers import (
    ConversationConfigHandler,
    FlowCancelHandler,
    FlowPauseHandler,
    FlowStartHandler,
    NavigationNextHandler,
    NavigationPreviousHandler,
    NavigationSkipHandler,
    WidgetDismissedHandler,
    WidgetMovedHandler,
    WidgetResizedHandler,
    WidgetStateHandler,
    WidgetValidationHandler,
)
from application.websocket.handlers.data_handlers import (
    AuditEventsHandler,
    ContentChunkAckHandler,
    MessageSendHandler,
    ResponseSubmitHandler,
    ToolResultHandler,
)
from application.websocket.handlers.system_handlers import (
    ConnectionResumeHandler,
    PingHandler,
    PongHandler,
)

__all__ = [
    # Base
    "BaseHandler",
    "NoOpHandler",
    # System
    "ConnectionResumeHandler",
    "PingHandler",
    "PongHandler",
    # Control - Conversation
    "ConversationConfigHandler",
    # Control - Widget
    "WidgetStateHandler",
    "WidgetValidationHandler",
    "WidgetMovedHandler",
    "WidgetResizedHandler",
    "WidgetDismissedHandler",
    # Control - Flow
    "FlowStartHandler",
    "FlowPauseHandler",
    "FlowCancelHandler",
    # Control - Navigation
    "NavigationNextHandler",
    "NavigationPreviousHandler",
    "NavigationSkipHandler",
    # Data
    "AuditEventsHandler",
    "MessageSendHandler",
    "ResponseSubmitHandler",
    "ContentChunkAckHandler",
    "ToolResultHandler",
    # Canvas
    "ViewportChangedHandler",
    "SelectionChangedHandler",
    "ConnectionCreatedHandler",
    "GroupToggledHandler",
    "LayerToggledHandler",
    "PresentationNavigatedHandler",
    "BookmarkNavigateHandler",
]
