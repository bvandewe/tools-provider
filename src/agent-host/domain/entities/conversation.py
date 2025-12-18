"""Conversation aggregate definition using the AggregateState pattern.

DomainEvents are appended/aggregated in the Conversation and the
repository publishes them via Mediator after the Conversation was persisted.

The Conversation is the **single AggregateRoot** in this architecture.
It represents a complete interaction between user and agent.
"""

from datetime import UTC, datetime
from typing import Any, cast
from uuid import uuid4

from multipledispatch import dispatch
from neuroglia.data.abstractions import AggregateRoot, AggregateState

from domain.enums import ConversationStatus
from domain.events.conversation import (
    ClientActionRequestedDomainEvent,
    ClientResponseReceivedDomainEvent,
    ConversationClearedDomainEvent,
    ConversationCompletedDomainEvent,
    ConversationCreatedDomainEvent,
    ConversationDeletedDomainEvent,
    ConversationPausedDomainEvent,
    ConversationResumedDomainEvent,
    ConversationSharedDomainEvent,
    ConversationShareRevokedDomainEvent,
    ConversationStartedDomainEvent,
    ConversationTerminatedDomainEvent,
    ConversationTitleUpdatedDomainEvent,
    DeadlineUpdatedDomainEvent,
    ItemAnsweredDomainEvent,
    ItemGeneratedDomainEvent,
    ItemScoreRecordedDomainEvent,
    MessageAddedDomainEvent,
    MessageStatusUpdatedDomainEvent,
    TemplateAdvancedDomainEvent,
    TemplateInitializedDomainEvent,
    TemplateNavigatedBackwardDomainEvent,
    ToolCallAddedDomainEvent,
    ToolResultAddedDomainEvent,
)
from domain.models.message import Message, MessageRole, MessageStatus


class ConversationState(AggregateState[str]):
    """Encapsulates the persisted state for the Conversation aggregate.

    This state is rebuilt from events (event sourcing).
    """

    # Identity
    id: str
    user_id: str
    definition_id: str  # References AgentDefinition

    # Display
    title: str | None
    system_prompt: str | None

    # Status
    status: str  # ConversationStatus value

    # Content
    messages: list[dict[str, Any]]  # Serialized message data
    pending_action: dict[str, Any] | None  # ClientAction awaiting response

    # Template progress (for proactive conversations)
    # Extended structure:
    # {
    #   current_index: int,              # Current position in item_order
    #   generated_items: list[dict],     # Items that have been presented
    #   item_order: list[int],           # Presentation order (indices into template.items)
    #   item_scores: dict[str, dict],    # item_id -> {score, max_score, is_correct, attempts}
    #   total_score: float,              # Accumulated score
    #   max_possible_score: float,       # Maximum possible score
    # }
    template_progress: dict[str, Any] | None

    # Template configuration (for UI behavior)
    # Stores the client-safe template config sent at initialization
    template_config: dict[str, Any] | None

    # Deadline tracking (for timed conversations)
    deadline: datetime | None  # Absolute deadline
    accumulated_pause_ms: int  # Total time paused (for deadline adjustment)

    # Sharing
    shared_with: list[dict[str, Any]]  # [{ user_id, role, shared_at, shared_by }]

    # Timestamps
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    paused_at: datetime | None
    completed_at: datetime | None

    def __init__(self) -> None:
        super().__init__()
        self.id = ""
        self.user_id = ""
        self.definition_id = ""
        self.title = None
        self.system_prompt = None
        self.status = ConversationStatus.PENDING.value
        self.messages = []
        self.pending_action = None
        self.template_progress = None
        self.template_config = None
        self.deadline = None
        self.accumulated_pause_ms = 0
        self.shared_with = []
        now = datetime.now(UTC)
        self.created_at = now
        self.updated_at = now
        self.started_at = None
        self.paused_at = None
        self.completed_at = None

    @dispatch(ConversationCreatedDomainEvent)
    def on(self, event: ConversationCreatedDomainEvent) -> None:  # type: ignore[override]
        """Apply the creation event to the state."""
        self.id = event.aggregate_id
        self.user_id = event.user_id
        self.definition_id = event.definition_id
        self.title = event.title
        self.system_prompt = event.system_prompt
        self.status = ConversationStatus.PENDING.value
        self.created_at = event.created_at
        self.updated_at = event.updated_at

        # Add system message if provided
        if event.system_prompt:
            system_msg = Message.create_system_message(event.system_prompt)
            self.messages.append(system_msg.to_dict())

    @dispatch(ConversationTitleUpdatedDomainEvent)
    def on(self, event: ConversationTitleUpdatedDomainEvent) -> None:  # type: ignore[override]
        """Apply the title updated event to the state."""
        self.title = event.new_title
        self.updated_at = datetime.now(UTC)

    @dispatch(MessageAddedDomainEvent)
    def on(self, event: MessageAddedDomainEvent) -> None:  # type: ignore[override]
        """Apply the message added event to the state."""
        message_data = {
            "id": event.message_id,
            "role": event.role,
            "content": event.content,
            "created_at": event.created_at.isoformat(),
            "status": event.status,
            "tool_calls": [],
            "tool_results": [],
            "metadata": event.metadata,
        }
        self.messages.append(message_data)
        self.updated_at = datetime.now(UTC)

        # Auto-generate title from first user message if not set
        if self.title is None and event.role == MessageRole.USER.value:
            content = event.content.strip()
            self.title = content[:47] + "..." if len(content) > 50 else content

    @dispatch(ToolCallAddedDomainEvent)
    def on(self, event: ToolCallAddedDomainEvent) -> None:  # type: ignore[override]
        """Apply the tool call added event to the state."""
        for msg in self.messages:
            if msg["id"] == event.message_id:
                msg["tool_calls"].append(
                    {
                        "call_id": event.call_id,
                        "tool_name": event.tool_name,
                        "arguments": event.arguments,
                    }
                )
                break
        self.updated_at = datetime.now(UTC)

    @dispatch(ToolResultAddedDomainEvent)
    def on(self, event: ToolResultAddedDomainEvent) -> None:  # type: ignore[override]
        """Apply the tool result added event to the state."""
        for msg in self.messages:
            if msg["id"] == event.message_id:
                msg["tool_results"].append(
                    {
                        "call_id": event.call_id,
                        "tool_name": event.tool_name,
                        "success": event.success,
                        "result": event.result,
                        "error": event.error,
                        "execution_time_ms": event.execution_time_ms,
                    }
                )
                break
        self.updated_at = datetime.now(UTC)

    @dispatch(MessageStatusUpdatedDomainEvent)
    def on(self, event: MessageStatusUpdatedDomainEvent) -> None:  # type: ignore[override]
        """Apply the message status updated event to the state."""
        for msg in self.messages:
            if msg["id"] == event.message_id:
                msg["status"] = event.new_status
                break
        self.updated_at = datetime.now(UTC)

    @dispatch(ConversationClearedDomainEvent)
    def on(self, event: ConversationClearedDomainEvent) -> None:  # type: ignore[override]
        """Apply the conversation cleared event to the state."""
        if event.keep_system:
            self.messages = [m for m in self.messages if m["role"] == MessageRole.SYSTEM.value]
        else:
            self.messages = []
        self.updated_at = datetime.now(UTC)

    @dispatch(ConversationDeletedDomainEvent)
    def on(self, event: ConversationDeletedDomainEvent) -> None:  # type: ignore[override]
        """Apply the deleted event to the state."""
        self.status = ConversationStatus.ARCHIVED.value
        self.updated_at = event.deleted_at

    @dispatch(ConversationStartedDomainEvent)
    def on(self, event: ConversationStartedDomainEvent) -> None:  # type: ignore[override]
        """Apply the started event to the state."""
        self.status = ConversationStatus.ACTIVE.value
        self.started_at = event.started_at
        self.updated_at = event.started_at

    @dispatch(ConversationPausedDomainEvent)
    def on(self, event: ConversationPausedDomainEvent) -> None:  # type: ignore[override]
        """Apply the paused event to the state."""
        self.status = ConversationStatus.PAUSED.value
        self.paused_at = event.paused_at
        self.updated_at = event.paused_at

    @dispatch(ConversationResumedDomainEvent)
    def on(self, event: ConversationResumedDomainEvent) -> None:  # type: ignore[override]
        """Apply the resumed event to the state."""
        self.status = ConversationStatus.ACTIVE.value
        self.paused_at = None
        self.updated_at = event.resumed_at

    @dispatch(ConversationCompletedDomainEvent)
    def on(self, event: ConversationCompletedDomainEvent) -> None:  # type: ignore[override]
        """Apply the completed event to the state."""
        self.status = ConversationStatus.COMPLETED.value
        self.pending_action = None
        self.completed_at = event.completed_at
        self.updated_at = event.completed_at

    @dispatch(ConversationTerminatedDomainEvent)
    def on(self, event: ConversationTerminatedDomainEvent) -> None:  # type: ignore[override]
        """Apply the terminated event to the state."""
        self.status = ConversationStatus.TERMINATED.value
        self.pending_action = None
        self.updated_at = event.terminated_at

    @dispatch(ClientActionRequestedDomainEvent)
    def on(self, event: ClientActionRequestedDomainEvent) -> None:  # type: ignore[override]
        """Apply client action requested event to the state."""
        self.status = ConversationStatus.AWAITING_WIDGET.value
        self.pending_action = event.action
        self.updated_at = event.requested_at

    @dispatch(ClientResponseReceivedDomainEvent)
    def on(self, event: ClientResponseReceivedDomainEvent) -> None:  # type: ignore[override]
        """Apply client response received event to the state."""
        self.status = ConversationStatus.ACTIVE.value
        self.pending_action = None
        self.updated_at = event.received_at

    @dispatch(ItemGeneratedDomainEvent)
    def on(self, event: ItemGeneratedDomainEvent) -> None:  # type: ignore[override]
        """Apply item generated event to the state."""
        if self.template_progress is None:
            self.template_progress = {"current_index": 0, "generated_items": []}
        self.template_progress["generated_items"].append(event.item)
        self.updated_at = event.generated_at

    @dispatch(ItemAnsweredDomainEvent)
    def on(self, event: ItemAnsweredDomainEvent) -> None:  # type: ignore[override]
        """Apply item answered event to the state."""
        if self.template_progress and "generated_items" in self.template_progress:
            for item in self.template_progress["generated_items"]:
                if item.get("id") == event.item_id:
                    item["user_response"] = event.user_response
                    item["is_correct"] = event.is_correct
                    item["response_time_ms"] = event.response_time_ms
                    item["answered_at"] = event.answered_at.isoformat()
                    break
        self.updated_at = event.answered_at

    @dispatch(TemplateAdvancedDomainEvent)
    def on(self, event: TemplateAdvancedDomainEvent) -> None:  # type: ignore[override]
        """Apply template advanced event to the state."""
        if self.template_progress is None:
            self.template_progress = {"current_index": 0, "generated_items": []}
        self.template_progress["current_index"] = event.current_index
        self.updated_at = event.advanced_at

    @dispatch(ConversationSharedDomainEvent)
    def on(self, event: ConversationSharedDomainEvent) -> None:  # type: ignore[override]
        """Apply conversation shared event to the state."""
        self.shared_with.append(
            {
                "user_id": event.user_id,
                "role": event.role,
                "shared_by": event.shared_by,
                "shared_at": event.shared_at.isoformat(),
            }
        )
        self.updated_at = event.shared_at

    @dispatch(ConversationShareRevokedDomainEvent)
    def on(self, event: ConversationShareRevokedDomainEvent) -> None:  # type: ignore[override]
        """Apply share revoked event to the state."""
        self.shared_with = [s for s in self.shared_with if s["user_id"] != event.user_id]
        self.updated_at = event.revoked_at

    @dispatch(TemplateInitializedDomainEvent)
    def on(self, event: TemplateInitializedDomainEvent) -> None:  # type: ignore[override]
        """Apply template initialized event to the state."""
        self.template_config = event.template_config
        self.deadline = event.deadline
        # Initialize template_progress with the item order
        if self.template_progress is None:
            self.template_progress = {
                "current_index": 0,
                "generated_items": [],
                "item_order": event.item_order,
                "item_scores": {},
                "total_score": 0.0,
                "max_possible_score": 0.0,
            }
        else:
            self.template_progress["item_order"] = event.item_order
        self.updated_at = event.initialized_at

    @dispatch(TemplateNavigatedBackwardDomainEvent)
    def on(self, event: TemplateNavigatedBackwardDomainEvent) -> None:  # type: ignore[override]
        """Apply backward navigation event to the state."""
        if self.template_progress is not None:
            self.template_progress["current_index"] = event.to_index
            # Clear the previous answer for the target item (reset for re-attempt)
            # The item's score will be overwritten on next submission
        self.updated_at = event.navigated_at

    @dispatch(DeadlineUpdatedDomainEvent)
    def on(self, event: DeadlineUpdatedDomainEvent) -> None:  # type: ignore[override]
        """Apply deadline updated event to the state."""
        self.deadline = event.new_deadline
        self.updated_at = event.updated_at

    @dispatch(ItemScoreRecordedDomainEvent)
    def on(self, event: ItemScoreRecordedDomainEvent) -> None:  # type: ignore[override]
        """Apply item score recorded event to the state."""
        if self.template_progress is None:
            self.template_progress = {
                "current_index": 0,
                "generated_items": [],
                "item_order": [],
                "item_scores": {},
                "total_score": 0.0,
                "max_possible_score": 0.0,
            }
        # Record/update the score for this item
        item_scores = self.template_progress.get("item_scores", {})
        old_score = item_scores.get(event.item_id, {}).get("score", 0.0)
        item_scores[event.item_id] = {
            "score": event.score,
            "max_score": event.max_score,
            "is_correct": event.is_correct,
            "content_id": event.content_id,
            "recorded_at": event.recorded_at.isoformat(),
        }
        self.template_progress["item_scores"] = item_scores
        # Update total score (replace old score with new one)
        current_total = self.template_progress.get("total_score", 0.0)
        self.template_progress["total_score"] = current_total - old_score + event.score
        # Track max possible score
        if old_score == 0:  # First time scoring this item
            current_max = self.template_progress.get("max_possible_score", 0.0)
            self.template_progress["max_possible_score"] = current_max + event.max_score
        self.updated_at = event.recorded_at


class Conversation(AggregateRoot[ConversationState, str]):
    """Conversation aggregate root - the single AggregateRoot in this architecture.

    Represents a complete interaction between user and agent.
    All conversation state is managed here and reconstructed from events.
    """

    def __init__(
        self,
        user_id: str,
        definition_id: str = "",
        title: str | None = None,
        system_prompt: str | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        conversation_id: str | None = None,
    ) -> None:
        super().__init__()
        aggregate_id = conversation_id or str(uuid4())
        created_time = created_at or datetime.now(UTC)
        updated_time = updated_at or created_time

        self.state.on(
            self.register_event(  # type: ignore
                ConversationCreatedDomainEvent(
                    aggregate_id=aggregate_id,
                    user_id=user_id,
                    definition_id=definition_id,
                    title=title,
                    system_prompt=system_prompt,
                    created_at=created_time,
                    updated_at=updated_time,
                )
            )
        )

    def id(self) -> str:
        """Return the aggregate identifier with a precise type."""
        aggregate_id = super().id()
        if aggregate_id is None:
            raise ValueError("Conversation aggregate identifier has not been initialized")
        return cast(str, aggregate_id)

    def update_title(self, new_title: str) -> bool:
        """Update the conversation title."""
        if self.state.title == new_title:
            return False
        self.state.on(
            self.register_event(  # type: ignore
                ConversationTitleUpdatedDomainEvent(
                    aggregate_id=self.id(),
                    new_title=new_title,
                )
            )
        )
        return True

    def add_message(
        self,
        role: MessageRole,
        content: str,
        message_id: str | None = None,
        status: MessageStatus = MessageStatus.COMPLETED,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Add a message to the conversation."""
        msg_id = message_id or str(uuid4())
        self.state.on(
            self.register_event(  # type: ignore
                MessageAddedDomainEvent(
                    aggregate_id=self.id(),
                    message_id=msg_id,
                    role=role.value,
                    content=content,
                    created_at=datetime.now(UTC),
                    status=status.value,
                    metadata=metadata,
                )
            )
        )
        return msg_id

    def add_user_message(self, content: str) -> str:
        """Add a user message to the conversation."""
        return self.add_message(MessageRole.USER, content)

    def add_assistant_message(
        self,
        content: str,
        status: MessageStatus = MessageStatus.COMPLETED,
    ) -> str:
        """Add an assistant message to the conversation."""
        return self.add_message(MessageRole.ASSISTANT, content, status=status)

    def add_tool_call(
        self,
        message_id: str,
        tool_name: str,
        arguments: dict[str, Any],
        call_id: str | None = None,
    ) -> str:
        """Add a tool call to a message."""
        cid = call_id or str(uuid4())
        self.state.on(
            self.register_event(  # type: ignore
                ToolCallAddedDomainEvent(
                    aggregate_id=self.id(),
                    message_id=message_id,
                    call_id=cid,
                    tool_name=tool_name,
                    arguments=arguments,
                )
            )
        )
        return cid

    def add_tool_result(
        self,
        message_id: str,
        call_id: str,
        tool_name: str,
        success: bool,
        result: Any,
        error: str | None = None,
        execution_time_ms: float | None = None,
    ) -> None:
        """Add a tool execution result to a message."""
        self.state.on(
            self.register_event(  # type: ignore
                ToolResultAddedDomainEvent(
                    aggregate_id=self.id(),
                    message_id=message_id,
                    call_id=call_id,
                    tool_name=tool_name,
                    success=success,
                    result=result,
                    error=error,
                    execution_time_ms=execution_time_ms,
                )
            )
        )

    def update_message_status(self, message_id: str, new_status: MessageStatus) -> bool:
        """Update the status of a message."""
        for msg in self.state.messages:
            if msg["id"] == message_id:
                if msg["status"] == new_status.value:
                    return False
                self.state.on(
                    self.register_event(  # type: ignore
                        MessageStatusUpdatedDomainEvent(
                            aggregate_id=self.id(),
                            message_id=message_id,
                            new_status=new_status.value,
                        )
                    )
                )
                return True
        return False

    def clear_messages(self, keep_system: bool = True) -> None:
        """Clear conversation messages."""
        self.state.on(
            self.register_event(  # type: ignore
                ConversationClearedDomainEvent(
                    aggregate_id=self.id(),
                    keep_system=keep_system,
                )
            )
        )

    def delete(self) -> None:
        """Mark the conversation as deleted."""
        self.state.on(
            self.register_event(  # type: ignore
                ConversationDeletedDomainEvent(
                    aggregate_id=self.id(),
                )
            )
        )

    def get_messages(self) -> list[Message]:
        """Get all messages as Message objects."""
        return [Message.from_dict(m) for m in self.state.messages]

    def get_context_messages(self, max_messages: int = 50) -> list[Message]:
        """Get messages for LLM context, respecting the max limit."""
        messages = self.get_messages()
        if not messages:
            return []

        system_messages = [m for m in messages if m.role == MessageRole.SYSTEM]
        other_messages = [m for m in messages if m.role != MessageRole.SYSTEM]

        max_other = max_messages - len(system_messages)
        recent_messages = other_messages[-max_other:] if max_other > 0 else []

        return system_messages + recent_messages

    def get_last_user_message(self) -> Message | None:
        """Get the last user message in the conversation."""
        messages = self.get_messages()
        for message in reversed(messages):
            if message.role == MessageRole.USER:
                return message
        return None

    def __len__(self) -> int:
        """Return the number of messages in the conversation."""
        return len(self.state.messages)

    # =========================================================================
    # LIFECYCLE METHODS
    # =========================================================================

    def start(self) -> None:
        """Start the conversation (first message exchange begins)."""
        if self.state.status != ConversationStatus.PENDING.value:
            return  # Already started
        self.state.on(
            self.register_event(  # type: ignore
                ConversationStartedDomainEvent(
                    aggregate_id=self.id(),
                )
            )
        )

    def pause(self) -> None:
        """Pause the conversation.

        Records the pause timestamp. When resumed, the deadline will be
        adjusted by the pause duration.
        """
        if self.state.status not in (ConversationStatus.ACTIVE.value, ConversationStatus.AWAITING_WIDGET.value):
            return  # Can only pause active conversations
        self.state.on(
            self.register_event(  # type: ignore
                ConversationPausedDomainEvent(
                    aggregate_id=self.id(),
                )
            )
        )

    def resume(self) -> None:
        """Resume a paused conversation.

        Adjusts the deadline by the pause duration if a deadline is set.
        """
        if self.state.status != ConversationStatus.PAUSED.value:
            return  # Can only resume paused conversations

        # Calculate pause duration and adjust deadline
        if self.state.paused_at and self.state.deadline:
            pause_duration = datetime.now(UTC) - self.state.paused_at
            new_deadline = self.state.deadline + pause_duration
            # Emit deadline updated event first
            self.state.on(
                self.register_event(  # type: ignore
                    DeadlineUpdatedDomainEvent(
                        aggregate_id=self.id(),
                        old_deadline=self.state.deadline,
                        new_deadline=new_deadline,
                        reason="pause_resume",
                    )
                )
            )

        self.state.on(
            self.register_event(  # type: ignore
                ConversationResumedDomainEvent(
                    aggregate_id=self.id(),
                )
            )
        )

    def complete(self, summary: dict[str, Any] | None = None) -> None:
        """Mark the conversation as completed."""
        self.state.on(
            self.register_event(  # type: ignore
                ConversationCompletedDomainEvent(
                    aggregate_id=self.id(),
                    summary=summary,
                )
            )
        )

    def terminate(self, reason: str = "") -> None:
        """Terminate the conversation early."""
        self.state.on(
            self.register_event(  # type: ignore
                ConversationTerminatedDomainEvent(
                    aggregate_id=self.id(),
                    reason=reason,
                )
            )
        )

    # =========================================================================
    # CLIENT ACTION METHODS (Widget interaction)
    # =========================================================================

    def request_client_action(self, action: dict[str, Any]) -> None:
        """Request a client action (widget response) from the user."""
        self.state.on(
            self.register_event(  # type: ignore
                ClientActionRequestedDomainEvent(
                    aggregate_id=self.id(),
                    action=action,
                )
            )
        )

    def receive_client_response(self, tool_call_id: str, response: Any) -> None:
        """Record the user's response to a client action."""
        self.state.on(
            self.register_event(  # type: ignore
                ClientResponseReceivedDomainEvent(
                    aggregate_id=self.id(),
                    tool_call_id=tool_call_id,
                    response=response,
                )
            )
        )

    # =========================================================================
    # TEMPLATE PROGRESS METHODS (for proactive/assessment conversations)
    # =========================================================================

    def record_generated_item(self, item: dict[str, Any]) -> None:
        """Record an item generated from a skill template."""
        self.state.on(
            self.register_event(  # type: ignore
                ItemGeneratedDomainEvent(
                    aggregate_id=self.id(),
                    item=item,
                )
            )
        )

    def record_item_answer(
        self,
        item_id: str,
        user_response: str,
        is_correct: bool | None = None,
        response_time_ms: int | None = None,
    ) -> None:
        """Record the user's answer to a generated item."""
        self.state.on(
            self.register_event(  # type: ignore
                ItemAnsweredDomainEvent(
                    aggregate_id=self.id(),
                    item_id=item_id,
                    user_response=user_response,
                    is_correct=is_correct,
                    response_time_ms=response_time_ms,
                )
            )
        )

    def advance_template(self) -> None:
        """Advance to the next item in the template."""
        current_index = 0
        if self.state.template_progress:
            current_index = self.state.template_progress.get("current_index", 0)
        self.state.on(
            self.register_event(  # type: ignore
                TemplateAdvancedDomainEvent(
                    aggregate_id=self.id(),
                    previous_index=current_index,
                    current_index=current_index + 1,
                )
            )
        )

    def get_current_template_index(self) -> int:
        """Get the current template item index."""
        if self.state.template_progress:
            return self.state.template_progress.get("current_index", 0)
        return 0

    def get_generated_items(self) -> list[dict[str, Any]]:
        """Get all generated items."""
        if self.state.template_progress:
            return self.state.template_progress.get("generated_items", [])
        return []

    def initialize_template(
        self,
        template_id: str,
        template_config: dict[str, Any],
        item_order: list[int],
        deadline: datetime | None = None,
    ) -> None:
        """Initialize template configuration for this conversation.

        Args:
            template_id: The template ID
            template_config: Client-safe template configuration
            item_order: Presentation order of items (indices into template.items)
            deadline: Absolute deadline (if max_duration is set)
        """
        self.state.on(
            self.register_event(  # type: ignore
                TemplateInitializedDomainEvent(
                    aggregate_id=self.id(),
                    template_id=template_id,
                    template_config=template_config,
                    item_order=item_order,
                    deadline=deadline,
                )
            )
        )

    def navigate_backward(self, to_index: int) -> bool:
        """Navigate backward to a previous item.

        Args:
            to_index: Target item index (in presentation order)

        Returns:
            True if navigation was successful, False otherwise
        """
        if self.state.template_progress is None:
            return False

        current_index = self.state.template_progress.get("current_index", 0)
        if to_index < 0 or to_index >= current_index:
            return False  # Can only go backward to previous items

        self.state.on(
            self.register_event(  # type: ignore
                TemplateNavigatedBackwardDomainEvent(
                    aggregate_id=self.id(),
                    from_index=current_index,
                    to_index=to_index,
                )
            )
        )
        return True

    def update_deadline(self, new_deadline: datetime | None, reason: str = "") -> None:
        """Update the conversation deadline.

        Args:
            new_deadline: New absolute deadline (None to remove deadline)
            reason: Reason for the update (e.g., 'pause_resume')
        """
        old_deadline = self.state.deadline
        self.state.on(
            self.register_event(  # type: ignore
                DeadlineUpdatedDomainEvent(
                    aggregate_id=self.id(),
                    old_deadline=old_deadline,
                    new_deadline=new_deadline,
                    reason=reason,
                )
            )
        )

    def record_item_score(
        self,
        item_id: str,
        score: float,
        max_score: float,
        is_correct: bool | None = None,
        content_id: str | None = None,
    ) -> None:
        """Record a score for an item response.

        Args:
            item_id: The item ID
            score: Score achieved
            max_score: Maximum possible score for this item
            is_correct: Whether the answer was correct (for scored items)
            content_id: Optional specific content ID within the item
        """
        self.state.on(
            self.register_event(  # type: ignore
                ItemScoreRecordedDomainEvent(
                    aggregate_id=self.id(),
                    item_id=item_id,
                    content_id=content_id,
                    score=score,
                    max_score=max_score,
                    is_correct=is_correct,
                )
            )
        )

    def get_item_order(self) -> list[int]:
        """Get the item presentation order."""
        if self.state.template_progress:
            return self.state.template_progress.get("item_order", [])
        return []

    def get_total_score(self) -> float:
        """Get the total accumulated score."""
        if self.state.template_progress:
            return self.state.template_progress.get("total_score", 0.0)
        return 0.0

    def get_max_possible_score(self) -> float:
        """Get the maximum possible score."""
        if self.state.template_progress:
            return self.state.template_progress.get("max_possible_score", 0.0)
        return 0.0

    def get_item_scores(self) -> dict[str, dict[str, Any]]:
        """Get all item scores."""
        if self.state.template_progress:
            return self.state.template_progress.get("item_scores", {})
        return {}

    def get_deadline(self) -> datetime | None:
        """Get the current deadline."""
        return self.state.deadline

    def get_template_config(self) -> dict[str, Any] | None:
        """Get the template configuration."""
        return self.state.template_config

    # =========================================================================
    # SHARING METHODS
    # =========================================================================

    def share_with(self, user_id: str, role: str, shared_by: str) -> bool:
        """Share this conversation with another user."""
        # Check if already shared with this user
        for share in self.state.shared_with:
            if share["user_id"] == user_id:
                return False  # Already shared

        self.state.on(
            self.register_event(  # type: ignore
                ConversationSharedDomainEvent(
                    aggregate_id=self.id(),
                    user_id=user_id,
                    role=role,
                    shared_by=shared_by,
                )
            )
        )
        return True

    def revoke_share(self, user_id: str, revoked_by: str) -> bool:
        """Revoke sharing from a user."""
        # Check if shared with this user
        found = any(share["user_id"] == user_id for share in self.state.shared_with)
        if not found:
            return False

        self.state.on(
            self.register_event(  # type: ignore
                ConversationShareRevokedDomainEvent(
                    aggregate_id=self.id(),
                    user_id=user_id,
                    revoked_by=revoked_by,
                )
            )
        )
        return True

    def is_shared_with(self, user_id: str) -> bool:
        """Check if conversation is shared with a specific user."""
        return any(share["user_id"] == user_id for share in self.state.shared_with)

    def get_share_role(self, user_id: str) -> str | None:
        """Get the share role for a specific user."""
        for share in self.state.shared_with:
            if share["user_id"] == user_id:
                return share["role"]
        return None

    # =========================================================================
    # PROPERTY ACCESSORS
    # =========================================================================

    @property
    def status(self) -> ConversationStatus:
        """Get the current status."""
        return ConversationStatus(self.state.status)

    @property
    def is_active(self) -> bool:
        """Check if conversation is active (can accept messages)."""
        return self.state.status in (
            ConversationStatus.ACTIVE.value,
            ConversationStatus.AWAITING_USER.value,
            ConversationStatus.AWAITING_WIDGET.value,
        )

    @property
    def is_paused(self) -> bool:
        """Check if conversation is paused."""
        return self.state.status == ConversationStatus.PAUSED.value

    @property
    def is_completed(self) -> bool:
        """Check if conversation is completed or terminated."""
        return self.state.status in (
            ConversationStatus.COMPLETED.value,
            ConversationStatus.TERMINATED.value,
            ConversationStatus.ARCHIVED.value,
        )

    @property
    def has_pending_action(self) -> bool:
        """Check if there's a pending client action."""
        return self.state.pending_action is not None

    @property
    def definition_id(self) -> str:
        """Get the definition ID."""
        return self.state.definition_id

    @property
    def owner_user_id(self) -> str:
        """Get the owner user ID."""
        return self.state.user_id
