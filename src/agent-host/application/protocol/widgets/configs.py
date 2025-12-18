"""
Agent Host WebSocket Protocol v1.0.0 - Widget Configuration Types

Configuration schemas for all 19 widget types.
"""

from typing import Any

from pydantic import BaseModel, Field

from ..core import Region
from ..enums import (
    ContentType,
    DatePickerMode,
    DragDropVariant,
    HotspotShape,
    MatrixLayout,
    ObjectFit,
    RatingStyle,
    SelectionMode,
    WidgetType,
)

# =============================================================================
# MULTIPLE CHOICE
# =============================================================================


class MultipleChoiceConfig(BaseModel):
    """Configuration for multiple_choice widget."""

    options: list[str]
    allow_multiple: bool = Field(default=False, alias="allowMultiple")
    shuffle_options: bool | None = Field(default=None, alias="shuffleOptions")
    show_labels: bool | None = Field(default=None, alias="showLabels")
    label_style: str | None = Field(default=None, alias="labelStyle")  # "letter" | "number"

    model_config = {"populate_by_name": True}


# =============================================================================
# FREE TEXT
# =============================================================================


class FreeTextConfig(BaseModel):
    """Configuration for free_text widget."""

    placeholder: str | None = None
    min_length: int | None = Field(default=None, alias="minLength")
    max_length: int | None = Field(default=None, alias="maxLength")
    multiline: bool = False
    rows: int | None = None

    model_config = {"populate_by_name": True}


# =============================================================================
# CODE EDITOR
# =============================================================================


class CodeEditorConfig(BaseModel):
    """Configuration for code_editor widget."""

    language: str
    initial_code: str | None = Field(default=None, alias="initialCode")
    min_lines: int | None = Field(default=None, alias="minLines")
    max_lines: int | None = Field(default=None, alias="maxLines")
    read_only: bool | None = Field(default=None, alias="readOnly")
    show_line_numbers: bool | None = Field(default=None, alias="showLineNumbers")

    model_config = {"populate_by_name": True}


# =============================================================================
# SLIDER
# =============================================================================


class SliderConfig(BaseModel):
    """Configuration for slider widget."""

    min: float
    max: float
    step: float
    default_value: float | None = Field(default=None, alias="defaultValue")
    show_value: bool | None = Field(default=None, alias="showValue")
    labels: dict[str, str] | None = None

    model_config = {"populate_by_name": True}


# =============================================================================
# DRAG & DROP
# =============================================================================


class DragDropItem(BaseModel):
    """Draggable item definition."""

    id: str
    content: str
    reusable: bool | None = None
    icon: str | None = None


class DragDropZone(BaseModel):
    """Drop zone definition."""

    id: str
    label: str
    ordered: bool | None = None
    slots: int | None = None


class DragDropPlaceholder(BaseModel):
    """Placeholder for graphical drag & drop."""

    id: str
    region: Region
    accepts: list[str] | None = None
    hint: str | None = None


class DragDropConfig(BaseModel):
    """Configuration for drag_drop widget."""

    variant: DragDropVariant = "category"
    items: list[DragDropItem]
    zones: list[DragDropZone] | None = None
    placeholders: list[DragDropPlaceholder] | None = None
    background_image: str | None = Field(default=None, alias="backgroundImage")
    background_size: dict[str, int] | None = Field(default=None, alias="backgroundSize")
    allow_multiple_per_zone: bool | None = Field(default=None, alias="allowMultiplePerZone")
    require_all_placed: bool | None = Field(default=None, alias="requireAllPlaced")
    shuffle_items: bool | None = Field(default=None, alias="shuffleItems")
    show_zone_capacity: bool | None = Field(default=None, alias="showZoneCapacity")
    show_slot_numbers: bool | None = Field(default=None, alias="showSlotNumbers")
    show_placeholder_hints: bool | None = Field(default=None, alias="showPlaceholderHints")
    snap_to_placeholder: bool | None = Field(default=None, alias="snapToPlaceholder")
    allow_free_positioning: bool | None = Field(default=None, alias="allowFreePositioning")

    model_config = {"populate_by_name": True}


# =============================================================================
# GRAPH TOPOLOGY
# =============================================================================


class GraphNodeProperty(BaseModel):
    """Property definition for graph nodes."""

    name: str
    type: str  # "text" | "number" | "select"
    required: bool | None = None
    default: Any = None
    options: list[str] | None = None


class GraphNodeType(BaseModel):
    """Node type definition for graph topology."""

    type_id: str = Field(..., alias="typeId")
    label: str
    icon: str | None = None
    color: str | None = None
    max_instances: int | None = Field(default=None, alias="maxInstances")
    properties: list[GraphNodeProperty] | None = None

    model_config = {"populate_by_name": True}


class GraphEdgeType(BaseModel):
    """Edge type definition for graph topology."""

    type_id: str = Field(..., alias="typeId")
    label: str
    style: str  # "arrow" | "line" | "dashed-arrow" | "double-arrow"
    color: str | None = None
    bidirectional: bool | None = None

    model_config = {"populate_by_name": True}


class GraphRegion(BaseModel):
    """Region definition for graph topology."""

    region_id: str = Field(..., alias="regionId")
    label: str
    color: str | None = None
    border_color: str | None = Field(default=None, alias="borderColor")

    model_config = {"populate_by_name": True}


class GraphConstraints(BaseModel):
    """Constraints for graph topology."""

    min_nodes: int | None = Field(default=None, alias="minNodes")
    max_nodes: int | None = Field(default=None, alias="maxNodes")
    min_edges: int | None = Field(default=None, alias="minEdges")
    max_edges: int | None = Field(default=None, alias="maxEdges")
    allow_cycles: bool | None = Field(default=None, alias="allowCycles")
    allow_self_loops: bool | None = Field(default=None, alias="allowSelfLoops")
    require_connected: bool | None = Field(default=None, alias="requireConnected")

    model_config = {"populate_by_name": True}


class GraphToolbar(BaseModel):
    """Toolbar configuration for graph topology."""

    show_node_palette: bool | None = Field(default=None, alias="showNodePalette")
    show_edge_tools: bool | None = Field(default=None, alias="showEdgeTools")
    show_region_tools: bool | None = Field(default=None, alias="showRegionTools")
    show_layout_tools: bool | None = Field(default=None, alias="showLayoutTools")

    model_config = {"populate_by_name": True}


class GraphValidationRule(BaseModel):
    """Validation rule for graph topology."""

    rule: str
    message: str


class GraphTopologyConfig(BaseModel):
    """Configuration for graph_topology widget."""

    mode: str  # "build" | "view"
    node_types: list[GraphNodeType] = Field(..., alias="nodeTypes")
    edge_types: list[GraphEdgeType] = Field(..., alias="edgeTypes")
    regions: list[GraphRegion] | None = None
    constraints: GraphConstraints | None = None
    initial_graph: Any | None = Field(default=None, alias="initialGraph")
    toolbar: GraphToolbar | None = None
    validation: dict[str, list[GraphValidationRule]] | None = None

    model_config = {"populate_by_name": True}


# =============================================================================
# MATRIX CHOICE
# =============================================================================


class MatrixChoiceRow(BaseModel):
    """Row definition for matrix choice."""

    id: str
    label: str


class MatrixChoiceColumn(BaseModel):
    """Column definition for matrix choice."""

    id: str
    label: str
    value: int | None = None


class MatrixChoiceConfig(BaseModel):
    """Configuration for matrix_choice widget."""

    layout: MatrixLayout = "rows"
    rows: list[MatrixChoiceRow]
    columns: list[MatrixChoiceColumn]
    selection_mode: SelectionMode = Field(default="single", alias="selectionMode")
    require_all_rows: bool | None = Field(default=None, alias="requireAllRows")
    shuffle_rows: bool | None = Field(default=None, alias="shuffleRows")
    shuffle_columns: bool | None = Field(default=None, alias="shuffleColumns")
    show_row_numbers: bool | None = Field(default=None, alias="showRowNumbers")
    sticky_header: bool | None = Field(default=None, alias="stickyHeader")

    model_config = {"populate_by_name": True}


# =============================================================================
# DOCUMENT VIEWER
# =============================================================================


class TableOfContentsConfig(BaseModel):
    """Table of contents configuration."""

    enabled: bool = True
    position: str = "left"  # "left" | "right"
    collapsible: bool | None = None
    default_expanded: bool | None = Field(default=None, alias="defaultExpanded")
    max_depth: int | None = Field(default=None, alias="maxDepth")

    model_config = {"populate_by_name": True}


class NavigationConfig(BaseModel):
    """Navigation configuration for document viewer."""

    show_progress: bool | None = Field(default=None, alias="showProgress")
    show_page_numbers: bool | None = Field(default=None, alias="showPageNumbers")
    enable_search: bool | None = Field(default=None, alias="enableSearch")
    enable_highlight: bool | None = Field(default=None, alias="enableHighlight")

    model_config = {"populate_by_name": True}


class DocumentSection(BaseModel):
    """Section definition for document viewer."""

    section_id: str = Field(..., alias="sectionId")
    heading: str
    anchor_id: str = Field(..., alias="anchorId")
    required_read_time: int | None = Field(default=None, alias="requiredReadTime")
    checkpoint: bool | None = None

    model_config = {"populate_by_name": True}


class EmbeddedWidget(BaseModel):
    """Embedded widget within document."""

    anchor_id: str = Field(..., alias="anchorId")
    widget_id: str = Field(..., alias="widgetId")
    widget_type: WidgetType = Field(..., alias="widgetType")
    config: Any

    model_config = {"populate_by_name": True}


class ReadingModeConfig(BaseModel):
    """Reading mode configuration."""

    font_size: str | None = Field(default=None, alias="fontSize")  # "small" | "medium" | "large"
    line_height: float | None = Field(default=None, alias="lineHeight")
    theme: str | None = None  # "light" | "dark" | "auto"

    model_config = {"populate_by_name": True}


class DocumentViewerConfig(BaseModel):
    """Configuration for document_viewer widget."""

    content: str | None = None
    content_url: str | None = Field(default=None, alias="contentUrl")
    content_type: ContentType = Field(default="markdown", alias="contentType")
    table_of_contents: TableOfContentsConfig | None = Field(default=None, alias="tableOfContents")
    navigation: NavigationConfig | None = None
    sections: list[DocumentSection] | None = None
    embedded_widgets: list[EmbeddedWidget] | None = Field(default=None, alias="embeddedWidgets")
    reading_mode: ReadingModeConfig | None = Field(default=None, alias="readingMode")

    model_config = {"populate_by_name": True}


# =============================================================================
# HOTSPOT
# =============================================================================


class HotspotRegion(BaseModel):
    """Clickable region on image."""

    id: str
    shape: HotspotShape
    coords: dict[str, Any]
    label: str | None = None
    correct: bool | None = None


class HotspotConfig(BaseModel):
    """Configuration for hotspot widget."""

    image: str
    image_size: dict[str, int] = Field(..., alias="imageSize")
    regions: list[HotspotRegion]
    selection_mode: SelectionMode = Field(default="single", alias="selectionMode")
    show_labels: bool | None = Field(default=None, alias="showLabels")
    highlight_on_hover: bool | None = Field(default=None, alias="highlightOnHover")
    show_feedback_immediately: bool | None = Field(default=None, alias="showFeedbackImmediately")

    model_config = {"populate_by_name": True}


# =============================================================================
# DRAWING
# =============================================================================


class DrawingToolConfig(BaseModel):
    """Configuration for individual drawing tools."""

    enabled: bool = True
    colors: list[str] | None = None
    sizes: list[int] | None = None
    opacity: float | None = None
    types: list[str] | None = None
    fonts: list[str] | None = None


class DrawingToolsConfig(BaseModel):
    """Configuration for all drawing tools."""

    pen: DrawingToolConfig | None = None
    highlighter: DrawingToolConfig | None = None
    eraser: DrawingToolConfig | None = None
    shapes: DrawingToolConfig | None = None
    text: DrawingToolConfig | None = None


class DrawingConfig(BaseModel):
    """Configuration for drawing widget."""

    canvas_size: dict[str, int] = Field(..., alias="canvasSize")
    background_image: str | None = Field(default=None, alias="backgroundImage")
    background_color: str | None = Field(default=None, alias="backgroundColor")
    tools: DrawingToolsConfig
    initial_drawing: Any | None = Field(default=None, alias="initialDrawing")
    allow_undo: bool | None = Field(default=None, alias="allowUndo")
    max_undo_steps: int | None = Field(default=None, alias="maxUndoSteps")

    model_config = {"populate_by_name": True}


# =============================================================================
# FILE UPLOAD
# =============================================================================


class FileUploadConfig(BaseModel):
    """Configuration for file_upload widget."""

    accept: list[str]
    max_file_size: int = Field(..., alias="maxFileSize")
    max_files: int = Field(..., alias="maxFiles")
    min_files: int | None = Field(default=None, alias="minFiles")
    allow_drag_drop: bool | None = Field(default=None, alias="allowDragDrop")
    show_preview: bool | None = Field(default=None, alias="showPreview")
    preview_max_height: int | None = Field(default=None, alias="previewMaxHeight")
    upload_endpoint: str = Field(..., alias="uploadEndpoint")
    upload_method: str | None = Field(default=None, alias="uploadMethod")  # "POST" | "PUT"
    upload_headers: dict[str, str] | None = Field(default=None, alias="uploadHeaders")
    auto_upload: bool | None = Field(default=None, alias="autoUpload")
    show_progress: bool | None = Field(default=None, alias="showProgress")
    allow_remove: bool | None = Field(default=None, alias="allowRemove")
    placeholder: str | None = None
    helper_text: str | None = Field(default=None, alias="helperText")

    model_config = {"populate_by_name": True}


# =============================================================================
# RATING
# =============================================================================


class RatingConfig(BaseModel):
    """Configuration for rating widget."""

    style: RatingStyle = "stars"
    max_rating: int = Field(..., alias="maxRating")
    allow_half: bool | None = Field(default=None, alias="allowHalf")
    default_value: float | None = Field(default=None, alias="defaultValue")
    show_value: bool | None = Field(default=None, alias="showValue")
    show_labels: bool | None = Field(default=None, alias="showLabels")
    labels: dict[str, str] | None = None
    size: str | None = None  # "small" | "medium" | "large"
    color: str | None = None
    empty_color: str | None = Field(default=None, alias="emptyColor")
    icon: str | None = None
    required: bool | None = None

    model_config = {"populate_by_name": True}


# =============================================================================
# DATE PICKER
# =============================================================================


class DatePickerConfig(BaseModel):
    """Configuration for date_picker widget."""

    mode: DatePickerMode = "date"
    format: str = "YYYY-MM-DD"
    display_format: str | None = Field(default=None, alias="displayFormat")
    placeholder: str | None = None
    min_date: str | None = Field(default=None, alias="minDate")
    max_date: str | None = Field(default=None, alias="maxDate")
    disabled_dates: list[str] | None = Field(default=None, alias="disabledDates")
    disabled_days_of_week: list[int] | None = Field(default=None, alias="disabledDaysOfWeek")
    default_value: str | None = Field(default=None, alias="defaultValue")
    show_today_button: bool | None = Field(default=None, alias="showTodayButton")
    show_clear_button: bool | None = Field(default=None, alias="showClearButton")
    week_starts_on: int | None = Field(default=None, alias="weekStartsOn")
    locale: str | None = None
    timezone: str | None = None
    required: bool | None = None

    model_config = {"populate_by_name": True}


# =============================================================================
# DROPDOWN
# =============================================================================


class DropdownOption(BaseModel):
    """Option for dropdown widget."""

    value: str
    label: str
    icon: str | None = None
    disabled: bool | None = None
    group: str | None = None


class DropdownGroup(BaseModel):
    """Group for dropdown options."""

    id: str
    label: str


class DropdownConfig(BaseModel):
    """Configuration for dropdown widget."""

    options: list[DropdownOption]
    groups: list[DropdownGroup] | None = None
    multiple: bool = False
    searchable: bool | None = None
    clearable: bool | None = None
    placeholder: str | None = None
    no_options_message: str | None = Field(default=None, alias="noOptionsMessage")
    max_selections: int | None = Field(default=None, alias="maxSelections")
    min_selections: int | None = Field(default=None, alias="minSelections")
    creatable: bool | None = None
    default_value: str | list[str] | None = Field(default=None, alias="defaultValue")
    disabled: bool | None = None
    loading: bool | None = None
    virtualized: bool | None = None
    max_dropdown_height: int | None = Field(default=None, alias="maxDropdownHeight")

    model_config = {"populate_by_name": True}


# =============================================================================
# IMAGE
# =============================================================================


class ImageConfig(BaseModel):
    """Configuration for image widget."""

    src: str
    alt: str
    caption: str | None = None
    width: int | None = None
    height: int | None = None
    object_fit: ObjectFit | None = Field(default=None, alias="objectFit")
    zoomable: bool | None = None
    max_zoom: float | None = Field(default=None, alias="maxZoom")
    pannable: bool | None = None
    show_controls: bool | None = Field(default=None, alias="showControls")
    downloadable: bool | None = None
    fallback_src: str | None = Field(default=None, alias="fallbackSrc")
    lazy_load: bool | None = Field(default=None, alias="lazyLoad")
    border_radius: int | None = Field(default=None, alias="borderRadius")
    shadow: bool | None = None

    model_config = {"populate_by_name": True}


# =============================================================================
# VIDEO
# =============================================================================


class VideoCaption(BaseModel):
    """Caption track for video."""

    language: str
    label: str
    src: str


class VideoQuality(BaseModel):
    """Quality option for video."""

    label: str
    src: str


class VideoChapter(BaseModel):
    """Chapter marker for video."""

    title: str
    start_time: float = Field(..., alias="startTime")

    model_config = {"populate_by_name": True}


class VideoCheckpointWidget(BaseModel):
    """Widget to display at video checkpoint."""

    widget_id: str = Field(..., alias="widgetId")
    widget_type: WidgetType = Field(..., alias="widgetType")
    config: Any

    model_config = {"populate_by_name": True}


class VideoCheckpoint(BaseModel):
    """Checkpoint in video timeline."""

    checkpoint_id: str = Field(..., alias="checkpointId")
    timestamp: float
    pause_on_reach: bool | None = Field(default=None, alias="pauseOnReach")
    required: bool | None = None
    widget: VideoCheckpointWidget | None = None
    action: str | None = None
    note: str | None = None

    model_config = {"populate_by_name": True}


class VideoControls(BaseModel):
    """Video player controls configuration."""

    play: bool | None = None
    pause: bool | None = None
    seek: bool | None = None
    volume: bool | None = None
    fullscreen: bool | None = None
    playback_speed: bool | None = Field(default=None, alias="playbackSpeed")
    captions: bool | None = None
    quality: bool | None = None

    model_config = {"populate_by_name": True}


class VideoConfig(BaseModel):
    """Configuration for video widget."""

    src: str
    poster: str | None = None
    title: str | None = None
    duration: float | None = None
    autoplay: bool | None = None
    muted: bool | None = None
    loop: bool | None = None
    controls: VideoControls | None = None
    playback_speeds: list[float] | None = Field(default=None, alias="playbackSpeeds")
    captions: list[VideoCaption] | None = None
    qualities: list[VideoQuality] | None = None
    checkpoints: list[VideoCheckpoint] | None = None
    chapters: list[VideoChapter] | None = None
    required_watch_percentage: float | None = Field(default=None, alias="requiredWatchPercentage")
    prevent_skip_ahead: bool | None = Field(default=None, alias="preventSkipAhead")
    track_progress: bool | None = Field(default=None, alias="trackProgress")

    model_config = {"populate_by_name": True}


# =============================================================================
# STICKY NOTE
# =============================================================================


class StickyNoteStyle(BaseModel):
    """Styling for sticky note widget."""

    background_color: str | None = Field(default=None, alias="backgroundColor")
    text_color: str | None = Field(default=None, alias="textColor")
    font_size: int | None = Field(default=None, alias="fontSize")
    font_family: str | None = Field(default=None, alias="fontFamily")
    shadow: bool | None = None
    rotation: int | None = None

    model_config = {"populate_by_name": True}


class StickyNoteConfig(BaseModel):
    """Configuration for sticky_note widget."""

    content: str
    editable: bool | None = None
    max_length: int | None = Field(default=None, alias="maxLength")
    placeholder: str | None = None
    style: StickyNoteStyle | None = None
    show_timestamp: bool | None = Field(default=None, alias="showTimestamp")
    show_author: bool | None = Field(default=None, alias="showAuthor")
    author: str | None = None
    created_at: str | None = Field(default=None, alias="createdAt")
    pinned: bool | None = None
    minimizable: bool | None = None
    minimized: bool | None = None

    model_config = {"populate_by_name": True}
