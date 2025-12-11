"""Domain events for Session aggregate operations.

These events capture all state changes in the Session lifecycle,
following the CloudEvent specification for interoperability.

Event categories:
- Lifecycle events: Created, Started, Completed, Terminated, Expired
- Interaction events: ItemStarted, ItemCompleted
- UI state events: PendingActionSet, PendingActionCleared
- Response events: ResponseSubmitted
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from neuroglia.data.abstractions import DomainEvent
from neuroglia.eventing.cloud_events.decorators import cloudevent

# =============================================================================
# Session Lifecycle Events
# =============================================================================


@cloudevent("session.created.v1")
@dataclass
class SessionCreatedDomainEvent(DomainEvent):
    """Event raised when a new session is created."""

    aggregate_id: str
    user_id: str
    conversation_id: str
    session_type: str  # SessionType value
    control_mode: str  # ControlMode value
    system_prompt: str | None
    config: dict[str, Any]
    created_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        user_id: str,
        conversation_id: str,
        session_type: str,
        control_mode: str,
        system_prompt: str | None,
        config: dict[str, Any],
        created_at: datetime,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.user_id = user_id
        self.conversation_id = conversation_id
        self.session_type = session_type
        self.control_mode = control_mode
        self.system_prompt = system_prompt
        self.config = config
        self.created_at = created_at


@cloudevent("session.started.v1")
@dataclass
class SessionStartedDomainEvent(DomainEvent):
    """Event raised when a session is started (transitioned from PENDING to ACTIVE)."""

    aggregate_id: str
    started_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        started_at: datetime,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.started_at = started_at


@cloudevent("session.completed.v1")
@dataclass
class SessionCompletedDomainEvent(DomainEvent):
    """Event raised when a session is completed successfully."""

    aggregate_id: str
    completed_at: datetime
    completion_reason: str  # e.g., "criteria_met", "user_finished", "max_items_reached"
    summary: dict[str, Any] | None

    def __init__(
        self,
        aggregate_id: str,
        completed_at: datetime,
        completion_reason: str,
        summary: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.completed_at = completed_at
        self.completion_reason = completion_reason
        self.summary = summary


@cloudevent("session.terminated.v1")
@dataclass
class SessionTerminatedDomainEvent(DomainEvent):
    """Event raised when a session is manually terminated."""

    aggregate_id: str
    terminated_at: datetime
    reason: str

    def __init__(
        self,
        aggregate_id: str,
        terminated_at: datetime,
        reason: str,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.terminated_at = terminated_at
        self.reason = reason


@cloudevent("session.expired.v1")
@dataclass
class SessionExpiredDomainEvent(DomainEvent):
    """Event raised when a session expires due to timeout."""

    aggregate_id: str
    expired_at: datetime
    reason: str  # e.g., "time_limit", "item_timeout", "inactivity"

    def __init__(
        self,
        aggregate_id: str,
        expired_at: datetime,
        reason: str,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.expired_at = expired_at
        self.reason = reason


# =============================================================================
# Session Interaction Events
# =============================================================================


@cloudevent("session.item.started.v1")
@dataclass
class SessionItemStartedDomainEvent(DomainEvent):
    """Event raised when a new session item (question/prompt) is started."""

    aggregate_id: str
    item_id: str
    sequence: int
    agent_prompt: str
    client_action: dict[str, Any] | None
    started_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        item_id: str,
        sequence: int,
        agent_prompt: str,
        client_action: dict[str, Any] | None,
        started_at: datetime,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.item_id = item_id
        self.sequence = sequence
        self.agent_prompt = agent_prompt
        self.client_action = client_action
        self.started_at = started_at


@cloudevent("session.item.completed.v1")
@dataclass
class SessionItemCompletedDomainEvent(DomainEvent):
    """Event raised when a session item is completed (user responded)."""

    aggregate_id: str
    item_id: str
    user_response: dict[str, Any]
    response_time_ms: float | None
    evaluation: dict[str, Any] | None
    completed_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        item_id: str,
        user_response: dict[str, Any],
        response_time_ms: float | None,
        evaluation: dict[str, Any] | None,
        completed_at: datetime,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.item_id = item_id
        self.user_response = user_response
        self.response_time_ms = response_time_ms
        self.evaluation = evaluation
        self.completed_at = completed_at


# =============================================================================
# UI State Events
# =============================================================================


@cloudevent("session.pending_action.set.v1")
@dataclass
class PendingActionSetDomainEvent(DomainEvent):
    """Event raised when a pending client action is set (waiting for user input)."""

    aggregate_id: str
    tool_call_id: str
    tool_name: str
    widget_type: str
    props: dict[str, Any]
    lock_input: bool
    set_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        tool_call_id: str,
        tool_name: str,
        widget_type: str,
        props: dict[str, Any],
        lock_input: bool,
        set_at: datetime,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.tool_call_id = tool_call_id
        self.tool_name = tool_name
        self.widget_type = widget_type
        self.props = props
        self.lock_input = lock_input
        self.set_at = set_at


@cloudevent("session.pending_action.cleared.v1")
@dataclass
class PendingActionClearedDomainEvent(DomainEvent):
    """Event raised when a pending client action is cleared (after response received)."""

    aggregate_id: str
    tool_call_id: str
    cleared_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        tool_call_id: str,
        cleared_at: datetime,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.tool_call_id = tool_call_id
        self.cleared_at = cleared_at


# =============================================================================
# Response Events
# =============================================================================


@cloudevent("session.response.submitted.v1")
@dataclass
class ResponseSubmittedDomainEvent(DomainEvent):
    """Event raised when a user submits a response to a client action."""

    aggregate_id: str
    tool_call_id: str
    response: Any
    validation_status: str  # ValidationStatus value
    validation_errors: list[str] | None
    submitted_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        tool_call_id: str,
        response: Any,
        validation_status: str,
        validation_errors: list[str] | None,
        submitted_at: datetime,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.tool_call_id = tool_call_id
        self.response = response
        self.validation_status = validation_status
        self.validation_errors = validation_errors
        self.submitted_at = submitted_at


# =============================================================================
# Status Change Event
# =============================================================================


@cloudevent("session.status.changed.v1")
@dataclass
class SessionStatusChangedDomainEvent(DomainEvent):
    """Event raised when session status changes."""

    aggregate_id: str
    old_status: str
    new_status: str
    changed_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        old_status: str,
        new_status: str,
        changed_at: datetime,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.old_status = old_status
        self.new_status = new_status
        self.changed_at = changed_at
