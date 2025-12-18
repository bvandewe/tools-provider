"""
Agent Host WebSocket Protocol v1.0.0 - Canvas System

Canvas system types for 2D spatial layouts.
"""

from typing import Any

from pydantic import BaseModel, Field

from .core import Position, Region
from .enums import (
    AnnotationType,
    BackgroundPattern,
    CanvasMode,
    ConditionOperator,
    ConnectionAnchor,
    ConnectionLabelPosition,
    ConnectionTypeEnum,
    MinimapPosition,
    PanButton,
    PresentationStepAction,
    SelectionMethod,
    ViewportAction,
    ViewportTargetType,
)

# =============================================================================
# CANVAS CONFIGURATION
# =============================================================================


class CanvasSettings(BaseModel):
    """Canvas dimension and background settings."""

    width: int
    height: int
    background_color: str | None = Field(default=None, alias="backgroundColor")
    background_image: str | None = Field(default=None, alias="backgroundImage")
    background_pattern: BackgroundPattern | None = Field(default=None, alias="backgroundPattern")

    model_config = {"populate_by_name": True}


class GridSettings(BaseModel):
    """Grid settings for canvas."""

    enabled: bool
    size: int
    snap_to_grid: bool = Field(..., alias="snapToGrid")
    visible: bool
    color: str | None = None

    model_config = {"populate_by_name": True}


class ZoomSettings(BaseModel):
    """Zoom settings for canvas."""

    initial: float
    min: float
    max: float
    step: float


class ViewportSettings(BaseModel):
    """Viewport settings for canvas."""

    initial_x: float = Field(..., alias="initialX")
    initial_y: float = Field(..., alias="initialY")
    pan_enabled: bool = Field(..., alias="panEnabled")
    pan_button: PanButton = Field(..., alias="panButton")

    model_config = {"populate_by_name": True}


class MinimapSettings(BaseModel):
    """Minimap settings for canvas."""

    enabled: bool
    position: MinimapPosition
    size: dict[str, int]  # {width, height}


class CanvasFeatures(BaseModel):
    """Feature flags for canvas."""

    connections: bool
    groups: bool
    layers: bool
    annotations: bool
    multi_select: bool = Field(..., alias="multiSelect")
    collaboration: bool

    model_config = {"populate_by_name": True}


class CanvasFullConfig(BaseModel):
    """Complete canvas configuration."""

    canvas: CanvasSettings
    grid: GridSettings
    zoom: ZoomSettings
    viewport: ViewportSettings
    minimap: MinimapSettings | None = None
    features: CanvasFeatures


# =============================================================================
# CONNECTIONS
# =============================================================================


class ConnectionStyle(BaseModel):
    """Visual style for connections."""

    type: ConnectionTypeEnum
    color: str
    width: int | None = None
    dash: str | None = None
    animate: bool | None = None


class ConnectionLabel(BaseModel):
    """Label for connections."""

    text: str
    position: ConnectionLabelPosition


class ConnectionEndpoint(BaseModel):
    """Endpoint of a connection."""

    widget_id: str = Field(..., alias="widgetId")
    anchor: ConnectionAnchor

    model_config = {"populate_by_name": True}


class ConnectionCondition(BaseModel):
    """Condition for conditional connections."""

    source_widget: str = Field(..., alias="sourceWidget")
    operator: ConditionOperator
    value: Any

    model_config = {"populate_by_name": True}


class ConnectionCreatePayload(BaseModel):
    """Create a connection between widgets."""

    connection_id: str = Field(..., alias="connectionId")
    source: ConnectionEndpoint
    target: ConnectionEndpoint
    style: ConnectionStyle
    label: ConnectionLabel | None = None
    interactive: bool | None = None
    condition: ConnectionCondition | None = None

    model_config = {"populate_by_name": True}


class ConnectionUpdatePayload(BaseModel):
    """Update connection properties."""

    connection_id: str = Field(..., alias="connectionId")
    style: ConnectionStyle | None = None
    label: ConnectionLabel | None = None

    model_config = {"populate_by_name": True}


class ConnectionDeletePayload(BaseModel):
    """Remove a connection."""

    connection_id: str = Field(..., alias="connectionId")
    animate: bool | None = None

    model_config = {"populate_by_name": True}


class ConnectionCreatedPayload(BaseModel):
    """User manually created a connection (Client → Server)."""

    source_widget_id: str = Field(..., alias="sourceWidgetId")
    source_anchor: ConnectionAnchor = Field(..., alias="sourceAnchor")
    target_widget_id: str = Field(..., alias="targetWidgetId")
    target_anchor: ConnectionAnchor = Field(..., alias="targetAnchor")

    model_config = {"populate_by_name": True}


# =============================================================================
# GROUPS
# =============================================================================


class GroupStyle(BaseModel):
    """Visual style for groups."""

    background_color: str | None = Field(default=None, alias="backgroundColor")
    border_color: str | None = Field(default=None, alias="borderColor")
    border_radius: int | None = Field(default=None, alias="borderRadius")

    model_config = {"populate_by_name": True}


class GroupLayout(BaseModel):
    """Layout for groups."""

    position: Position
    padding: int | None = None


class GroupCreatePayload(BaseModel):
    """Create a group."""

    group_id: str = Field(..., alias="groupId")
    title: str
    widget_ids: list[str] = Field(..., alias="widgetIds")
    style: GroupStyle | None = None
    collapsible: bool | None = None
    collapsed: bool | None = None
    draggable: bool | None = None
    layout: GroupLayout | None = None

    model_config = {"populate_by_name": True}


class GroupUpdatePayload(BaseModel):
    """Update group properties."""

    group_id: str = Field(..., alias="groupId")
    title: str | None = None
    collapsed: bool | None = None
    style: GroupStyle | None = None

    model_config = {"populate_by_name": True}


class GroupAddPayload(BaseModel):
    """Add widgets to group."""

    group_id: str = Field(..., alias="groupId")
    widget_ids: list[str] = Field(..., alias="widgetIds")

    model_config = {"populate_by_name": True}


class GroupRemovePayload(BaseModel):
    """Remove widgets from group."""

    group_id: str = Field(..., alias="groupId")
    widget_ids: list[str] = Field(..., alias="widgetIds")

    model_config = {"populate_by_name": True}


class GroupDeletePayload(BaseModel):
    """Delete the group container."""

    group_id: str = Field(..., alias="groupId")
    delete_widgets: bool = Field(default=False, alias="deleteWidgets")

    model_config = {"populate_by_name": True}


class GroupToggledPayload(BaseModel):
    """User toggled group collapse state (Client → Server)."""

    group_id: str = Field(..., alias="groupId")
    collapsed: bool

    model_config = {"populate_by_name": True}


# =============================================================================
# LAYERS
# =============================================================================


class LayerCreatePayload(BaseModel):
    """Create a new layer."""

    layer_id: str = Field(..., alias="layerId")
    name: str
    visible: bool = True
    locked: bool = False
    opacity: float = 1.0
    z_index: int = Field(..., alias="zIndex")

    model_config = {"populate_by_name": True}


class LayerUpdatePayload(BaseModel):
    """Update layer properties."""

    layer_id: str = Field(..., alias="layerId")
    name: str | None = None
    visible: bool | None = None
    locked: bool | None = None
    opacity: float | None = None

    model_config = {"populate_by_name": True}


class LayerAssignPayload(BaseModel):
    """Assign widgets to a layer."""

    layer_id: str = Field(..., alias="layerId")
    widget_ids: list[str] = Field(..., alias="widgetIds")

    model_config = {"populate_by_name": True}


class LayerToggledPayload(BaseModel):
    """User toggled layer visibility (Client → Server)."""

    layer_id: str = Field(..., alias="layerId")
    visible: bool

    model_config = {"populate_by_name": True}


# =============================================================================
# SELECTION
# =============================================================================


class SelectionPayload(BaseModel):
    """Selection state."""

    widget_ids: list[str] = Field(..., alias="widgetIds")
    group_ids: list[str] = Field(..., alias="groupIds")
    connection_ids: list[str] = Field(..., alias="connectionIds")
    selection_method: SelectionMethod | None = Field(default=None, alias="selectionMethod")

    model_config = {"populate_by_name": True}


# =============================================================================
# VIEWPORT
# =============================================================================


class ViewportFocusTarget(BaseModel):
    """Target for viewport focus operations."""

    type: ViewportTargetType
    widget_id: str | None = Field(default=None, alias="widgetId")
    widget_ids: list[str] | None = Field(default=None, alias="widgetIds")
    group_id: str | None = Field(default=None, alias="groupId")
    x: float | None = None
    y: float | None = None
    width: float | None = None
    height: float | None = None

    model_config = {"populate_by_name": True}


class ViewportPayload(BaseModel):
    """Control viewport (pan/zoom/focus)."""

    action: ViewportAction
    target: ViewportFocusTarget | None = None
    position: Position | None = None
    offset: Position | None = None
    zoom: float | None = None
    padding: int | None = None
    animate: bool | None = None
    animation_duration: int | None = Field(default=None, alias="animationDuration")
    animation_easing: str | None = Field(default=None, alias="animationEasing")

    model_config = {"populate_by_name": True}


class ViewportChangedPayload(BaseModel):
    """Viewport changed notification (Client → Server)."""

    position: Position
    zoom: float
    visible_region: Region = Field(..., alias="visibleRegion")

    model_config = {"populate_by_name": True}


# =============================================================================
# PRESENTATION MODE
# =============================================================================


class PresentationStep(BaseModel):
    """Step in a presentation sequence."""

    step_id: str = Field(..., alias="stepId")
    target: ViewportFocusTarget
    zoom: float | None = None
    narration: str | None = None
    duration: int | None = None
    action: PresentationStepAction

    model_config = {"populate_by_name": True}


class PresentationControls(BaseModel):
    """Controls for presentation."""

    show_progress: bool | None = Field(default=None, alias="showProgress")
    allow_skip: bool | None = Field(default=None, alias="allowSkip")
    allow_back: bool | None = Field(default=None, alias="allowBack")

    model_config = {"populate_by_name": True}


class PresentationStartPayload(BaseModel):
    """Start a presentation/guided tour."""

    presentation_id: str = Field(..., alias="presentationId")
    title: str
    steps: list[PresentationStep]
    controls: PresentationControls

    model_config = {"populate_by_name": True}


class PresentationStepPayload(BaseModel):
    """Move to specific step."""

    step_id: str = Field(..., alias="stepId")
    animate: bool | None = None

    model_config = {"populate_by_name": True}


class PresentationEndPayload(BaseModel):
    """End presentation mode."""

    presentation_id: str = Field(..., alias="presentationId")
    reason: str

    model_config = {"populate_by_name": True}


class PresentationNavigatedPayload(BaseModel):
    """User navigated within presentation (Client → Server)."""

    presentation_id: str = Field(..., alias="presentationId")
    from_step: str = Field(..., alias="fromStep")
    to_step: str = Field(..., alias="toStep")
    action: str  # "next" | "previous" | "skip"

    model_config = {"populate_by_name": True}


# =============================================================================
# BOOKMARKS
# =============================================================================


class BookmarkCreatePayload(BaseModel):
    """Create a bookmark/navigation point."""

    bookmark_id: str = Field(..., alias="bookmarkId")
    name: str
    description: str | None = None
    target: ViewportFocusTarget
    zoom: float | None = None
    icon: str | None = None
    color: str | None = None
    show_in_navigation: bool | None = Field(default=None, alias="showInNavigation")
    sort_order: int | None = Field(default=None, alias="sortOrder")

    model_config = {"populate_by_name": True}


class BookmarkUpdatePayload(BaseModel):
    """Update bookmark properties."""

    bookmark_id: str = Field(..., alias="bookmarkId")
    name: str | None = None
    icon: str | None = None
    color: str | None = None

    model_config = {"populate_by_name": True}


class BookmarkDeletePayload(BaseModel):
    """Remove a bookmark."""

    bookmark_id: str = Field(..., alias="bookmarkId")

    model_config = {"populate_by_name": True}


class BookmarkNavigatePayload(BaseModel):
    """User navigated to bookmark (Client → Server)."""

    bookmark_id: str = Field(..., alias="bookmarkId")

    model_config = {"populate_by_name": True}


class BookmarkCreatedPayload(BaseModel):
    """User created a personal bookmark (Client → Server)."""

    name: str
    position: Position
    zoom: float | None = None

    model_config = {"populate_by_name": True}


# =============================================================================
# COMMENTS
# =============================================================================


class CommentAuthor(BaseModel):
    """Comment author information."""

    user_id: str = Field(..., alias="userId")
    name: str
    avatar: str | None = None

    model_config = {"populate_by_name": True}


class CommentAttachment(BaseModel):
    """What the comment is attached to."""

    type: str  # "widget" | "canvas" | "connection"
    widget_id: str | None = Field(default=None, alias="widgetId")
    connection_id: str | None = Field(default=None, alias="connectionId")

    model_config = {"populate_by_name": True}


class CommentCreatePayload(BaseModel):
    """Create a comment thread."""

    comment_id: str = Field(..., alias="commentId")
    thread_id: str = Field(..., alias="threadId")
    attached_to: CommentAttachment = Field(..., alias="attachedTo")
    position: Position
    author: CommentAuthor
    content: str
    timestamp: str
    resolved: bool = False

    model_config = {"populate_by_name": True}


class CommentReplyPayload(BaseModel):
    """Reply to a comment (Client → Server)."""

    thread_id: str = Field(..., alias="threadId")
    content: str

    model_config = {"populate_by_name": True}


class CommentResolvePayload(BaseModel):
    """Mark thread as resolved."""

    thread_id: str = Field(..., alias="threadId")
    resolved: bool

    model_config = {"populate_by_name": True}


class CommentDeletePayload(BaseModel):
    """Delete a comment."""

    comment_id: str = Field(..., alias="commentId")

    model_config = {"populate_by_name": True}


# =============================================================================
# HISTORY
# =============================================================================


class HistoryEntry(BaseModel):
    """History entry for undo/redo."""

    entry_id: str = Field(..., alias="entryId")
    timestamp: str
    action: str
    description: str
    widget_id: str | None = Field(default=None, alias="widgetId")
    can_revert: bool = Field(..., alias="canRevert")

    model_config = {"populate_by_name": True}


class HistoryEntriesPayload(BaseModel):
    """History entries response."""

    entries: list[HistoryEntry]
    total_count: int = Field(..., alias="totalCount")
    has_more: bool = Field(..., alias="hasMore")

    model_config = {"populate_by_name": True}


# =============================================================================
# TEMPLATES
# =============================================================================


class WidgetTemplate(BaseModel):
    """Pre-defined widget template."""

    template_id: str = Field(..., alias="templateId")
    name: str
    category: str
    preview: str | None = None
    widget_type: str = Field(..., alias="widgetType")
    config: Any

    model_config = {"populate_by_name": True}


class TemplateListPayload(BaseModel):
    """Available widget templates."""

    templates: list[WidgetTemplate]


class TemplateInstantiatePayload(BaseModel):
    """Create widget from template (Client → Server)."""

    template_id: str = Field(..., alias="templateId")
    position: Position

    model_config = {"populate_by_name": True}


# =============================================================================
# ANNOTATIONS
# =============================================================================


class AnnotationStyle(BaseModel):
    """Style for annotations."""

    background_color: str | None = Field(default=None, alias="backgroundColor")
    text_color: str | None = Field(default=None, alias="textColor")
    font_size: int | None = Field(default=None, alias="fontSize")

    model_config = {"populate_by_name": True}


class AnnotationCreatePayload(BaseModel):
    """Create an annotation."""

    annotation_id: str = Field(..., alias="annotationId")
    annotation_type: AnnotationType = Field(..., alias="annotationType")
    content: str
    position: Position
    style: AnnotationStyle | None = None
    author: str | None = None
    timestamp: str | None = None

    model_config = {"populate_by_name": True}


class AnnotationCreatedPayload(BaseModel):
    """User created annotation (Client → Server)."""

    annotation_type: AnnotationType = Field(..., alias="annotationType")
    content: str
    position: Position

    model_config = {"populate_by_name": True}


# =============================================================================
# CANVAS MODE
# =============================================================================


class CanvasModeConfig(BaseModel):
    """Configuration for canvas mode switch."""

    connection_type: str | None = Field(default=None, alias="connectionType")
    source_widget: str | None = Field(default=None, alias="sourceWidget")

    model_config = {"populate_by_name": True}


class CanvasModePayload(BaseModel):
    """Switch canvas interaction modes."""

    mode: CanvasMode
    config: CanvasModeConfig | None = None


class CanvasModeChangedPayload(BaseModel):
    """Canvas mode changed (Client → Server)."""

    mode: CanvasMode
    previous_mode: CanvasMode = Field(..., alias="previousMode")

    model_config = {"populate_by_name": True}
