"""
Agent Host WebSocket Protocol v1.0.0 - Enums and Constants

All enumeration types and constant values for the protocol.
"""

from enum import IntEnum
from typing import Literal

# =============================================================================
# CORE ENUMS
# =============================================================================

MessageSource = Literal["client", "server"]
ProtocolVersion = Literal["1.0"]
MessagePlane = Literal["system", "control", "data"]


# =============================================================================
# CONTROL PLANE ENUMS
# =============================================================================

DisplayMode = Literal["append", "replace"]
ItemTimerMode = Literal["parallel", "focused", "aggregate"]
WidgetCompletionBehavior = Literal["readonly", "text", "hidden"]
WidgetState = Literal["active", "readonly", "disabled", "hidden"]
ConditionOperator = Literal["equals", "not_equals", "contains", "in", "greater_than", "less_than", "regex"]
ConditionEffect = Literal["show", "hide", "enable", "disable", "focus"]
DismissAction = Literal["hide", "minimize", "collapse"]
ItemTimeoutAction = Literal["auto_advance", "lock", "warn"]
ConnectionCloseReason = Literal["user_logout", "session_expired", "server_shutdown", "conversation_complete", "idle_timeout"]
ErrorCategory = Literal["transport", "authentication", "validation", "business", "server", "rate_limit"]
ContentRole = Literal["assistant", "user", "system"]


# =============================================================================
# WIDGET ENUMS
# =============================================================================

WidgetType = Literal[
    "message",
    "multiple_choice",
    "free_text",
    "code_editor",
    "slider",
    "hotspot",
    "drag_drop",
    "dropdown",
    "iframe",
    "sticky_note",
    "image",
    "video",
    "graph_topology",
    "matrix_choice",
    "document_viewer",
    "file_upload",
    "rating",
    "date_picker",
    "drawing",
    "button",  # Confirmation/action button
]

AnchorPosition = Literal[
    "top-left",
    "top-center",
    "top-right",
    "center-left",
    "center",
    "center-right",
    "bottom-left",
    "bottom-center",
    "bottom-right",
]

DragDropVariant = Literal["category", "sequence", "graphical"]
RatingStyle = Literal["stars", "numeric", "emoji", "thumbs"]
DatePickerMode = Literal["date", "time", "datetime", "daterange"]
ObjectFit = Literal["contain", "cover", "fill", "none"]
MatrixLayout = Literal["rows", "columns", "likert"]
SelectionMode = Literal["single", "multiple"]
ContentType = Literal["markdown", "html", "text"]
HotspotShape = Literal["circle", "rect", "polygon"]
DrawingFormat = Literal["svg", "png"]


# =============================================================================
# CANVAS ENUMS
# =============================================================================

CanvasMode = Literal["select", "pan", "connect", "annotate", "draw", "presentation"]
ConnectionTypeEnum = Literal["arrow", "line", "curve", "elbow", "double-arrow"]
ConnectionAnchor = Literal["auto", "top", "right", "bottom", "left", "top-left", "top-right", "bottom-left", "bottom-right"]
BackgroundPattern = Literal["none", "dots", "lines", "crosshatch", "custom"]
AlignmentOption = Literal["left", "center-horizontal", "right", "top", "center-vertical", "bottom"]
SelectionMethod = Literal["click", "ctrl_click", "shift_click", "lasso", "marquee"]
AnnotationType = Literal["sticky_note", "callout", "highlight", "drawing", "shape", "text"]
ViewportAction = Literal["focus", "pan", "panBy", "zoom", "zoomToFit", "zoomToSelection", "reset"]
ViewportTargetType = Literal["widget", "group", "widgets", "point", "region"]
PresentationStepAction = Literal["auto_advance", "await_click", "await_interaction", "await_complete", "await_all_complete", "manual"]
MinimapPosition = Literal["top-left", "top-right", "bottom-left", "bottom-right"]
PanButton = Literal["left", "middle", "right"]
ConnectionLabelPosition = Literal["start", "middle", "end"]
MouseButton = Literal["left", "right", "middle"]
ClickType = Literal["single", "double", "triple"]


# =============================================================================
# AUDIT ENUMS
# =============================================================================

AuditEventType = Literal[
    "focus_change",
    "keystroke",
    "mouse_click",
    "mouse_move",
    "paste",
    "copy",
    "scroll",
    "visibility_change",
    "window_blur",
    "window_focus",
]

AuditElementType = Literal["widget", "chat", "canvas", "background", "toolbar", "navigation"]
AuditStatus = Literal["stored", "rejected"]


# =============================================================================
# IFRAME ENUMS
# =============================================================================

IframeCommunicationMode = Literal["relay", "independent"]
IframeLoading = Literal["eager", "lazy"]
IframeErrorType = Literal[
    "load_failed",
    "timeout",
    "sandbox_blocked",
    "origin_mismatch",
    "communication_error",
    "content_error",
]


# =============================================================================
# WEBSOCKET CLOSE CODES
# =============================================================================


class StandardCloseCode(IntEnum):
    """Standard WebSocket close codes (RFC 6455)."""

    NORMAL_CLOSURE = 1000
    GOING_AWAY = 1001
    PROTOCOL_ERROR = 1002
    UNSUPPORTED_DATA = 1003
    NO_STATUS_RECEIVED = 1005
    ABNORMAL_CLOSURE = 1006
    INVALID_PAYLOAD_DATA = 1007
    POLICY_VIOLATION = 1008
    MESSAGE_TOO_BIG = 1009
    MANDATORY_EXTENSION = 1010
    INTERNAL_ERROR = 1011
    SERVICE_RESTART = 1012
    TRY_AGAIN_LATER = 1013
    BAD_GATEWAY = 1014
    TLS_HANDSHAKE = 1015


class AppCloseCode(IntEnum):
    """Application-specific close codes (4000-4999)."""

    AUTHENTICATION_REQUIRED = 4000
    AUTHENTICATION_EXPIRED = 4001
    AUTHENTICATION_INVALID = 4002
    CONVERSATION_NOT_FOUND = 4003
    CONVERSATION_ENDED = 4004
    DEFINITION_NOT_FOUND = 4005
    RATE_LIMITED = 4006
    DUPLICATE_CONNECTION = 4007
    IDLE_TIMEOUT = 4008
    MAINTENANCE_MODE = 4009
    VERSION_MISMATCH = 4010
    PAYLOAD_TOO_LARGE = 4011
    INVALID_MESSAGE = 4012
    RESOURCE_EXHAUSTED = 4013
    UPSTREAM_ERROR = 4014
    CONVERSATION_PAUSED = 4015


# =============================================================================
# MESSAGE TYPE CONSTANTS
# =============================================================================


class MessageTypes:
    """All message type constants for the protocol."""

    # System
    SYSTEM_CONNECTION_ESTABLISHED = "system.connection.established"
    SYSTEM_CONNECTION_RESUME = "system.connection.resume"
    SYSTEM_CONNECTION_RESUMED = "system.connection.resumed"
    SYSTEM_CONNECTION_CLOSE = "system.connection.close"
    SYSTEM_PING = "system.ping"
    SYSTEM_PONG = "system.pong"
    SYSTEM_ERROR = "system.error"

    # Control - Conversation
    CONTROL_CONVERSATION_CONFIG = "control.conversation.config"
    CONTROL_CONVERSATION_DISPLAY = "control.conversation.display"
    CONTROL_CONVERSATION_DEADLINE = "control.conversation.deadline"
    CONTROL_CONVERSATION_PAUSE = "control.conversation.pause"
    CONTROL_CONVERSATION_RESUME = "control.conversation.resume"
    CONTROL_CONVERSATION_COMPLETE = "control.conversation.complete"

    # Control - Item
    CONTROL_ITEM_CONTEXT = "control.item.context"
    CONTROL_ITEM_SCORE = "control.item.score"
    CONTROL_ITEM_TIMEOUT = "control.item.timeout"
    CONTROL_ITEM_EXPIRED = "control.item.expired"

    # Control - Widget
    CONTROL_WIDGET_STATE = "control.widget.state"
    CONTROL_WIDGET_FOCUS = "control.widget.focus"
    CONTROL_WIDGET_VALIDATION = "control.widget.validation"
    CONTROL_WIDGET_LAYOUT = "control.widget.layout"
    CONTROL_WIDGET_MOVED = "control.widget.moved"
    CONTROL_WIDGET_RESIZED = "control.widget.resized"
    CONTROL_WIDGET_DISMISSED = "control.widget.dismissed"
    CONTROL_WIDGET_CONDITION = "control.widget.condition"

    # Control - Flow
    CONTROL_FLOW_START = "control.flow.start"
    CONTROL_FLOW_PAUSE = "control.flow.pause"
    CONTROL_FLOW_RESUME = "control.flow.resume"
    CONTROL_FLOW_CANCEL = "control.flow.cancel"

    # Control - Navigation
    CONTROL_NAVIGATION_NEXT = "control.navigation.next"
    CONTROL_NAVIGATION_PREVIOUS = "control.navigation.previous"
    CONTROL_NAVIGATION_SKIP = "control.navigation.skip"

    # Control - Audit
    CONTROL_AUDIT_CONFIG = "control.audit.config"
    CONTROL_AUDIT_FLUSH = "control.audit.flush"

    # Control - Canvas
    CONTROL_CANVAS_CONFIG = "control.canvas.config"
    CONTROL_CANVAS_VIEWPORT = "control.canvas.viewport"
    CONTROL_CANVAS_ZOOM = "control.canvas.zoom"
    CONTROL_CANVAS_MODE = "control.canvas.mode"
    CONTROL_CANVAS_CONNECTION_CREATE = "control.canvas.connection.create"
    CONTROL_CANVAS_CONNECTION_UPDATE = "control.canvas.connection.update"
    CONTROL_CANVAS_CONNECTION_DELETE = "control.canvas.connection.delete"
    CONTROL_CANVAS_CONNECTION_CREATED = "control.canvas.connection.created"
    CONTROL_CANVAS_GROUP_CREATE = "control.canvas.group.create"
    CONTROL_CANVAS_GROUP_UPDATE = "control.canvas.group.update"
    CONTROL_CANVAS_GROUP_ADD = "control.canvas.group.add"
    CONTROL_CANVAS_GROUP_REMOVE = "control.canvas.group.remove"
    CONTROL_CANVAS_GROUP_DELETE = "control.canvas.group.delete"
    CONTROL_CANVAS_GROUP_TOGGLED = "control.canvas.group.toggled"
    CONTROL_CANVAS_LAYER_CREATE = "control.canvas.layer.create"
    CONTROL_CANVAS_LAYER_UPDATE = "control.canvas.layer.update"
    CONTROL_CANVAS_LAYER_ASSIGN = "control.canvas.layer.assign"
    CONTROL_CANVAS_LAYER_TOGGLED = "control.canvas.layer.toggled"
    CONTROL_CANVAS_SELECTION_SET = "control.canvas.selection.set"
    CONTROL_CANVAS_SELECTION_CHANGED = "control.canvas.selection.changed"
    CONTROL_CANVAS_PRESENTATION_START = "control.canvas.presentation.start"
    CONTROL_CANVAS_PRESENTATION_STEP = "control.canvas.presentation.step"
    CONTROL_CANVAS_PRESENTATION_END = "control.canvas.presentation.end"
    CONTROL_CANVAS_PRESENTATION_NAVIGATED = "control.canvas.presentation.navigated"
    CONTROL_CANVAS_BOOKMARK_CREATE = "control.canvas.bookmark.create"
    CONTROL_CANVAS_BOOKMARK_UPDATE = "control.canvas.bookmark.update"
    CONTROL_CANVAS_BOOKMARK_DELETE = "control.canvas.bookmark.delete"
    CONTROL_CANVAS_BOOKMARK_NAVIGATE = "control.canvas.bookmark.navigate"
    CONTROL_CANVAS_BOOKMARK_CREATED = "control.canvas.bookmark.created"

    # Control - IFRAME
    CONTROL_IFRAME_RESIZE = "control.iframe.resize"
    CONTROL_IFRAME_NAVIGATE = "control.iframe.navigate"

    # Data - Content
    DATA_CONTENT_CHUNK = "data.content.chunk"
    DATA_CONTENT_COMPLETE = "data.content.complete"

    # Data - Widget
    DATA_WIDGET_RENDER = "data.widget.render"

    # Data - Tools
    DATA_TOOL_CALL = "data.tool.call"
    DATA_TOOL_RESULT = "data.tool.result"

    # Data - Messages
    DATA_MESSAGE_SEND = "data.message.send"
    DATA_MESSAGE_ACK = "data.message.ack"

    # Data - Responses
    DATA_RESPONSE_SUBMIT = "data.response.submit"

    # Data - Annotations
    DATA_ANNOTATION_CREATE = "data.annotation.create"
    DATA_ANNOTATION_CREATED = "data.annotation.created"

    # Data - Audit
    DATA_AUDIT_EVENTS = "data.audit.events"
    DATA_AUDIT_ACK = "data.audit.ack"
    DATA_AUDIT_FLUSHED = "data.audit.flushed"

    # Data - IFRAME
    DATA_IFRAME_EVENT = "data.iframe.event"
    DATA_IFRAME_COMMAND = "data.iframe.command"
    DATA_IFRAME_STATE = "data.iframe.state"
    DATA_IFRAME_ERROR = "data.iframe.error"


# =============================================================================
# SERVER CAPABILITIES
# =============================================================================

# List of all message types the server can send to clients.
# Used in system.connection.established and /chat/new response for capability negotiation.
SERVER_CAPABILITIES: list[str] = [
    # System messages (server → client)
    MessageTypes.SYSTEM_CONNECTION_ESTABLISHED,
    MessageTypes.SYSTEM_CONNECTION_RESUMED,
    MessageTypes.SYSTEM_CONNECTION_CLOSE,
    MessageTypes.SYSTEM_PING,
    MessageTypes.SYSTEM_PONG,
    MessageTypes.SYSTEM_ERROR,
    # Control - Conversation
    MessageTypes.CONTROL_CONVERSATION_CONFIG,
    MessageTypes.CONTROL_CONVERSATION_DISPLAY,
    MessageTypes.CONTROL_CONVERSATION_DEADLINE,
    MessageTypes.CONTROL_CONVERSATION_PAUSE,
    MessageTypes.CONTROL_CONVERSATION_RESUME,
    MessageTypes.CONTROL_CONVERSATION_COMPLETE,
    # Control - Item
    MessageTypes.CONTROL_ITEM_CONTEXT,
    MessageTypes.CONTROL_ITEM_SCORE,
    MessageTypes.CONTROL_ITEM_TIMEOUT,
    MessageTypes.CONTROL_ITEM_EXPIRED,
    # Control - Widget
    MessageTypes.CONTROL_WIDGET_STATE,
    MessageTypes.CONTROL_WIDGET_FOCUS,
    MessageTypes.CONTROL_WIDGET_VALIDATION,
    MessageTypes.CONTROL_WIDGET_LAYOUT,
    # Control - Flow (started/paused acknowledgments)
    MessageTypes.CONTROL_FLOW_START,
    # Data - Content
    MessageTypes.DATA_CONTENT_CHUNK,
    MessageTypes.DATA_CONTENT_COMPLETE,
    # Data - Widget
    MessageTypes.DATA_WIDGET_RENDER,
    # Data - Tools
    MessageTypes.DATA_TOOL_CALL,
    MessageTypes.DATA_TOOL_RESULT,
    # Data - Messages
    MessageTypes.DATA_MESSAGE_ACK,
    # Data - Audit
    MessageTypes.DATA_AUDIT_ACK,
    MessageTypes.DATA_AUDIT_FLUSHED,
]
