"""
Agent Host WebSocket Protocol v1.0.0 - Widget Response Values

Response value types for all widget types.
"""

from typing import Any

from pydantic import BaseModel, Field

from ..core import Position, Region
from ..enums import DrawingFormat

# =============================================================================
# SIMPLE VALUES (type aliases)
# =============================================================================

# Multiple choice: string | list[str]
# Free text: str
# Code editor: str
# Slider: float
# Rating: float
# Date picker: str | DateRangeValue
# Dropdown: str | list[str]


# =============================================================================
# DRAG & DROP VALUES
# =============================================================================


class DragDropCategoryValue(BaseModel):
    """Response value for category drag & drop."""

    # Zone ID -> list of item IDs
    __root__: dict[str, list[str]] | None = None

    model_config = {"extra": "allow"}


class DragDropPlacement(BaseModel):
    """Individual placement for graphical drag & drop."""

    placeholder_id: str = Field(..., alias="placeholderId")
    item_id: str = Field(..., alias="itemId")

    model_config = {"populate_by_name": True}


class DragDropFreePosition(BaseModel):
    """Free position for graphical drag & drop."""

    item_id: str = Field(..., alias="itemId")
    position: Position

    model_config = {"populate_by_name": True}


class DragDropGraphicalValue(BaseModel):
    """Response value for graphical drag & drop."""

    placements: list[DragDropPlacement]
    free_positions: list[DragDropFreePosition] | None = Field(default=None, alias="freePositions")

    model_config = {"populate_by_name": True}


# =============================================================================
# GRAPH TOPOLOGY VALUE
# =============================================================================


class GraphTopologyNode(BaseModel):
    """Node in graph topology response."""

    node_id: str = Field(..., alias="nodeId")
    type_id: str = Field(..., alias="typeId")
    position: Position
    properties: dict[str, Any]

    model_config = {"populate_by_name": True}


class GraphTopologyEdge(BaseModel):
    """Edge in graph topology response."""

    edge_id: str = Field(..., alias="edgeId")
    type_id: str = Field(..., alias="typeId")
    source_node_id: str = Field(..., alias="sourceNodeId")
    target_node_id: str = Field(..., alias="targetNodeId")

    model_config = {"populate_by_name": True}


class GraphTopologyRegionValue(BaseModel):
    """Region in graph topology response."""

    region_id: str = Field(..., alias="regionId")
    type_id: str = Field(..., alias="typeId")
    bounds: Region
    contained_nodes: list[str] = Field(..., alias="containedNodes")

    model_config = {"populate_by_name": True}


class GraphTopologyValue(BaseModel):
    """Response value for graph_topology widget."""

    nodes: list[GraphTopologyNode]
    edges: list[GraphTopologyEdge]
    regions: list[GraphTopologyRegionValue] | None = None


# =============================================================================
# MATRIX CHOICE VALUE
# =============================================================================


class MatrixChoiceValue(BaseModel):
    """Response value for matrix_choice widget."""

    selections: dict[str, list[str]]  # Row ID -> list of column IDs


# =============================================================================
# DOCUMENT VIEWER VALUE
# =============================================================================


class DocumentViewerHighlight(BaseModel):
    """User highlight in document."""

    section_id: str = Field(..., alias="sectionId")
    text: str
    color: str

    model_config = {"populate_by_name": True}


class EmbeddedResponse(BaseModel):
    """Response from embedded widget."""

    value: Any


class DocumentViewerValue(BaseModel):
    """Response value for document_viewer widget."""

    read_sections: list[str] = Field(..., alias="readSections")
    time_spent: int = Field(..., alias="timeSpent")
    highlights: list[DocumentViewerHighlight] | None = None
    embedded_responses: dict[str, EmbeddedResponse] | None = Field(default=None, alias="embeddedResponses")

    model_config = {"populate_by_name": True}


# =============================================================================
# HOTSPOT VALUE
# =============================================================================


class HotspotValue(BaseModel):
    """Response value for hotspot widget."""

    selected_regions: list[str] = Field(..., alias="selectedRegions")

    model_config = {"populate_by_name": True}


# =============================================================================
# DRAWING VALUE
# =============================================================================


class DrawingValue(BaseModel):
    """Response value for drawing widget."""

    format: DrawingFormat
    data: str  # SVG string or encoded data
    png_base64: str | None = None


# =============================================================================
# FILE UPLOAD VALUE
# =============================================================================


class FileUploadFile(BaseModel):
    """Uploaded file metadata."""

    file_id: str = Field(..., alias="fileId")
    filename: str
    mime_type: str = Field(..., alias="mimeType")
    size: int
    uploaded_at: str = Field(..., alias="uploadedAt")
    url: str

    model_config = {"populate_by_name": True}


class FileUploadValue(BaseModel):
    """Response value for file_upload widget."""

    files: list[FileUploadFile]


# =============================================================================
# DATE RANGE VALUE
# =============================================================================


class DateRangeValue(BaseModel):
    """Response value for date_picker with mode="daterange"."""

    start: str
    end: str


# =============================================================================
# IMAGE VALUE
# =============================================================================


class ImageValue(BaseModel):
    """Response value for interactive image widget."""

    viewed: bool
    zoom_level: float | None = Field(default=None, alias="zoomLevel")
    view_duration: int | None = Field(default=None, alias="viewDuration")

    model_config = {"populate_by_name": True}


# =============================================================================
# VIDEO VALUE
# =============================================================================


class VideoPlaybackEvent(BaseModel):
    """Playback event for video analytics."""

    event: str  # "play" | "pause" | "seek" | etc.
    timestamp: float | None = None
    from_time: float | None = Field(default=None, alias="from")
    to_time: float | None = Field(default=None, alias="to")
    time: str  # ISO timestamp

    model_config = {"populate_by_name": True}


class VideoValue(BaseModel):
    """Response value for video widget."""

    watched_percentage: float = Field(..., alias="watchedPercentage")
    total_watch_time: float = Field(..., alias="totalWatchTime")
    completed_checkpoints: list[str] = Field(..., alias="completedCheckpoints")
    checkpoint_responses: dict[str, dict[str, Any]] | None = Field(default=None, alias="checkpointResponses")
    last_position: float = Field(..., alias="lastPosition")
    playback_events: list[VideoPlaybackEvent] | None = Field(default=None, alias="playbackEvents")

    model_config = {"populate_by_name": True}


# =============================================================================
# STICKY NOTE VALUE
# =============================================================================


class StickyNoteValue(BaseModel):
    """Response value for editable sticky_note widget."""

    content: str
    edited_at: str | None = Field(default=None, alias="editedAt")

    model_config = {"populate_by_name": True}
