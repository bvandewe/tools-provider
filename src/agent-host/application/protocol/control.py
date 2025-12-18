"""
Agent Host WebSocket Protocol v1.0.0 - Control Plane Messages

Control plane payloads for conversation, item, widget, flow, and navigation.
"""

from typing import Any

from pydantic import BaseModel, Field

from .audit import AuditConfig
from .core import Dimensions, Position
from .enums import (
    AnchorPosition,
    ConditionEffect,
    ConditionOperator,
    DismissAction,
    DisplayMode,
    ItemTimeoutAction,
    ItemTimerMode,
    WidgetCompletionBehavior,
    WidgetState,
)

# =============================================================================
# CONVERSATION-LEVEL CONTROLS
# =============================================================================


class ConversationConfigPayload(BaseModel):
    """Sent at conversation start to configure overall behavior."""

    template_id: str = Field(..., alias="templateId")
    template_name: str = Field(..., alias="templateName")
    total_items: int = Field(..., alias="totalItems")
    display_mode: DisplayMode = Field(..., alias="displayMode")
    show_conversation_history: bool = Field(..., alias="showConversationHistory")
    allow_backward_navigation: bool = Field(..., alias="allowBackwardNavigation")
    allow_concurrent_item_widgets: bool = Field(default=False, alias="allowConcurrentItemWidgets")
    allow_skip: bool = Field(..., alias="allowSkip")
    enable_chat_input_initially: bool = Field(..., alias="enableChatInputInitially")
    display_progress_indicator: bool = Field(..., alias="displayProgressIndicator")
    display_final_score_report: bool = Field(..., alias="displayFinalScoreReport")
    continue_after_completion: bool = Field(..., alias="continueAfterCompletion")
    item_timer_mode: ItemTimerMode | None = Field(default=None, alias="itemTimerMode")
    audit: AuditConfig | None = None

    model_config = {"populate_by_name": True}


class FlowConfig(BaseModel):
    """Configuration for flow mode (1D)."""

    behavior: DisplayMode
    max_visible_messages: int | None = Field(default=None, alias="maxVisibleMessages")
    auto_scroll: bool = Field(default=True, alias="autoScroll")

    model_config = {"populate_by_name": True}


class CanvasConfig(BaseModel):
    """Configuration for canvas mode (2D)."""

    width: int
    height: int
    background: str
    grid_enabled: bool = Field(..., alias="gridEnabled")
    grid_size: int = Field(..., alias="gridSize")
    snap_to_grid: bool = Field(..., alias="snapToGrid")
    min_zoom: float = Field(..., alias="minZoom")
    max_zoom: float = Field(..., alias="maxZoom")
    initial_zoom: float = Field(..., alias="initialZoom")
    initial_viewport: Position = Field(..., alias="initialViewport")

    model_config = {"populate_by_name": True}


class ConversationDisplayPayload(BaseModel):
    """Configure the display mode for the conversation."""

    mode: str  # "flow" | "canvas"
    flow_config: FlowConfig | None = Field(default=None, alias="flowConfig")
    canvas_config: CanvasConfig | None = Field(default=None, alias="canvasConfig")

    model_config = {"populate_by_name": True}


class ConversationDeadlinePayload(BaseModel):
    """Sets or updates the conversation-level deadline."""

    deadline: str
    show_warning: bool | None = Field(default=None, alias="showWarning")
    warning_threshold_seconds: int | None = Field(default=None, alias="warningThresholdSeconds")

    model_config = {"populate_by_name": True}


class ConversationPausePayload(BaseModel):
    """Server-initiated pause."""

    reason: str
    paused_at: str = Field(..., alias="pausedAt")

    model_config = {"populate_by_name": True}


# =============================================================================
# ITEM-LEVEL CONTROLS
# =============================================================================


class ItemContextPayload(BaseModel):
    """Sent when advancing to a new template item."""

    item_id: str = Field(..., alias="itemId")
    item_index: int = Field(..., alias="itemIndex")
    total_items: int = Field(..., alias="totalItems")
    item_title: str | None = Field(default=None, alias="itemTitle")
    enable_chat_input: bool = Field(..., alias="enableChatInput")
    time_limit_seconds: int | None = Field(default=None, alias="timeLimitSeconds")
    show_remaining_time: bool = Field(..., alias="showRemainingTime")
    widget_completion_behavior: WidgetCompletionBehavior = Field(..., alias="widgetCompletionBehavior")
    conversation_deadline: str | None = Field(default=None, alias="conversationDeadline")

    model_config = {"populate_by_name": True}


class ItemScorePayload(BaseModel):
    """Optional score feedback after item completion."""

    item_id: str = Field(..., alias="itemId")
    score: float
    max_score: float = Field(..., alias="maxScore")
    feedback: str | None = None
    correct_answer: str | None = Field(default=None, alias="correctAnswer")

    model_config = {"populate_by_name": True}


class ItemTimeoutPayload(BaseModel):
    """Sent when item time limit expires (Server → Client)."""

    item_id: str = Field(..., alias="itemId")
    action: ItemTimeoutAction

    model_config = {"populate_by_name": True}


class ItemExpiredPayload(BaseModel):
    """Item timer expired (Client → Server)."""

    item_id: str = Field(..., alias="itemId")
    expired_at: str = Field(..., alias="expiredAt")

    model_config = {"populate_by_name": True}


# =============================================================================
# WIDGET-LEVEL CONTROLS
# =============================================================================


class WidgetLayout(BaseModel):
    """Widget layout configuration."""

    mode: str  # "flow" | "canvas"
    position: Position | None = None
    dimensions: Dimensions | None = None
    anchor: AnchorPosition = "top-left"
    z_index: int | None = Field(default=None, alias="zIndex")

    model_config = {"populate_by_name": True}


class WidgetStatePayload(BaseModel):
    """Controls the interactive state of a widget."""

    widget_id: str = Field(..., alias="widgetId")
    state: WidgetState
    clear_value: bool | None = Field(default=None, alias="clearValue")
    reason: str | None = None

    model_config = {"populate_by_name": True}


class WidgetFocusPayload(BaseModel):
    """Request focus on a specific widget."""

    widget_id: str = Field(..., alias="widgetId")
    highlight: bool | None = None
    scroll_into_view: bool | None = Field(default=None, alias="scrollIntoView")

    model_config = {"populate_by_name": True}


class WidgetValidationPayload(BaseModel):
    """Display validation error on a widget."""

    widget_id: str = Field(..., alias="widgetId")
    valid: bool
    message: str | None = None
    details: dict[str, Any] | None = None

    model_config = {"populate_by_name": True}


class WidgetLayoutPayload(BaseModel):
    """Update a widget's position, size, or constraints on the canvas."""

    widget_id: str = Field(..., alias="widgetId")
    layout: WidgetLayout
    animate: bool | None = None
    animation_duration: int | None = Field(default=None, alias="animationDuration")

    model_config = {"populate_by_name": True}


class WidgetMovedPayload(BaseModel):
    """Notify server when user moves a widget on canvas."""

    widget_id: str = Field(..., alias="widgetId")
    position: Position

    model_config = {"populate_by_name": True}


class WidgetResizedPayload(BaseModel):
    """Notify server when user resizes a widget on canvas."""

    widget_id: str = Field(..., alias="widgetId")
    dimensions: Dimensions

    model_config = {"populate_by_name": True}


class WidgetDismissedPayload(BaseModel):
    """Notify server when user dismisses a widget."""

    widget_id: str = Field(..., alias="widgetId")
    action: DismissAction

    model_config = {"populate_by_name": True}


class WidgetCondition(BaseModel):
    """Condition for widget visibility/state."""

    source_widget: str = Field(..., alias="sourceWidget")
    operator: ConditionOperator
    value: Any
    effect: ConditionEffect

    model_config = {"populate_by_name": True}


class WidgetConditionPayload(BaseModel):
    """Set visibility/state condition for a widget."""

    widget_id: str = Field(..., alias="widgetId")
    conditions: list[WidgetCondition]
    default_state: WidgetState = Field(..., alias="defaultState")
    evaluate_on: str = Field(..., alias="evaluateOn")  # "submit" | "change"

    model_config = {"populate_by_name": True}


# =============================================================================
# FLOW & NAVIGATION CONTROLS
# =============================================================================


class FlowStartPayload(BaseModel):
    """Start the conversation/template flow (proactive agent)."""

    pass


class FlowPausePayload(BaseModel):
    """User-initiated pause."""

    reason: str


class FlowCancelPayload(BaseModel):
    """Cancel the current operation."""

    request_id: str | None = Field(default=None, alias="requestId")

    model_config = {"populate_by_name": True}


class NavigationPayload(BaseModel):
    """Navigation between items."""

    current_item_id: str | None = Field(default=None, alias="currentItemId")
    item_id: str | None = Field(default=None, alias="itemId")
    reason: str | None = None

    model_config = {"populate_by_name": True}
