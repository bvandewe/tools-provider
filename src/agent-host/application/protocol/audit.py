"""
Agent Host WebSocket Protocol v1.0.0 - Audit Types

Audit and telemetry message payloads.
"""

from typing import Any

from pydantic import BaseModel, Field

from .enums import AuditElementType, AuditEventType, AuditStatus

# =============================================================================
# AUDIT CONFIGURATION
# =============================================================================


class AuditConfig(BaseModel):
    """Configuration for audit/telemetry tracking."""

    enabled: bool = False
    capture_keystrokes: bool = Field(default=False, alias="captureKeystrokes")
    capture_mouse_clicks: bool = Field(default=False, alias="captureMouseClicks")
    capture_mouse_position: bool = Field(default=False, alias="captureMousePosition")
    capture_focus_changes: bool = Field(default=True, alias="captureFocusChanges")
    capture_clipboard: bool = Field(default=False, alias="captureClipboard")
    batch_interval_ms: int = Field(default=1000, alias="batchIntervalMs")
    exclude_widget_types: list[str] = Field(default_factory=list, alias="excludeWidgetTypes")

    model_config = {"populate_by_name": True}


# =============================================================================
# AUDIT ELEMENT CONTEXT
# =============================================================================


class AuditElementRegion(BaseModel):
    """Region bounds for audit element."""

    x: float
    y: float
    width: float
    height: float


class AuditElementContext(BaseModel):
    """Context about which element was involved in an audit event."""

    type: AuditElementType
    widget_id: str | None = Field(default=None, alias="widgetId")
    widget_type: str | None = Field(default=None, alias="widgetType")
    item_id: str | None = Field(default=None, alias="itemId")
    region: AuditElementRegion | None = None

    model_config = {"populate_by_name": True}


# =============================================================================
# AUDIT EVENTS
# =============================================================================


class AuditEvent(BaseModel):
    """Individual audit event."""

    event_id: str = Field(..., alias="eventId")
    event_type: AuditEventType = Field(..., alias="eventType")
    timestamp: str
    context: dict[str, Any]

    model_config = {"populate_by_name": True}


# =============================================================================
# AUDIT MESSAGE PAYLOADS
# =============================================================================


class AuditEventsPayload(BaseModel):
    """Batched audit events from frontend (Client → Server)."""

    user_id: str = Field(..., alias="userId")
    session_id: str = Field(..., alias="sessionId")
    batch_id: str = Field(..., alias="batchId")
    events: list[AuditEvent]

    model_config = {"populate_by_name": True}


class AuditAckPayload(BaseModel):
    """Acknowledge receipt of audit batch (Server → Client)."""

    batch_id: str = Field(..., alias="batchId")
    received_count: int = Field(..., alias="receivedCount")
    status: AuditStatus

    model_config = {"populate_by_name": True}


class AuditFlushPayload(BaseModel):
    """Request immediate flush of pending audit events (Server → Client)."""

    reason: str


class AuditFlushedPayload(BaseModel):
    """Confirm flush completed (Client → Server)."""

    pending_batches: int = Field(..., alias="pendingBatches")
    total_events_flushed: int = Field(..., alias="totalEventsFlushed")

    model_config = {"populate_by_name": True}


class AuditConfigUpdatePayload(BaseModel):
    """Update audit configuration mid-conversation (Server → Client)."""

    enabled: bool
    capture_keystrokes: bool | None = Field(default=None, alias="captureKeystrokes")
    capture_mouse_clicks: bool | None = Field(default=None, alias="captureMouseClicks")
    reason: str | None = None

    model_config = {"populate_by_name": True}
