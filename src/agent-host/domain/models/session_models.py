"""Session domain models and value objects.

This module contains the core value objects for the Session aggregate:
- Enums: SessionType, ControlMode, SessionStatus, ValidationStatus
- Value Objects: SessionConfig, SessionItem, ClientAction, ClientResponse, UiState

These models support both reactive (user-driven) and proactive (agent-driven) sessions.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4


class SessionType(str, Enum):
    """Types of sessions with different behaviors.

    Each session type has specific characteristics:
    - THOUGHT: Reactive, reflective exploration (user-driven)
    - LEARNING: Proactive, hybrid input (guided + free)
    - VALIDATION: Proactive, structured only (assessments)
    - SURVEY: Proactive, data collection via forms
    - WORKFLOW: Proactive, guided multi-step processes
    - APPROVAL: Proactive, decision workflows with confirmation
    """

    THOUGHT = "thought"
    LEARNING = "learning"
    VALIDATION = "validation"
    SURVEY = "survey"
    WORKFLOW = "workflow"
    APPROVAL = "approval"


class ControlMode(str, Enum):
    """Who drives the conversation.

    - REACTIVE: User prompts first, user drives the conversation
    - PROACTIVE: Agent prompts first, agent drives with widgets
    """

    REACTIVE = "reactive"
    PROACTIVE = "proactive"


class SessionStatus(str, Enum):
    """Session lifecycle states.

    State machine transitions:
    - PENDING -> ACTIVE (on start)
    - ACTIVE -> AWAITING_CLIENT_ACTION (on client tool call)
    - AWAITING_CLIENT_ACTION -> ACTIVE (on response received)
    - ACTIVE -> COMPLETED (on completion criteria met)
    - ACTIVE -> EXPIRED (on timeout)
    - ANY -> TERMINATED (on manual termination)
    """

    PENDING = "pending"
    ACTIVE = "active"
    AWAITING_CLIENT_ACTION = "awaiting_client_action"
    COMPLETED = "completed"
    EXPIRED = "expired"
    TERMINATED = "terminated"


class ValidationStatus(str, Enum):
    """Validation status for client responses.

    Used to track whether user responses meet schema requirements.
    """

    VALID = "valid"
    INVALID = "invalid"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class SessionConfig:
    """Type-specific session configuration.

    This is a value object that configures session behavior including
    time constraints, termination criteria, and input constraints.
    """

    # Time constraints
    time_limit_seconds: int | None = None
    item_time_limit_seconds: int | None = None

    # Termination criteria
    max_items: int | None = None
    completion_criteria: dict[str, Any] | None = None

    # Input constraints
    allow_skip: bool = False
    allow_back: bool = False

    # Concurrency
    allow_concurrent_sessions: bool = True

    # LLM Configuration (optional override)
    model_id: str | None = None

    # Extra data that doesn't map to fields (e.g., category, question_count)
    extra: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "time_limit_seconds": self.time_limit_seconds,
            "item_time_limit_seconds": self.item_time_limit_seconds,
            "max_items": self.max_items,
            "completion_criteria": self.completion_criteria,
            "allow_skip": self.allow_skip,
            "allow_back": self.allow_back,
            "allow_concurrent_sessions": self.allow_concurrent_sessions,
        }
        # Include model_id if set
        if self.model_id:
            result["model_id"] = self.model_id
        # Include extra data if present
        if self.extra:
            result.update(self.extra)
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionConfig":
        """Create from dictionary, preserving extra keys."""
        # Known keys for SessionConfig
        known_keys = {"time_limit_seconds", "item_time_limit_seconds", "max_items", "completion_criteria", "allow_skip", "allow_back", "allow_concurrent_sessions", "model_id", "extra"}
        # Collect unknown keys into extra
        extra = {k: v for k, v in data.items() if k not in known_keys}

        return cls(
            time_limit_seconds=data.get("time_limit_seconds"),
            item_time_limit_seconds=data.get("item_time_limit_seconds"),
            max_items=data.get("max_items"),
            completion_criteria=data.get("completion_criteria"),
            allow_skip=data.get("allow_skip", False),
            allow_back=data.get("allow_back", False),
            allow_concurrent_sessions=data.get("allow_concurrent_sessions", True),
            model_id=data.get("model_id"),
            extra=extra if extra else None,
        )


@dataclass
class ClientAction:
    """An action requiring client-side rendering.

    Represents a tool call that should be intercepted and rendered
    as a widget on the client side instead of being executed server-side.

    Attributes:
        tool_call_id: Unique identifier from the LLM's tool call
        tool_name: Name of the client tool (e.g., "present_choices")
        widget_type: Type of widget to render (e.g., "multiple_choice")
        props: Widget-specific properties to pass to the frontend
        lock_input: Whether to disable free-text chat input while widget is active
    """

    tool_call_id: str
    tool_name: str
    widget_type: str
    props: dict[str, Any]
    lock_input: bool = True

    def to_sse_payload(self) -> dict[str, Any]:
        """Convert to SSE event payload format.

        This format is consumed by the frontend's showClientActionWidget function
        which expects: tool_call_id, tool_name, widget_type, props, lock_input
        """
        return {
            "tool_call_id": self.tool_call_id,
            "tool_name": self.tool_name,
            "widget_type": self.widget_type,
            "props": self.props,
            "lock_input": self.lock_input,
        }

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for persistence."""
        return {
            "tool_call_id": self.tool_call_id,
            "tool_name": self.tool_name,
            "widget_type": self.widget_type,
            "props": self.props,
            "lock_input": self.lock_input,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ClientAction":
        """Create from dictionary."""
        return cls(
            tool_call_id=data["tool_call_id"],
            tool_name=data["tool_name"],
            widget_type=data["widget_type"],
            props=data.get("props", {}),
            lock_input=data.get("lock_input", True),
        )


@dataclass
class ClientResponse:
    """User's response to a client action.

    Contains the user's input from a widget along with validation status.

    Attributes:
        tool_call_id: Matches the ClientAction's tool_call_id
        response: The actual response data (schema depends on widget type)
        timestamp: When the response was submitted
        validation_status: Whether the response passed schema validation
        validation_errors: List of validation error messages if invalid
    """

    tool_call_id: str
    response: Any
    timestamp: datetime
    validation_status: ValidationStatus = ValidationStatus.VALID
    validation_errors: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for persistence."""
        return {
            "tool_call_id": self.tool_call_id,
            "response": self.response,
            "timestamp": self.timestamp.isoformat(),
            "validation_status": self.validation_status.value,
            "validation_errors": self.validation_errors,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ClientResponse":
        """Create from dictionary."""
        from datetime import datetime

        timestamp = data["timestamp"]
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)

        return cls(
            tool_call_id=data["tool_call_id"],
            response=data["response"],
            timestamp=timestamp,
            validation_status=ValidationStatus(data.get("validation_status", "valid")),
            validation_errors=data.get("validation_errors"),
        )


@dataclass
class SessionItem:
    """A single interaction loop within a session.

    Represents one question-answer cycle in a proactive session,
    capturing what the agent presented and how the user responded.

    Attributes:
        id: Unique identifier for this item
        sequence: Order in which this item was presented (1-indexed)
        started_at: When the agent presented the prompt
        completed_at: When the user responded (None if pending)
        agent_prompt: The text content the agent displayed
        client_action: The widget presented (None for text-only prompts)
        user_response: The user's response (None if pending)
        response_time_ms: Time from presentation to response
        evaluation: Optional evaluation/scoring data
    """

    id: str
    sequence: int
    started_at: datetime
    completed_at: datetime | None = None
    agent_prompt: str = ""
    client_action: ClientAction | None = None
    user_response: ClientResponse | None = None
    response_time_ms: float | None = None
    evaluation: dict[str, Any] | None = None

    @classmethod
    def create(
        cls,
        sequence: int,
        agent_prompt: str,
        client_action: ClientAction | None = None,
        started_at: datetime | None = None,
    ) -> "SessionItem":
        """Factory method to create a new session item."""
        from datetime import UTC

        return cls(
            id=str(uuid4()),
            sequence=sequence,
            started_at=started_at or datetime.now(UTC),
            agent_prompt=agent_prompt,
            client_action=client_action,
        )

    def complete(
        self,
        user_response: ClientResponse,
        evaluation: dict[str, Any] | None = None,
    ) -> None:
        """Mark this item as completed with user's response."""
        from datetime import UTC

        self.completed_at = datetime.now(UTC)
        self.user_response = user_response
        self.evaluation = evaluation

        # Calculate response time
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            self.response_time_ms = delta.total_seconds() * 1000

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for persistence."""
        return {
            "id": self.id,
            "sequence": self.sequence,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "agent_prompt": self.agent_prompt,
            "client_action": self.client_action.to_dict() if self.client_action else None,
            "user_response": self.user_response.to_dict() if self.user_response else None,
            "response_time_ms": self.response_time_ms,
            "evaluation": self.evaluation,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionItem":
        """Create from dictionary."""
        from datetime import UTC, datetime

        started_at = data["started_at"]
        if isinstance(started_at, str):
            started_at = datetime.fromisoformat(started_at)
            # Ensure timezone-aware (assume UTC if naive)
            if started_at.tzinfo is None:
                started_at = started_at.replace(tzinfo=UTC)

        completed_at = data.get("completed_at")
        if completed_at and isinstance(completed_at, str):
            completed_at = datetime.fromisoformat(completed_at)
            # Ensure timezone-aware (assume UTC if naive)
            if completed_at.tzinfo is None:
                completed_at = completed_at.replace(tzinfo=UTC)

        client_action = None
        if data.get("client_action"):
            client_action = ClientAction.from_dict(data["client_action"])

        user_response = None
        if data.get("user_response"):
            user_response = ClientResponse.from_dict(data["user_response"])

        return cls(
            id=data["id"],
            sequence=data["sequence"],
            started_at=started_at,
            completed_at=completed_at,
            agent_prompt=data.get("agent_prompt", ""),
            client_action=client_action,
            user_response=user_response,
            response_time_ms=data.get("response_time_ms"),
            evaluation=data.get("evaluation"),
        )


@dataclass
class UiState:
    """Current UI state for restoration on reconnect/refresh.

    This value object captures the frontend state so that users can
    resume their session after a page refresh or network disconnection.

    Attributes:
        chat_input_locked: Whether the chat input should be disabled
        active_widget: The currently displayed widget (None if none)
        widget_partial_state: Partial form data for restoration
    """

    chat_input_locked: bool = False
    active_widget: ClientAction | None = None
    widget_partial_state: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for persistence."""
        return {
            "chat_input_locked": self.chat_input_locked,
            "active_widget": self.active_widget.to_dict() if self.active_widget else None,
            "widget_partial_state": self.widget_partial_state,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UiState":
        """Create from dictionary."""
        active_widget = None
        if data.get("active_widget"):
            active_widget = ClientAction.from_dict(data["active_widget"])

        return cls(
            chat_input_locked=data.get("chat_input_locked", False),
            active_widget=active_widget,
            widget_partial_state=data.get("widget_partial_state"),
        )


# =============================================================================
# Default Session Type Configurations
# =============================================================================


def get_default_config_for_session_type(session_type: SessionType) -> SessionConfig:
    """Get the default configuration for a session type.

    Args:
        session_type: The type of session to configure

    Returns:
        Default SessionConfig for the session type
    """
    configs = {
        SessionType.THOUGHT: SessionConfig(
            time_limit_seconds=None,
            max_items=None,
            allow_skip=True,
            allow_back=True,
            allow_concurrent_sessions=True,
        ),
        SessionType.LEARNING: SessionConfig(
            time_limit_seconds=3600,  # 1 hour
            max_items=None,
            allow_skip=True,
            allow_back=True,
            allow_concurrent_sessions=True,
        ),
        SessionType.VALIDATION: SessionConfig(
            time_limit_seconds=1800,  # 30 minutes
            item_time_limit_seconds=120,  # 2 minutes per item
            max_items=20,
            allow_skip=False,
            allow_back=False,
            allow_concurrent_sessions=False,
        ),
        SessionType.SURVEY: SessionConfig(
            time_limit_seconds=None,
            max_items=None,
            allow_skip=True,
            allow_back=True,
            allow_concurrent_sessions=True,
        ),
        SessionType.WORKFLOW: SessionConfig(
            time_limit_seconds=None,
            max_items=None,
            allow_skip=False,
            allow_back=True,
            allow_concurrent_sessions=True,
        ),
        SessionType.APPROVAL: SessionConfig(
            time_limit_seconds=None,
            max_items=None,
            allow_skip=False,
            allow_back=False,
            allow_concurrent_sessions=True,
        ),
    }
    return configs.get(session_type, SessionConfig())


def get_control_mode_for_session_type(session_type: SessionType) -> ControlMode:
    """Get the control mode for a session type.

    Args:
        session_type: The type of session

    Returns:
        The control mode (REACTIVE or PROACTIVE)
    """
    reactive_types = {SessionType.THOUGHT}
    return ControlMode.REACTIVE if session_type in reactive_types else ControlMode.PROACTIVE
