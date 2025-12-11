"""Session aggregate definition using the AggregateState pattern.

The Session aggregate manages proactive/reactive interactions with users.
It wraps a Conversation (via composition) and adds:
- Session lifecycle management
- UI state for widget rendering
- Interaction tracking (SessionItems)
- Pending action state for client tools

DomainEvents are appended/aggregated in the Session and the
repository publishes them via Mediator after the Session was persisted.
"""

from datetime import UTC, datetime
from typing import Any, cast
from uuid import uuid4

from multipledispatch import dispatch
from neuroglia.data.abstractions import AggregateRoot, AggregateState
from neuroglia.mapping.mapper import map_to

from domain.events.session import (
    PendingActionClearedDomainEvent,
    PendingActionSetDomainEvent,
    ResponseSubmittedDomainEvent,
    SessionCompletedDomainEvent,
    SessionCreatedDomainEvent,
    SessionExpiredDomainEvent,
    SessionItemCompletedDomainEvent,
    SessionItemStartedDomainEvent,
    SessionStartedDomainEvent,
    SessionStatusChangedDomainEvent,
    SessionTerminatedDomainEvent,
)
from domain.models.session_models import (
    ClientAction,
    ClientResponse,
    ControlMode,
    SessionConfig,
    SessionItem,
    SessionStatus,
    SessionType,
    UiState,
    get_control_mode_for_session_type,
    get_default_config_for_session_type,
)
from integration.models.session_dto import SessionDto


class DomainError(Exception):
    """Exception raised for domain rule violations."""

    pass


@map_to(SessionDto)
class SessionState(AggregateState[str]):
    """Encapsulates the persisted state for the Session aggregate."""

    # Identity
    id: str
    user_id: str
    conversation_id: str

    # Configuration
    session_type: SessionType
    control_mode: ControlMode
    system_prompt: str | None
    config: dict[str, Any]

    # Status
    status: SessionStatus

    # Items
    current_item_id: str | None
    items: list[dict[str, Any]]

    # UI State
    ui_state: dict[str, Any]
    pending_action: dict[str, Any] | None

    # Audit
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    terminated_reason: str | None

    def __init__(self) -> None:
        super().__init__()
        self.id = ""
        self.user_id = ""
        self.conversation_id = ""
        self.session_type = SessionType.THOUGHT
        self.control_mode = ControlMode.REACTIVE
        self.system_prompt = None
        self.config = {}
        self.status = SessionStatus.PENDING
        self.current_item_id = None
        self.items = []
        self.ui_state = UiState().to_dict()
        self.pending_action = None

        now = datetime.now(UTC)
        self.created_at = now
        self.started_at = None
        self.completed_at = None
        self.terminated_reason = None

    # =========================================================================
    # Event Handlers
    # =========================================================================

    @dispatch(SessionCreatedDomainEvent)
    def on(self, event: SessionCreatedDomainEvent) -> None:  # type: ignore[override]
        """Apply the creation event to the state."""
        self.id = event.aggregate_id
        self.user_id = event.user_id
        self.conversation_id = event.conversation_id
        self.session_type = SessionType(event.session_type)
        self.control_mode = ControlMode(event.control_mode)
        self.system_prompt = event.system_prompt
        self.config = event.config
        self.status = SessionStatus.PENDING
        self.created_at = event.created_at

    @dispatch(SessionStartedDomainEvent)
    def on(self, event: SessionStartedDomainEvent) -> None:  # type: ignore[override]
        """Apply the started event to the state."""
        self.status = SessionStatus.ACTIVE
        self.started_at = event.started_at

    @dispatch(SessionCompletedDomainEvent)
    def on(self, event: SessionCompletedDomainEvent) -> None:  # type: ignore[override]
        """Apply the completed event to the state."""
        self.status = SessionStatus.COMPLETED
        self.completed_at = event.completed_at
        self.pending_action = None

    @dispatch(SessionTerminatedDomainEvent)
    def on(self, event: SessionTerminatedDomainEvent) -> None:  # type: ignore[override]
        """Apply the terminated event to the state."""
        self.status = SessionStatus.TERMINATED
        self.completed_at = event.terminated_at
        self.terminated_reason = event.reason
        self.pending_action = None

    @dispatch(SessionExpiredDomainEvent)
    def on(self, event: SessionExpiredDomainEvent) -> None:  # type: ignore[override]
        """Apply the expired event to the state."""
        self.status = SessionStatus.EXPIRED
        self.completed_at = event.expired_at
        self.terminated_reason = event.reason
        self.pending_action = None

    @dispatch(SessionStatusChangedDomainEvent)
    def on(self, event: SessionStatusChangedDomainEvent) -> None:  # type: ignore[override]
        """Apply the status changed event to the state."""
        self.status = SessionStatus(event.new_status)

    @dispatch(SessionItemStartedDomainEvent)
    def on(self, event: SessionItemStartedDomainEvent) -> None:  # type: ignore[override]
        """Apply the item started event to the state."""
        item_data = {
            "id": event.item_id,
            "sequence": event.sequence,
            "started_at": event.started_at.isoformat(),
            "completed_at": None,
            "agent_prompt": event.agent_prompt,
            "client_action": event.client_action,
            "user_response": None,
            "response_time_ms": None,
            "evaluation": None,
        }
        self.items.append(item_data)
        self.current_item_id = event.item_id

    @dispatch(SessionItemCompletedDomainEvent)
    def on(self, event: SessionItemCompletedDomainEvent) -> None:  # type: ignore[override]
        """Apply the item completed event to the state."""
        for item in self.items:
            if item["id"] == event.item_id:
                item["completed_at"] = event.completed_at.isoformat()
                item["user_response"] = event.user_response
                item["response_time_ms"] = event.response_time_ms
                item["evaluation"] = event.evaluation
                break

    @dispatch(PendingActionSetDomainEvent)
    def on(self, event: PendingActionSetDomainEvent) -> None:  # type: ignore[override]
        """Apply the pending action set event to the state."""
        self.pending_action = {
            "tool_call_id": event.tool_call_id,
            "tool_name": event.tool_name,
            "widget_type": event.widget_type,
            "props": event.props,
            "lock_input": event.lock_input,
        }
        self.status = SessionStatus.AWAITING_CLIENT_ACTION
        # Update UI state
        ui_state = UiState.from_dict(self.ui_state)
        ui_state.chat_input_locked = event.lock_input
        ui_state.active_widget = ClientAction.from_dict(self.pending_action)
        self.ui_state = ui_state.to_dict()

    @dispatch(PendingActionClearedDomainEvent)
    def on(self, event: PendingActionClearedDomainEvent) -> None:  # type: ignore[override]
        """Apply the pending action cleared event to the state."""
        self.pending_action = None
        self.status = SessionStatus.ACTIVE
        # Update UI state
        ui_state = UiState.from_dict(self.ui_state)
        ui_state.chat_input_locked = False
        ui_state.active_widget = None
        ui_state.widget_partial_state = None
        self.ui_state = ui_state.to_dict()

    @dispatch(ResponseSubmittedDomainEvent)
    def on(self, event: ResponseSubmittedDomainEvent) -> None:  # type: ignore[override]
        """Apply the response submitted event to the state."""
        # Response is stored in the item, this event is mainly for audit
        pass


class Session(AggregateRoot[SessionState, str]):
    """Session aggregate root managing proactive/reactive interactions.

    A Session wraps a Conversation and adds:
    - Structured interaction management (SessionItems)
    - Client-side widget state (pending actions)
    - UI state for restoration
    - Session-specific configuration

    State transitions:
    - create() -> PENDING
    - start() -> ACTIVE
    - set_pending_action() -> AWAITING_CLIENT_ACTION
    - submit_response() -> ACTIVE
    - complete() -> COMPLETED
    - terminate() -> TERMINATED
    - expire() -> EXPIRED
    """

    def __init__(
        self,
        user_id: str,
        conversation_id: str,
        session_type: SessionType,
        system_prompt: str | None = None,
        config: SessionConfig | None = None,
        created_at: datetime | None = None,
        session_id: str | None = None,
    ) -> None:
        """Create a new Session.

        Args:
            user_id: The user who owns this session
            conversation_id: The linked Conversation aggregate ID
            session_type: Type of session (determines behavior)
            system_prompt: Optional custom system prompt
            config: Optional custom configuration (uses defaults if None)
            created_at: Optional creation timestamp (defaults to now)
            session_id: Optional specific ID (generates UUID if None)
        """
        super().__init__()
        aggregate_id = session_id or str(uuid4())
        created_time = created_at or datetime.now(UTC)

        # Get control mode and default config for session type
        control_mode = get_control_mode_for_session_type(session_type)
        session_config = config or get_default_config_for_session_type(session_type)

        self.state.on(
            self.register_event(  # type: ignore
                SessionCreatedDomainEvent(
                    aggregate_id=aggregate_id,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    session_type=session_type.value,
                    control_mode=control_mode.value,
                    system_prompt=system_prompt,
                    config=session_config.to_dict(),
                    created_at=created_time,
                )
            )
        )

    def id(self) -> str:
        """Return the aggregate identifier with a precise type."""
        aggregate_id = super().id()
        if aggregate_id is None:
            raise ValueError("Session aggregate identifier has not been initialized")
        return cast(str, aggregate_id)

    # =========================================================================
    # Commands
    # =========================================================================

    def start(self) -> None:
        """Start the session, transitioning from PENDING to ACTIVE.

        Raises:
            DomainError: If session is not in PENDING status
        """
        if self.state.status != SessionStatus.PENDING:
            raise DomainError(f"Cannot start session in status {self.state.status.value}")

        self.state.on(
            self.register_event(  # type: ignore
                SessionStartedDomainEvent(
                    aggregate_id=self.id(),
                    started_at=datetime.now(UTC),
                )
            )
        )

    def start_item(
        self,
        agent_prompt: str,
        client_action: ClientAction | None = None,
    ) -> SessionItem:
        """Start a new session item (question/prompt).

        Args:
            agent_prompt: The text content the agent is presenting
            client_action: Optional client-side widget to render

        Returns:
            The created SessionItem

        Raises:
            DomainError: If session is not active
        """
        if self.state.status not in (SessionStatus.ACTIVE, SessionStatus.AWAITING_CLIENT_ACTION):
            raise DomainError(f"Cannot start item in session status {self.state.status.value}")

        now = datetime.now(UTC)
        item = SessionItem.create(
            sequence=len(self.state.items) + 1,
            agent_prompt=agent_prompt,
            client_action=client_action,
            started_at=now,
        )

        self.state.on(
            self.register_event(  # type: ignore
                SessionItemStartedDomainEvent(
                    aggregate_id=self.id(),
                    item_id=item.id,
                    sequence=item.sequence,
                    agent_prompt=agent_prompt,
                    client_action=client_action.to_dict() if client_action else None,
                    started_at=now,
                )
            )
        )

        return item

    def set_pending_action(self, action: ClientAction) -> None:
        """Set a pending client action (widget awaiting user input).

        This transitions the session to AWAITING_CLIENT_ACTION status.

        Args:
            action: The client action to set as pending

        Raises:
            DomainError: If session is not active
        """
        if self.state.status != SessionStatus.ACTIVE:
            raise DomainError(f"Cannot set pending action in session status {self.state.status.value}")

        self.state.on(
            self.register_event(  # type: ignore
                PendingActionSetDomainEvent(
                    aggregate_id=self.id(),
                    tool_call_id=action.tool_call_id,
                    tool_name=action.tool_name,
                    widget_type=action.widget_type,
                    props=action.props,
                    lock_input=action.lock_input,
                    set_at=datetime.now(UTC),
                )
            )
        )

    def submit_response(
        self,
        response: ClientResponse,
        evaluation: dict[str, Any] | None = None,
    ) -> SessionItem | None:
        """Submit a user's response to a pending client action.

        This clears the pending action and completes the current item.

        Args:
            response: The user's response data
            evaluation: Optional evaluation/scoring data

        Returns:
            The completed SessionItem, or None if no current item

        Raises:
            DomainError: If no pending action or response doesn't match
        """
        if self.state.status != SessionStatus.AWAITING_CLIENT_ACTION:
            raise DomainError(f"Cannot submit response in session status {self.state.status.value}")

        if self.state.pending_action is None:
            raise DomainError("No pending action to respond to")

        pending_tool_call_id = self.state.pending_action["tool_call_id"]
        if response.tool_call_id != pending_tool_call_id:
            raise DomainError(f"Response tool_call_id {response.tool_call_id} does not match pending action {pending_tool_call_id}")

        now = datetime.now(UTC)

        # Register response submitted event
        self.state.on(
            self.register_event(  # type: ignore
                ResponseSubmittedDomainEvent(
                    aggregate_id=self.id(),
                    tool_call_id=response.tool_call_id,
                    response=response.response,
                    validation_status=response.validation_status.value,
                    validation_errors=response.validation_errors,
                    submitted_at=now,
                )
            )
        )

        # Complete the current item if exists
        current_item = self.get_current_item()
        if current_item:
            # Calculate response time
            response_time_ms = None
            if current_item.started_at:
                delta = now - current_item.started_at
                response_time_ms = delta.total_seconds() * 1000

            self.state.on(
                self.register_event(  # type: ignore
                    SessionItemCompletedDomainEvent(
                        aggregate_id=self.id(),
                        item_id=current_item.id,
                        user_response=response.to_dict(),
                        response_time_ms=response_time_ms,
                        evaluation=evaluation,
                        completed_at=now,
                    )
                )
            )

        # Clear pending action
        self.state.on(
            self.register_event(  # type: ignore
                PendingActionClearedDomainEvent(
                    aggregate_id=self.id(),
                    tool_call_id=response.tool_call_id,
                    cleared_at=now,
                )
            )
        )

        return current_item

    def complete(self, reason: str = "completed", summary: dict[str, Any] | None = None) -> None:
        """Complete the session successfully.

        Args:
            reason: The completion reason
            summary: Optional summary data

        Raises:
            DomainError: If session cannot be completed
        """
        if self.state.status in (SessionStatus.COMPLETED, SessionStatus.TERMINATED, SessionStatus.EXPIRED):
            raise DomainError(f"Cannot complete session in status {self.state.status.value}")

        self.state.on(
            self.register_event(  # type: ignore
                SessionCompletedDomainEvent(
                    aggregate_id=self.id(),
                    completed_at=datetime.now(UTC),
                    completion_reason=reason,
                    summary=summary,
                )
            )
        )

    def terminate(self, reason: str) -> None:
        """Manually terminate the session.

        Args:
            reason: The termination reason

        Raises:
            DomainError: If session is already completed/terminated
        """
        if self.state.status in (SessionStatus.COMPLETED, SessionStatus.TERMINATED, SessionStatus.EXPIRED):
            raise DomainError(f"Cannot terminate session in status {self.state.status.value}")

        self.state.on(
            self.register_event(  # type: ignore
                SessionTerminatedDomainEvent(
                    aggregate_id=self.id(),
                    terminated_at=datetime.now(UTC),
                    reason=reason,
                )
            )
        )

    def expire(self, reason: str = "time_limit") -> None:
        """Mark the session as expired.

        Args:
            reason: The expiration reason (e.g., "time_limit", "inactivity")

        Raises:
            DomainError: If session is already completed/terminated
        """
        if self.state.status in (SessionStatus.COMPLETED, SessionStatus.TERMINATED, SessionStatus.EXPIRED):
            raise DomainError(f"Cannot expire session in status {self.state.status.value}")

        self.state.on(
            self.register_event(  # type: ignore
                SessionExpiredDomainEvent(
                    aggregate_id=self.id(),
                    expired_at=datetime.now(UTC),
                    reason=reason,
                )
            )
        )

    # =========================================================================
    # Queries
    # =========================================================================

    def get_pending_action(self) -> ClientAction | None:
        """Get the pending client action, if any."""
        if self.state.pending_action is None:
            return None
        return ClientAction.from_dict(self.state.pending_action)

    def get_current_item(self) -> SessionItem | None:
        """Get the current (most recent uncompleted) session item."""
        if not self.state.items:
            return None

        # Return the last item if it's not completed
        last_item_data = self.state.items[-1]
        if last_item_data.get("completed_at") is None:
            return SessionItem.from_dict(last_item_data)

        return None

    def get_item_by_id(self, item_id: str) -> SessionItem | None:
        """Get a session item by ID."""
        for item_data in self.state.items:
            if item_data["id"] == item_id:
                return SessionItem.from_dict(item_data)
        return None

    def get_all_items(self) -> list[SessionItem]:
        """Get all session items."""
        return [SessionItem.from_dict(item_data) for item_data in self.state.items]

    def get_completed_items_count(self) -> int:
        """Get the count of completed items."""
        return sum(1 for item in self.state.items if item.get("completed_at") is not None)

    def get_ui_state(self) -> UiState:
        """Get the current UI state for frontend restoration."""
        return UiState.from_dict(self.state.ui_state)

    def get_config(self) -> SessionConfig:
        """Get the session configuration."""
        return SessionConfig.from_dict(self.state.config)

    def is_active(self) -> bool:
        """Check if the session is in an active state."""
        return self.state.status in (SessionStatus.ACTIVE, SessionStatus.AWAITING_CLIENT_ACTION)

    def is_proactive(self) -> bool:
        """Check if this is a proactive session."""
        return self.state.control_mode == ControlMode.PROACTIVE

    def can_accept_response(self) -> bool:
        """Check if the session can accept a client response."""
        return self.state.status == SessionStatus.AWAITING_CLIENT_ACTION and self.state.pending_action is not None

    def get_time_remaining_seconds(self) -> int | None:
        """Calculate remaining time if there's a time limit.

        Returns:
            Remaining seconds, or None if no time limit
        """
        config = self.get_config()
        if config.time_limit_seconds is None:
            return None

        if self.state.started_at is None:
            return config.time_limit_seconds

        elapsed = (datetime.now(UTC) - self.state.started_at).total_seconds()
        remaining = config.time_limit_seconds - elapsed
        return max(0, int(remaining))
