"""
Agent Host WebSocket Protocol v1.0.0 - Widget Base Types

Base types for the widget system.
"""

from typing import Any

from pydantic import BaseModel, Field

from ..core import Dimensions, Position
from ..enums import AnchorPosition, DismissAction, WidgetType

# =============================================================================
# WIDGET LAYOUT
# =============================================================================


class WidgetLayout(BaseModel):
    """Widget layout configuration."""

    mode: str  # "flow" | "canvas"
    position: Position | None = None
    dimensions: Dimensions | None = None
    anchor: AnchorPosition = "top-left"
    z_index: int | None = Field(default=None, alias="zIndex")

    model_config = {"populate_by_name": True}


# =============================================================================
# WIDGET CONSTRAINTS
# =============================================================================


class WidgetConstraints(BaseModel):
    """Controls what users can do with a widget."""

    moveable: bool = False
    resizable: bool = False
    dismissable: bool = False
    dismiss_action: DismissAction = Field(default="hide", alias="dismissAction")
    selectable: bool | None = None
    connectable: bool | None = None

    model_config = {"populate_by_name": True}


# =============================================================================
# WIDGET RENDER PAYLOAD
# =============================================================================


class WidgetRenderPayload(BaseModel):
    """Server requests rendering of a widget."""

    item_id: str = Field(..., alias="itemId")
    widget_id: str = Field(..., alias="widgetId")
    widget_type: WidgetType = Field(..., alias="widgetType")
    stem: str | None = None
    config: Any  # Widget-specific config
    required: bool = True
    skippable: bool | None = None
    initial_value: Any | None = Field(default=None, alias="initialValue")
    show_user_response: bool | None = Field(default=None, alias="showUserResponse")
    layout: WidgetLayout
    constraints: WidgetConstraints

    model_config = {"populate_by_name": True}
