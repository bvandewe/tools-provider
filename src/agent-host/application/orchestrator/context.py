"""Orchestrator context and state dataclasses.

This module contains the core data structures used by the orchestrator:
- OrchestratorState: Enum defining the state machine states
- ItemExecutionState: Tracks execution of a single template item
- ConversationContext: Full context for an active conversation

These dataclasses are designed to be:
- Immutable where possible (use frozen=True sparingly due to mutation needs)
- Serializable for potential persistence/resume capability
- Well-documented for clear semantics
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class OrchestratorState(str, Enum):
    """State of the conversation orchestrator.

    State Machine Transitions:
        INITIALIZING → READY (reactive flow)
        INITIALIZING → PRESENTING (proactive flow)
        READY → PROCESSING (user sends message)
        PROCESSING → READY (agent responds, await next input)
        PROCESSING → SUSPENDED (widget requires response)
        PRESENTING → SUSPENDED (widget rendered, await response)
        SUSPENDED → PRESENTING (widget response received, continue)
        SUSPENDED → READY (all items complete)
        READY/PRESENTING → PAUSED (user requests pause)
        PAUSED → READY/PRESENTING (user resumes)
        ANY → COMPLETED (conversation ends)
        ANY → ERROR (unrecoverable error)
    """

    INITIALIZING = "initializing"
    READY = "ready"  # Waiting for user input (reactive)
    PRESENTING = "presenting"  # Agent is presenting content (proactive)
    PROCESSING = "processing"  # Processing user input
    SUSPENDED = "suspended"  # Waiting for client response (widget)
    PAUSED = "paused"  # Conversation paused
    COMPLETED = "completed"  # Conversation finished
    ERROR = "error"  # Error state

    def can_transition_to(self, target: "OrchestratorState") -> bool:
        """Check if transition to target state is allowed.

        Args:
            target: The target state to transition to

        Returns:
            True if the transition is valid, False otherwise
        """
        valid_transitions: dict[OrchestratorState, set[OrchestratorState]] = {
            OrchestratorState.INITIALIZING: {
                OrchestratorState.READY,
                OrchestratorState.PRESENTING,
                OrchestratorState.ERROR,
            },
            OrchestratorState.READY: {
                OrchestratorState.PROCESSING,
                OrchestratorState.PAUSED,
                OrchestratorState.COMPLETED,
                OrchestratorState.ERROR,
            },
            OrchestratorState.PRESENTING: {
                OrchestratorState.SUSPENDED,
                OrchestratorState.READY,
                OrchestratorState.PAUSED,
                OrchestratorState.COMPLETED,
                OrchestratorState.ERROR,
            },
            OrchestratorState.PROCESSING: {
                OrchestratorState.READY,
                OrchestratorState.SUSPENDED,
                OrchestratorState.PAUSED,
                OrchestratorState.COMPLETED,
                OrchestratorState.ERROR,
            },
            OrchestratorState.SUSPENDED: {
                OrchestratorState.PRESENTING,
                OrchestratorState.READY,
                OrchestratorState.PAUSED,
                OrchestratorState.COMPLETED,
                OrchestratorState.ERROR,
            },
            OrchestratorState.PAUSED: {
                OrchestratorState.READY,
                OrchestratorState.PRESENTING,
                OrchestratorState.COMPLETED,
                OrchestratorState.ERROR,
            },
            OrchestratorState.COMPLETED: set(),  # Terminal state
            OrchestratorState.ERROR: set(),  # Terminal state
        }
        return target in valid_transitions.get(self, set())

    def is_terminal(self) -> bool:
        """Check if this is a terminal state (no further transitions)."""
        return self in {OrchestratorState.COMPLETED, OrchestratorState.ERROR}

    def allows_user_input(self) -> bool:
        """Check if user input is accepted in this state."""
        return self in {OrchestratorState.READY, OrchestratorState.PROCESSING}

    def allows_widget_response(self) -> bool:
        """Check if widget responses are accepted in this state."""
        return self == OrchestratorState.SUSPENDED


@dataclass
class ItemExecutionState:
    """Tracks the execution state of a single template item.

    This state is ephemeral during the WebSocket session but can be
    persisted to the conversation aggregate for resume capability.

    Attributes:
        item_id: Unique identifier for the template item
        item_index: Zero-based index in the template's items list
        started_at: Timestamp when item execution started
        completed_at: Timestamp when item execution completed (None if ongoing)
        widget_responses: Map of widget_id → response value
        required_widget_ids: Set of widget IDs that must be answered
        answered_widget_ids: Set of widget IDs that have been answered
        require_user_confirmation: Whether user must click confirm button
        confirmation_button_text: Text for the confirmation button
        user_confirmed: Whether user has clicked the confirm button
    """

    item_id: str
    item_index: int
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None

    # Widget response tracking
    widget_responses: dict[str, Any] = field(default_factory=dict)
    required_widget_ids: set[str] = field(default_factory=set)
    answered_widget_ids: set[str] = field(default_factory=set)

    # User confirmation tracking
    require_user_confirmation: bool = False
    confirmation_button_text: str = "Submit"
    user_confirmed: bool = False

    @property
    def is_complete(self) -> bool:
        """Check if all required widgets have been answered and confirmed if needed.

        Returns:
            True if item execution is complete, False otherwise
        """
        widgets_answered = self.required_widget_ids <= self.answered_widget_ids
        if self.require_user_confirmation:
            return widgets_answered and self.user_confirmed
        return widgets_answered

    @property
    def pending_widget_ids(self) -> set[str]:
        """Get IDs of required widgets not yet answered.

        Returns:
            Set of widget IDs that still need responses
        """
        return self.required_widget_ids - self.answered_widget_ids

    @property
    def completion_percentage(self) -> float:
        """Calculate completion percentage based on required widgets.

        Returns:
            Percentage (0.0 to 100.0) of required widgets answered
        """
        if not self.required_widget_ids:
            # If no widgets required, check confirmation only
            if self.require_user_confirmation:
                return 100.0 if self.user_confirmed else 0.0
            return 100.0

        widget_progress = len(self.answered_widget_ids) / len(self.required_widget_ids)
        if self.require_user_confirmation:
            # Widget completion is 90%, confirmation is 10%
            base_progress = widget_progress * 90.0
            confirmation_progress = 10.0 if self.user_confirmed else 0.0
            return base_progress + confirmation_progress
        return widget_progress * 100.0

    def record_response(self, widget_id: str, value: Any) -> None:
        """Record a widget response.

        Args:
            widget_id: The widget's unique identifier
            value: The response value from the user
        """
        self.widget_responses[widget_id] = value
        self.answered_widget_ids.add(widget_id)

    def confirm(self) -> None:
        """Mark the item as confirmed by user."""
        self.user_confirmed = True
        if self.is_complete:
            self.completed_at = datetime.now(UTC)

    def mark_complete(self) -> None:
        """Explicitly mark the item as complete."""
        self.completed_at = datetime.now(UTC)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for persistence.

        Returns:
            Dictionary representation suitable for JSON serialization
        """
        return {
            "item_id": self.item_id,
            "item_index": self.item_index,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "widget_responses": self.widget_responses,
            "required_widget_ids": list(self.required_widget_ids),
            "answered_widget_ids": list(self.answered_widget_ids),
            "require_user_confirmation": self.require_user_confirmation,
            "confirmation_button_text": self.confirmation_button_text,
            "user_confirmed": self.user_confirmed,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ItemExecutionState":
        """Deserialize from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            Reconstructed ItemExecutionState instance
        """
        started_at = data.get("started_at")
        if isinstance(started_at, str):
            started_at = datetime.fromisoformat(started_at)
        elif started_at is None:
            started_at = datetime.now(UTC)

        completed_at = data.get("completed_at")
        if isinstance(completed_at, str):
            completed_at = datetime.fromisoformat(completed_at)

        return cls(
            item_id=data["item_id"],
            item_index=data["item_index"],
            started_at=started_at,
            completed_at=completed_at,
            widget_responses=data.get("widget_responses", {}),
            required_widget_ids=set(data.get("required_widget_ids", [])),
            answered_widget_ids=set(data.get("answered_widget_ids", [])),
            require_user_confirmation=data.get("require_user_confirmation", False),
            confirmation_button_text=data.get("confirmation_button_text", "Submit"),
            user_confirmed=data.get("user_confirmed", False),
        )


@dataclass
class ConversationContext:
    """Context for an active conversation orchestration.

    Contains all the information needed to orchestrate a conversation,
    including references to the connection, definition, template, and agent state.

    This context is maintained in memory during an active WebSocket session
    and can be serialized for resume capability.

    Attributes:
        connection_id: WebSocket connection identifier
        conversation_id: Domain conversation aggregate ID
        user_id: Authenticated user's identifier
        definition_id: Agent definition ID (optional)
        definition_name: Human-readable definition name
        system_prompt: System prompt from agent definition
        model: LLM model identifier (e.g., "openai:gpt-4o")
        allow_model_selection: Whether users can change model
        is_proactive: Whether this is a proactive (template-driven) conversation
        has_template: Whether a template is associated
        template_id: Template identifier if proactive
        current_item_index: Current position in template items
        total_items: Total number of template items
        template_config: Template configuration parameters
        current_item_state: Execution state for current item
        state: Current orchestrator state
        started_at: When the conversation started
        last_activity: Timestamp of last user/agent activity
        client_capabilities: Capabilities declared by the client
        tools: Available tools for this conversation
        access_token: User's access token for tool execution
        pending_widget_id: Widget awaiting response
        pending_tool_call_id: Tool call awaiting result
    """

    # Connection reference
    connection_id: str
    conversation_id: str
    user_id: str

    # Definition info (loaded from read model)
    definition_id: str | None = None
    definition_name: str | None = None
    system_prompt: str | None = None
    model: str | None = None
    allow_model_selection: bool = True
    is_proactive: bool = False
    has_template: bool = False
    template_id: str | None = None

    # Template state (for proactive conversations)
    current_item_index: int = 0
    total_items: int = 0
    template_config: dict[str, Any] = field(default_factory=dict)

    # Current item execution state
    current_item_state: ItemExecutionState | None = None

    # Orchestrator state
    state: OrchestratorState = OrchestratorState.INITIALIZING
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_activity: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Client capabilities
    client_capabilities: list[str] = field(default_factory=list)

    # Tools and authentication
    tools: list[Any] = field(default_factory=list)
    access_token: str | None = None

    # Pending operations
    pending_widget_id: str | None = None
    pending_tool_call_id: str | None = None

    @property
    def template_progress_percentage(self) -> float:
        """Calculate overall template progress.

        Returns:
            Percentage (0.0 to 100.0) of template completion
        """
        if self.total_items == 0:
            return 0.0
        return (self.current_item_index / self.total_items) * 100.0

    @property
    def is_template_complete(self) -> bool:
        """Check if all template items have been processed.

        Returns:
            True if template is complete, False otherwise
        """
        return self.current_item_index >= self.total_items

    @property
    def has_pending_operation(self) -> bool:
        """Check if there's a pending widget or tool call.

        Returns:
            True if waiting for a response, False otherwise
        """
        return self.pending_widget_id is not None or self.pending_tool_call_id is not None

    def update_activity(self) -> None:
        """Update the last activity timestamp to now."""
        self.last_activity = datetime.now(UTC)

    def transition_to(self, new_state: OrchestratorState) -> bool:
        """Attempt to transition to a new state.

        Args:
            new_state: The target state

        Returns:
            True if transition succeeded, False if invalid
        """
        if self.state.can_transition_to(new_state):
            self.state = new_state
            self.update_activity()
            return True
        return False

    def advance_to_next_item(self) -> bool:
        """Advance to the next template item.

        Returns:
            True if there are more items, False if template complete
        """
        if self.current_item_state:
            self.current_item_state.mark_complete()

        self.current_item_index += 1
        self.current_item_state = None
        self.pending_widget_id = None
        self.update_activity()

        return not self.is_template_complete

    def start_item(self, item_id: str, require_confirmation: bool = False, button_text: str = "Submit") -> ItemExecutionState:
        """Start execution of a new template item.

        Args:
            item_id: The item's unique identifier
            require_confirmation: Whether user must confirm after widgets
            button_text: Text for the confirmation button

        Returns:
            The new ItemExecutionState
        """
        self.current_item_state = ItemExecutionState(
            item_id=item_id,
            item_index=self.current_item_index,
            require_user_confirmation=require_confirmation,
            confirmation_button_text=button_text,
        )
        self.update_activity()
        return self.current_item_state

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for persistence/debugging.

        Returns:
            Dictionary representation
        """
        return {
            "connection_id": self.connection_id,
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "definition_id": self.definition_id,
            "definition_name": self.definition_name,
            "model": self.model,
            "allow_model_selection": self.allow_model_selection,
            "is_proactive": self.is_proactive,
            "has_template": self.has_template,
            "template_id": self.template_id,
            "current_item_index": self.current_item_index,
            "total_items": self.total_items,
            "template_config": self.template_config,
            "current_item_state": self.current_item_state.to_dict() if self.current_item_state else None,
            "state": self.state.value,
            "started_at": self.started_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "client_capabilities": self.client_capabilities,
            "tool_count": len(self.tools),
            "has_access_token": self.access_token is not None,
            "pending_widget_id": self.pending_widget_id,
            "pending_tool_call_id": self.pending_tool_call_id,
        }
