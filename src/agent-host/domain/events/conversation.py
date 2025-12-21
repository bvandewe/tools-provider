"""Conversation domain events.

Events emitted by the Conversation aggregate to capture state changes.
These are persisted to EventStoreDB and can be used for:
- Event sourcing (rebuilding state)
- Projections (updating read models)
- Integration events (notifying other services)

Note: All events use snake_case for field names to match Python conventions.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from neuroglia.data.abstractions import DomainEvent
from neuroglia.eventing.cloud_events.decorators import cloudevent

# =============================================================================
# CONVERSATION LIFECYCLE EVENTS
# =============================================================================


@cloudevent("conversation.created.v1")
@dataclass
class ConversationCreatedDomainEvent(DomainEvent):
    """Emitted when a new conversation is created."""

    aggregate_id: str
    user_id: str
    definition_id: str
    title: str | None
    system_prompt: str | None
    created_at: datetime
    updated_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        user_id: str,
        definition_id: str = "",
        title: str | None = None,
        system_prompt: str | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.user_id = user_id
        self.definition_id = definition_id
        self.title = title
        self.system_prompt = system_prompt
        self.created_at = created_at or datetime.now(UTC)
        self.updated_at = updated_at or datetime.now(UTC)


@cloudevent("conversation.started.v1")
@dataclass
class ConversationStartedDomainEvent(DomainEvent):
    """Emitted when a conversation is started (first message exchange begins)."""

    aggregate_id: str
    started_at: datetime

    def __init__(self, aggregate_id: str, started_at: datetime | None = None) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.started_at = started_at or datetime.now(UTC)


@cloudevent("conversation.paused.v1")
@dataclass
class ConversationPausedDomainEvent(DomainEvent):
    """Emitted when user pauses a conversation."""

    aggregate_id: str
    paused_at: datetime

    def __init__(self, aggregate_id: str, paused_at: datetime | None = None) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.paused_at = paused_at or datetime.now(UTC)


@cloudevent("conversation.resumed.v1")
@dataclass
class ConversationResumedDomainEvent(DomainEvent):
    """Emitted when user resumes a paused conversation."""

    aggregate_id: str
    resumed_at: datetime

    def __init__(self, aggregate_id: str, resumed_at: datetime | None = None) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.resumed_at = resumed_at or datetime.now(UTC)


@cloudevent("conversation.completed.v1")
@dataclass
class ConversationCompletedDomainEvent(DomainEvent):
    """Emitted when a conversation completes successfully."""

    aggregate_id: str
    summary: dict[str, Any] | None
    completed_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        summary: dict[str, Any] | None = None,
        completed_at: datetime | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.summary = summary
        self.completed_at = completed_at or datetime.now(UTC)


@cloudevent("conversation.terminated.v1")
@dataclass
class ConversationTerminatedDomainEvent(DomainEvent):
    """Emitted when user terminates a conversation early."""

    aggregate_id: str
    reason: str
    terminated_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        reason: str = "",
        terminated_at: datetime | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.reason = reason
        self.terminated_at = terminated_at or datetime.now(UTC)


@cloudevent("conversation.deleted.v1")
@dataclass
class ConversationDeletedDomainEvent(DomainEvent):
    """Emitted when a conversation is soft-deleted/archived."""

    aggregate_id: str
    deleted_at: datetime

    def __init__(self, aggregate_id: str, deleted_at: datetime | None = None) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.deleted_at = deleted_at or datetime.now(UTC)


@cloudevent("conversation.cleared.v1")
@dataclass
class ConversationClearedDomainEvent(DomainEvent):
    """Emitted when conversation messages are cleared."""

    aggregate_id: str
    keep_system: bool
    cleared_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        keep_system: bool = True,
        cleared_at: datetime | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.keep_system = keep_system
        self.cleared_at = cleared_at or datetime.now(UTC)


# =============================================================================
# METADATA EVENTS
# =============================================================================


@cloudevent("conversation.title-updated.v1")
@dataclass
class ConversationTitleUpdatedDomainEvent(DomainEvent):
    """Emitted when conversation title is changed."""

    aggregate_id: str
    old_title: str | None
    new_title: str
    renamed_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        new_title: str,
        old_title: str | None = None,
        renamed_at: datetime | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.old_title = old_title
        self.new_title = new_title
        self.renamed_at = renamed_at or datetime.now(UTC)


# =============================================================================
# MESSAGE EVENTS
# =============================================================================


@cloudevent("conversation.message-added.v1")
@dataclass
class MessageAddedDomainEvent(DomainEvent):
    """Emitted when a message is added to the conversation."""

    aggregate_id: str
    message_id: str
    role: str
    content: str
    status: str
    metadata: dict[str, Any] | None
    created_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        message_id: str,
        role: str,
        content: str,
        status: str = "",
        metadata: dict[str, Any] | None = None,
        created_at: datetime | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.message_id = message_id
        self.role = role
        self.content = content
        self.status = status
        self.metadata = metadata
        self.created_at = created_at or datetime.now(UTC)


@cloudevent("conversation.message-status-updated.v1")
@dataclass
class MessageStatusUpdatedDomainEvent(DomainEvent):
    """Emitted when a message status changes."""

    aggregate_id: str
    message_id: str
    new_status: str

    def __init__(self, aggregate_id: str, message_id: str, new_status: str) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.message_id = message_id
        self.new_status = new_status


@cloudevent("conversation.message-content-updated.v1")
@dataclass
class MessageContentUpdatedDomainEvent(DomainEvent):
    """Emitted when a message content is updated (e.g., after streaming completes)."""

    aggregate_id: str
    message_id: str
    content: str
    updated_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        message_id: str,
        content: str,
        updated_at: datetime | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.message_id = message_id
        self.content = content
        self.updated_at = updated_at or datetime.now(UTC)


@cloudevent("conversation.tool-call-added.v1")
@dataclass
class ToolCallAddedDomainEvent(DomainEvent):
    """Emitted when a tool call is added to a message."""

    aggregate_id: str
    message_id: str
    call_id: str
    tool_name: str
    arguments: dict[str, Any]

    def __init__(
        self,
        aggregate_id: str,
        message_id: str,
        call_id: str,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.message_id = message_id
        self.call_id = call_id
        self.tool_name = tool_name
        self.arguments = arguments or {}


@cloudevent("conversation.tool-result-added.v1")
@dataclass
class ToolResultAddedDomainEvent(DomainEvent):
    """Emitted when a tool execution result is recorded."""

    aggregate_id: str
    message_id: str
    call_id: str
    tool_name: str
    success: bool
    result: Any
    error: str | None
    execution_time_ms: float | None

    def __init__(
        self,
        aggregate_id: str,
        message_id: str,
        call_id: str,
        tool_name: str,
        success: bool = True,
        result: Any = None,
        error: str | None = None,
        execution_time_ms: float | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.message_id = message_id
        self.call_id = call_id
        self.tool_name = tool_name
        self.success = success
        self.result = result
        self.error = error
        self.execution_time_ms = execution_time_ms


# =============================================================================
# CLIENT ACTION EVENTS (Widget interaction)
# =============================================================================


@cloudevent("conversation.client-action-requested.v1")
@dataclass
class ClientActionRequestedDomainEvent(DomainEvent):
    """Emitted when the agent requests a client action (widget response)."""

    aggregate_id: str
    action: dict[str, Any]
    requested_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        action: dict[str, Any] | None = None,
        requested_at: datetime | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.action = action or {}
        self.requested_at = requested_at or datetime.now(UTC)


@cloudevent("conversation.client-response-received.v1")
@dataclass
class ClientResponseReceivedDomainEvent(DomainEvent):
    """Emitted when the user submits a response to a client action."""

    aggregate_id: str
    tool_call_id: str
    response: Any
    received_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        tool_call_id: str,
        response: Any = None,
        received_at: datetime | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.tool_call_id = tool_call_id
        self.response = response
        self.received_at = received_at or datetime.now(UTC)


# =============================================================================
# TEMPLATE / ASSESSMENT EVENTS
# =============================================================================


@cloudevent("conversation.item-generated.v1")
@dataclass
class ItemGeneratedDomainEvent(DomainEvent):
    """Emitted when an item is generated from a skill template.

    Used for assessment conversations where LLM generates questions.
    The generated item includes the correct answer for later grading.
    """

    aggregate_id: str
    item: dict[str, Any]
    generated_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        item: dict[str, Any] | None = None,
        generated_at: datetime | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.item = item or {}
        self.generated_at = generated_at or datetime.now(UTC)


@cloudevent("conversation.item-answered.v1")
@dataclass
class ItemAnsweredDomainEvent(DomainEvent):
    """Emitted when user answers a generated item.

    Records the user's response and grading result for assessment.
    """

    aggregate_id: str
    item_id: str
    user_response: str
    is_correct: bool | None
    response_time_ms: int | None
    answered_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        item_id: str,
        user_response: str,
        is_correct: bool | None = None,
        response_time_ms: int | None = None,
        answered_at: datetime | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.item_id = item_id
        self.user_response = user_response
        self.is_correct = is_correct
        self.response_time_ms = response_time_ms
        self.answered_at = answered_at or datetime.now(UTC)


@cloudevent("conversation.template-advanced.v1")
@dataclass
class TemplateAdvancedDomainEvent(DomainEvent):
    """Emitted when conversation advances to next template item."""

    aggregate_id: str
    previous_index: int
    current_index: int
    advanced_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        previous_index: int = 0,
        current_index: int = 0,
        advanced_at: datetime | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.previous_index = previous_index
        self.current_index = current_index
        self.advanced_at = advanced_at or datetime.now(UTC)


# =============================================================================
# SHARING EVENTS
# =============================================================================


@cloudevent("conversation.shared.v1")
@dataclass
class ConversationSharedDomainEvent(DomainEvent):
    """Emitted when a conversation is shared with another user."""

    aggregate_id: str
    user_id: str
    role: str
    shared_by: str
    shared_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        user_id: str,
        role: str,
        shared_by: str,
        shared_at: datetime | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.user_id = user_id
        self.role = role
        self.shared_by = shared_by
        self.shared_at = shared_at or datetime.now(UTC)


@cloudevent("conversation.share-revoked.v1")
@dataclass
class ConversationShareRevokedDomainEvent(DomainEvent):
    """Emitted when sharing is revoked from a user."""

    aggregate_id: str
    user_id: str
    revoked_by: str
    revoked_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        user_id: str,
        revoked_by: str,
        revoked_at: datetime | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.user_id = user_id
        self.revoked_by = revoked_by
        self.revoked_at = revoked_at or datetime.now(UTC)


# =============================================================================
# TEMPLATE CONFIGURATION EVENTS
# =============================================================================


@cloudevent("conversation.template-initialized.v1")
@dataclass
class TemplateInitializedDomainEvent(DomainEvent):
    """Emitted when a conversation is initialized with a template configuration.

    Captures the template settings and the item order (which may be shuffled).
    """

    aggregate_id: str
    template_id: str
    template_config: dict[str, Any]
    item_order: list[int]  # Indices of items in presentation order (shuffled or sequential)
    deadline: datetime | None  # Absolute deadline if max_duration is set
    initialized_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        template_id: str,
        template_config: dict[str, Any] | None = None,
        item_order: list[int] | None = None,
        deadline: datetime | None = None,
        initialized_at: datetime | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.template_id = template_id
        self.template_config = template_config or {}
        self.item_order = item_order or []
        self.deadline = deadline
        self.initialized_at = initialized_at or datetime.now(UTC)


@cloudevent("conversation.template-navigated-backward.v1")
@dataclass
class TemplateNavigatedBackwardDomainEvent(DomainEvent):
    """Emitted when user navigates backward to a previous item."""

    aggregate_id: str
    from_index: int
    to_index: int
    navigated_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        from_index: int,
        to_index: int,
        navigated_at: datetime | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.from_index = from_index
        self.to_index = to_index
        self.navigated_at = navigated_at or datetime.now(UTC)


@cloudevent("conversation.deadline-updated.v1")
@dataclass
class DeadlineUpdatedDomainEvent(DomainEvent):
    """Emitted when the conversation deadline is adjusted (e.g., after pause/resume)."""

    aggregate_id: str
    old_deadline: datetime | None
    new_deadline: datetime | None
    reason: str  # 'pause_resume', 'extension', etc.
    updated_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        old_deadline: datetime | None = None,
        new_deadline: datetime | None = None,
        reason: str = "",
        updated_at: datetime | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.old_deadline = old_deadline
        self.new_deadline = new_deadline
        self.reason = reason
        self.updated_at = updated_at or datetime.now(UTC)


@cloudevent("conversation.item-score-recorded.v1")
@dataclass
class ItemScoreRecordedDomainEvent(DomainEvent):
    """Emitted when a score is recorded for an item response."""

    aggregate_id: str
    item_id: str
    content_id: str | None
    score: float
    max_score: float
    is_correct: bool | None
    recorded_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        item_id: str,
        content_id: str | None = None,
        score: float = 0.0,
        max_score: float = 1.0,
        is_correct: bool | None = None,
        recorded_at: datetime | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.item_id = item_id
        self.content_id = content_id
        self.score = score
        self.max_score = max_score
        self.is_correct = is_correct
        self.recorded_at = recorded_at or datetime.now(UTC)
