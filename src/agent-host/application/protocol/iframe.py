"""
Agent Host WebSocket Protocol v1.0.0 - IFRAME Widget

Secure IFRAME widget with bidirectional communication.
"""

from typing import Any

from pydantic import BaseModel, Field

from .core import Dimensions, Position


class IframeSandboxConfig(BaseModel):
    """Sandbox restrictions for IFRAME."""

    allow_scripts: bool = Field(default=True, alias="allowScripts")
    allow_forms: bool = Field(default=False, alias="allowForms")
    allow_same_origin: bool = Field(default=False, alias="allowSameOrigin")
    allow_popups: bool = Field(default=False, alias="allowPopups")
    allow_modals: bool = Field(default=False, alias="allowModals")
    allow_downloads: bool = Field(default=False, alias="allowDownloads")

    model_config = {"populate_by_name": True}


class IframePermissionsConfig(BaseModel):
    """Feature permissions for IFRAME."""

    camera: bool = False
    microphone: bool = False
    geolocation: bool = False
    fullscreen: bool = False
    clipboard: bool = False
    payment: bool = False

    model_config = {"populate_by_name": True}


class IframeCommunicationConfig(BaseModel):
    """Communication settings for IFRAME."""

    origin: str
    allowed_events: list[str] | None = Field(default=None, alias="allowedEvents")
    allowed_commands: list[str] | None = Field(default=None, alias="allowedCommands")

    model_config = {"populate_by_name": True}


class IframeLoadingConfig(BaseModel):
    """Loading behavior for IFRAME."""

    strategy: str = "eager"  # "eager" | "lazy"
    show_spinner: bool = Field(default=True, alias="showSpinner")
    timeout: int | None = None
    retry_on_error: bool = Field(default=True, alias="retryOnError")
    max_retries: int = Field(default=3, alias="maxRetries")

    model_config = {"populate_by_name": True}


class IframeLayoutConfig(BaseModel):
    """Layout configuration for IFRAME."""

    position: Position
    dimensions: Dimensions
    min_dimensions: Dimensions | None = Field(default=None, alias="minDimensions")
    max_dimensions: Dimensions | None = Field(default=None, alias="maxDimensions")
    resizable: bool = False
    movable: bool = False
    z_index: int | None = Field(default=None, alias="zIndex")

    model_config = {"populate_by_name": True}


class IframeConfig(BaseModel):
    """Complete IFRAME widget configuration."""

    widget_id: str = Field(..., alias="widgetId")
    source: str
    title: str | None = None
    sandbox: IframeSandboxConfig | None = None
    permissions: IframePermissionsConfig | None = None
    communication: IframeCommunicationConfig | None = None
    loading: IframeLoadingConfig | None = None
    layout: IframeLayoutConfig | None = None
    initial_state: dict[str, Any] | None = Field(default=None, alias="initialState")

    model_config = {"populate_by_name": True}


# =============================================================================
# IFRAME EVENTS (IFRAME → Server via Client)
# =============================================================================


class IframeEventPayload(BaseModel):
    """Event from IFRAME content."""

    widget_id: str = Field(..., alias="widgetId")
    event_type: str = Field(..., alias="eventType")
    data: dict[str, Any]
    timestamp: str

    model_config = {"populate_by_name": True}


# =============================================================================
# IFRAME COMMANDS (Server → Client → IFRAME)
# =============================================================================


class IframeCommandPayload(BaseModel):
    """Send command to IFRAME."""

    widget_id: str = Field(..., alias="widgetId")
    command: str
    data: dict[str, Any] | None = None
    expect_response: bool = Field(default=False, alias="expectResponse")
    timeout: int | None = None

    model_config = {"populate_by_name": True}


# =============================================================================
# IFRAME STATE
# =============================================================================


class IframeStatePayload(BaseModel):
    """State synchronization for IFRAME."""

    widget_id: str = Field(..., alias="widgetId")
    state: dict[str, Any]

    model_config = {"populate_by_name": True}


# =============================================================================
# IFRAME LIFECYCLE
# =============================================================================


class IframeLoadedPayload(BaseModel):
    """IFRAME loaded notification."""

    widget_id: str = Field(..., alias="widgetId")
    load_time_ms: int = Field(..., alias="loadTimeMs")
    content_size: Dimensions | None = Field(default=None, alias="contentSize")

    model_config = {"populate_by_name": True}


class IframeErrorPayload(BaseModel):
    """IFRAME error notification."""

    widget_id: str = Field(..., alias="widgetId")
    error_type: str = Field(..., alias="errorType")  # "load" | "timeout" | "security" | "communication"
    error_message: str = Field(..., alias="errorMessage")
    recoverable: bool

    model_config = {"populate_by_name": True}


class IframeResizePayload(BaseModel):
    """IFRAME resize request from content."""

    widget_id: str = Field(..., alias="widgetId")
    requested_size: Dimensions = Field(..., alias="requestedSize")
    allow_auto_resize: bool = Field(default=True, alias="allowAutoResize")

    model_config = {"populate_by_name": True}
