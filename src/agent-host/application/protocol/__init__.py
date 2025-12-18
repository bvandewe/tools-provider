"""
Agent Host WebSocket Protocol v1.0.0 - Python Pydantic Models

This package provides type-safe Pydantic models for the Agent Host WebSocket protocol.
Both frontend (TypeScript) and backend (Python) implementations share the same protocol
specification defined in websocket-protocol-v1.md.

Package Structure:
    - enums.py: All enums, Literal types, close codes, MessageTypes constants
    - core.py: Base types (Position, Dimensions, Region, ProtocolMessage)
    - system.py: System message payloads (connection lifecycle, keepalive, errors)
    - audit.py: Audit/telemetry types
    - control.py: Control plane payloads (conversation, item, widget, flow, navigation)
    - data.py: Data plane payloads (content, tools, messages, responses)
    - canvas.py: Canvas system types (connections, groups, layers, viewport, etc.)
    - iframe.py: IFRAME widget types
    - widgets/: Widget subpackage
        - base.py: Widget base types
        - configs.py: All widget configuration schemas
        - values.py: Widget response value types

Usage:
    from application.protocol import (
        ProtocolMessage,
        MessageTypes,
        ConversationConfigPayload,
        WidgetRenderPayload,
        # ... etc
    )
"""

# =============================================================================
# ENUMS & CONSTANTS
# =============================================================================
# =============================================================================
# AUDIT PAYLOADS
# =============================================================================
from .audit import (
    AuditAckPayload,
    AuditConfig,
    AuditConfigUpdatePayload,
    AuditElementContext,
    AuditElementRegion,
    AuditEvent,
    AuditEventsPayload,
    AuditFlushedPayload,
    AuditFlushPayload,
)

# =============================================================================
# CANVAS SYSTEM
# =============================================================================
from .canvas import (
    AnnotationCreatedPayload,
    AnnotationCreatePayload,
    # Annotations
    AnnotationStyle,
    BookmarkCreatedPayload,
    # Bookmarks
    BookmarkCreatePayload,
    BookmarkDeletePayload,
    BookmarkNavigatePayload,
    BookmarkUpdatePayload,
    CanvasFeatures,
    CanvasFullConfig,
    CanvasModeChangedPayload,
    # Canvas mode
    CanvasModeConfig,
    CanvasModePayload,
    # Configuration
    CanvasSettings,
    CommentAttachment,
    # Comments
    CommentAuthor,
    CommentCreatePayload,
    CommentDeletePayload,
    CommentReplyPayload,
    CommentResolvePayload,
    ConnectionCondition,
    ConnectionCreatedPayload,
    ConnectionCreatePayload,
    ConnectionDeletePayload,
    ConnectionEndpoint,
    ConnectionLabel,
    # Connections
    ConnectionStyle,
    ConnectionUpdatePayload,
    GridSettings,
    GroupAddPayload,
    GroupCreatePayload,
    GroupDeletePayload,
    GroupLayout,
    GroupRemovePayload,
    # Groups
    GroupStyle,
    GroupToggledPayload,
    GroupUpdatePayload,
    HistoryEntriesPayload,
    # History
    HistoryEntry,
    LayerAssignPayload,
    # Layers
    LayerCreatePayload,
    LayerToggledPayload,
    LayerUpdatePayload,
    MinimapSettings,
    PresentationControls,
    PresentationEndPayload,
    PresentationNavigatedPayload,
    PresentationStartPayload,
    # Presentation
    PresentationStep,
    PresentationStepPayload,
    # Selection
    SelectionPayload,
    TemplateInstantiatePayload,
    TemplateListPayload,
    ViewportChangedPayload,
    # Viewport
    ViewportFocusTarget,
    ViewportPayload,
    ViewportSettings,
    # Templates
    WidgetTemplate,
    ZoomSettings,
)

# =============================================================================
# CONTROL PLANE PAYLOADS
# =============================================================================
from .control import (
    CanvasConfig,
    ConversationConfigPayload,
    ConversationDeadlinePayload,
    ConversationDisplayPayload,
    ConversationPausePayload,
    FlowCancelPayload,
    # Conversation
    FlowConfig,
    FlowPausePayload,
    # Flow & Navigation
    FlowStartPayload,
    # Item
    ItemContextPayload,
    ItemExpiredPayload,
    ItemScorePayload,
    ItemTimeoutPayload,
    NavigationPayload,
    WidgetCondition,
    WidgetConditionPayload,
    WidgetDismissedPayload,
    WidgetFocusPayload,
    WidgetLayout as ControlWidgetLayout,
    WidgetLayoutPayload,
    WidgetMovedPayload,
    WidgetResizedPayload,
    # Widget state
    WidgetStatePayload,
    WidgetValidationPayload,
)

# =============================================================================
# CORE TYPES
# =============================================================================
from .core import (
    Dimensions,
    Position,
    ProtocolMessage,
    Region,
    calculate_reconnect_backoff,
    create_message,
)

# =============================================================================
# DATA PLANE PAYLOADS
# =============================================================================
from .data import (
    # Content streaming
    ContentChunkPayload,
    ContentCompletePayload,
    MessageAckPayload,
    # User messages
    MessageSendPayload,
    # Responses
    ResponseMetadata,
    ResponseSubmitPayload,
    # Tool execution
    ToolCallPayload,
    ToolResultPayload,
)
from .enums import (
    AlignmentOption,
    AnchorPosition,
    AnnotationType,
    AppCloseCode,
    AuditElementType,
    # Audit enums
    AuditEventType,
    BackgroundPattern,
    # Canvas enums
    CanvasMode,
    ConditionEffect,
    # Condition system
    ConditionOperator,
    ConnectionAnchor,
    ConnectionLabelPosition,
    ConnectionTypeEnum,
    DismissAction,
    # Display and behavior
    DisplayMode,
    DragDropVariant,
    ItemTimerMode,
    MessagePlane,
    # Core enums
    MessageSource,
    # Message type constants
    MessageTypes,
    MinimapPosition,
    PanButton,
    PresentationStepAction,
    ProtocolVersion,
    SelectionMethod,
    # Close codes
    StandardCloseCode,
    ViewportAction,
    ViewportTargetType,
    WidgetCompletionBehavior,
    WidgetState,
    # Widget system
    WidgetType,
)

# =============================================================================
# IFRAME WIDGET
# =============================================================================
from .iframe import (
    IframeCommandPayload,
    IframeCommunicationConfig,
    IframeConfig,
    IframeErrorPayload,
    IframeEventPayload,
    IframeLayoutConfig,
    IframeLoadedPayload,
    IframeLoadingConfig,
    IframePermissionsConfig,
    IframeResizePayload,
    IframeSandboxConfig,
    IframeStatePayload,
)

# =============================================================================
# SYSTEM PAYLOADS
# =============================================================================
from .system import (
    ClientState,
    SystemConnectionClosePayload,
    SystemConnectionEstablishedPayload,
    SystemConnectionResumedPayload,
    SystemConnectionResumePayload,
    SystemErrorPayload,
    SystemPingPongPayload,
)

# =============================================================================
# WIDGETS SUBPACKAGE
# =============================================================================
from .widgets import (
    CodeEditorConfig,
    DatePickerConfig,
    DateRangeValue,
    DocumentSection,
    DocumentViewerConfig,
    DocumentViewerHighlight,
    DocumentViewerValue,
    # Widget response values
    DragDropCategoryValue,
    DragDropConfig,
    DragDropFreePosition,
    DragDropGraphicalValue,
    DragDropItem,
    DragDropPlaceholder,
    DragDropPlacement,
    DragDropZone,
    DrawingConfig,
    DrawingToolConfig,
    DrawingValue,
    DropdownConfig,
    DropdownGroup,
    DropdownOption,
    EmbeddedWidget,
    FileUploadConfig,
    FileUploadFile,
    FileUploadValue,
    FreeTextConfig,
    GraphConstraints,
    GraphEdgeType,
    GraphNodeType,
    GraphRegion,
    GraphToolbar,
    GraphTopologyConfig,
    GraphTopologyEdge,
    GraphTopologyNode,
    GraphTopologyRegionValue,
    GraphTopologyValue,
    HotspotConfig,
    HotspotRegion,
    HotspotValue,
    ImageConfig,
    ImageValue,
    MatrixChoiceColumn,
    MatrixChoiceConfig,
    MatrixChoiceRow,
    MatrixChoiceValue,
    # Widget configs
    MultipleChoiceConfig,
    RatingConfig,
    SliderConfig,
    StickyNoteConfig,
    StickyNoteStyle,
    StickyNoteValue,
    VideoCaption,
    VideoChapter,
    VideoCheckpoint,
    VideoConfig,
    VideoControls,
    VideoPlaybackEvent,
    VideoQuality,
    VideoValue,
    WidgetConstraints,
    # Base types
    WidgetLayout,
    WidgetRenderPayload,
)

__all__ = [
    # ==========================================================================
    # ENUMS & CONSTANTS
    # ==========================================================================
    "MessageSource",
    "ProtocolVersion",
    "MessagePlane",
    "DisplayMode",
    "ItemTimerMode",
    "WidgetCompletionBehavior",
    "WidgetState",
    "WidgetType",
    "AnchorPosition",
    "DismissAction",
    "DragDropVariant",
    "ConditionOperator",
    "ConditionEffect",
    "CanvasMode",
    "ConnectionTypeEnum",
    "ConnectionAnchor",
    "ConnectionLabelPosition",
    "BackgroundPattern",
    "PanButton",
    "MinimapPosition",
    "SelectionMethod",
    "AnnotationType",
    "ViewportAction",
    "ViewportTargetType",
    "PresentationStepAction",
    "AlignmentOption",
    "AuditEventType",
    "AuditElementType",
    "StandardCloseCode",
    "AppCloseCode",
    "MessageTypes",
    # ==========================================================================
    # CORE TYPES
    # ==========================================================================
    "Position",
    "Dimensions",
    "Region",
    "ProtocolMessage",
    "create_message",
    "calculate_reconnect_backoff",
    # ==========================================================================
    # SYSTEM PAYLOADS
    # ==========================================================================
    "ClientState",
    "SystemConnectionEstablishedPayload",
    "SystemConnectionResumePayload",
    "SystemConnectionResumedPayload",
    "SystemConnectionClosePayload",
    "SystemPingPongPayload",
    "SystemErrorPayload",
    # ==========================================================================
    # AUDIT PAYLOADS
    # ==========================================================================
    "AuditConfig",
    "AuditElementRegion",
    "AuditElementContext",
    "AuditEvent",
    "AuditEventsPayload",
    "AuditAckPayload",
    "AuditFlushPayload",
    "AuditFlushedPayload",
    "AuditConfigUpdatePayload",
    # ==========================================================================
    # CONTROL PLANE PAYLOADS
    # ==========================================================================
    "FlowConfig",
    "CanvasConfig",
    "ConversationConfigPayload",
    "ConversationDisplayPayload",
    "ConversationDeadlinePayload",
    "ConversationPausePayload",
    "ItemContextPayload",
    "ItemScorePayload",
    "ItemTimeoutPayload",
    "ItemExpiredPayload",
    "WidgetStatePayload",
    "WidgetFocusPayload",
    "WidgetValidationPayload",
    "ControlWidgetLayout",
    "WidgetLayoutPayload",
    "WidgetMovedPayload",
    "WidgetResizedPayload",
    "WidgetDismissedPayload",
    "WidgetCondition",
    "WidgetConditionPayload",
    "FlowStartPayload",
    "FlowPausePayload",
    "FlowCancelPayload",
    "NavigationPayload",
    # ==========================================================================
    # DATA PLANE PAYLOADS
    # ==========================================================================
    "ContentChunkPayload",
    "ContentCompletePayload",
    "ToolCallPayload",
    "ToolResultPayload",
    "MessageSendPayload",
    "MessageAckPayload",
    "ResponseMetadata",
    "ResponseSubmitPayload",
    # ==========================================================================
    # CANVAS SYSTEM
    # ==========================================================================
    "CanvasSettings",
    "GridSettings",
    "ZoomSettings",
    "ViewportSettings",
    "MinimapSettings",
    "CanvasFeatures",
    "CanvasFullConfig",
    "ConnectionStyle",
    "ConnectionLabel",
    "ConnectionEndpoint",
    "ConnectionCondition",
    "ConnectionCreatePayload",
    "ConnectionUpdatePayload",
    "ConnectionDeletePayload",
    "ConnectionCreatedPayload",
    "GroupStyle",
    "GroupLayout",
    "GroupCreatePayload",
    "GroupUpdatePayload",
    "GroupAddPayload",
    "GroupRemovePayload",
    "GroupDeletePayload",
    "GroupToggledPayload",
    "LayerCreatePayload",
    "LayerUpdatePayload",
    "LayerAssignPayload",
    "LayerToggledPayload",
    "SelectionPayload",
    "ViewportFocusTarget",
    "ViewportPayload",
    "ViewportChangedPayload",
    "PresentationStep",
    "PresentationControls",
    "PresentationStartPayload",
    "PresentationStepPayload",
    "PresentationEndPayload",
    "PresentationNavigatedPayload",
    "BookmarkCreatePayload",
    "BookmarkUpdatePayload",
    "BookmarkDeletePayload",
    "BookmarkNavigatePayload",
    "BookmarkCreatedPayload",
    "CommentAuthor",
    "CommentAttachment",
    "CommentCreatePayload",
    "CommentReplyPayload",
    "CommentResolvePayload",
    "CommentDeletePayload",
    "HistoryEntry",
    "HistoryEntriesPayload",
    "WidgetTemplate",
    "TemplateListPayload",
    "TemplateInstantiatePayload",
    "AnnotationStyle",
    "AnnotationCreatePayload",
    "AnnotationCreatedPayload",
    "CanvasModeConfig",
    "CanvasModePayload",
    "CanvasModeChangedPayload",
    # ==========================================================================
    # IFRAME WIDGET
    # ==========================================================================
    "IframeSandboxConfig",
    "IframePermissionsConfig",
    "IframeCommunicationConfig",
    "IframeLoadingConfig",
    "IframeLayoutConfig",
    "IframeConfig",
    "IframeEventPayload",
    "IframeCommandPayload",
    "IframeStatePayload",
    "IframeLoadedPayload",
    "IframeErrorPayload",
    "IframeResizePayload",
    # ==========================================================================
    # WIDGETS
    # ==========================================================================
    "WidgetLayout",
    "WidgetConstraints",
    "WidgetRenderPayload",
    "MultipleChoiceConfig",
    "FreeTextConfig",
    "CodeEditorConfig",
    "SliderConfig",
    "DragDropItem",
    "DragDropZone",
    "DragDropPlaceholder",
    "DragDropConfig",
    "GraphNodeType",
    "GraphEdgeType",
    "GraphRegion",
    "GraphConstraints",
    "GraphToolbar",
    "GraphTopologyConfig",
    "MatrixChoiceRow",
    "MatrixChoiceColumn",
    "MatrixChoiceConfig",
    "EmbeddedWidget",
    "DocumentSection",
    "DocumentViewerConfig",
    "HotspotRegion",
    "HotspotConfig",
    "DrawingToolConfig",
    "DrawingConfig",
    "FileUploadConfig",
    "RatingConfig",
    "DatePickerConfig",
    "DropdownOption",
    "DropdownGroup",
    "DropdownConfig",
    "ImageConfig",
    "VideoCaption",
    "VideoQuality",
    "VideoChapter",
    "VideoCheckpoint",
    "VideoControls",
    "VideoConfig",
    "StickyNoteStyle",
    "StickyNoteConfig",
    "DragDropCategoryValue",
    "DragDropPlacement",
    "DragDropFreePosition",
    "DragDropGraphicalValue",
    "GraphTopologyNode",
    "GraphTopologyEdge",
    "GraphTopologyRegionValue",
    "GraphTopologyValue",
    "MatrixChoiceValue",
    "DocumentViewerHighlight",
    "DocumentViewerValue",
    "HotspotValue",
    "DrawingValue",
    "FileUploadFile",
    "FileUploadValue",
    "DateRangeValue",
    "ImageValue",
    "VideoPlaybackEvent",
    "VideoValue",
    "StickyNoteValue",
]
