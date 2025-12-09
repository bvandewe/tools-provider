"""Domain events for Conversation aggregate operations."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from neuroglia.data.abstractions import DomainEvent
from neuroglia.eventing.cloud_events.decorators import cloudevent


@cloudevent("conversation.created.v1")
@dataclass
class ConversationCreatedDomainEvent(DomainEvent):
    """Event raised when a new conversation is created."""

    aggregate_id: str
    user_id: str
    title: str | None
    system_prompt: str | None
    created_at: datetime
    updated_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        user_id: str,
        title: str | None,
        system_prompt: str | None,
        created_at: datetime,
        updated_at: datetime,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.user_id = user_id
        self.title = title
        self.system_prompt = system_prompt
        self.created_at = created_at
        self.updated_at = updated_at


@cloudevent("conversation.title.updated.v1")
@dataclass
class ConversationTitleUpdatedDomainEvent(DomainEvent):
    """Event raised when conversation title is updated."""

    aggregate_id: str
    new_title: str

    def __init__(
        self,
        aggregate_id: str,
        new_title: str,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.new_title = new_title


@cloudevent("conversation.message.added.v1")
@dataclass
class MessageAddedDomainEvent(DomainEvent):
    """Event raised when a message is added to the conversation."""

    aggregate_id: str
    message_id: str
    role: str  # MessageRole value
    content: str
    created_at: datetime
    status: str  # MessageStatus value
    metadata: dict[str, Any]

    def __init__(
        self,
        aggregate_id: str,
        message_id: str,
        role: str,
        content: str,
        created_at: datetime,
        status: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.message_id = message_id
        self.role = role
        self.content = content
        self.created_at = created_at
        self.status = status
        self.metadata = metadata or {}


@cloudevent("conversation.tool.called.v1")
@dataclass
class ToolCallAddedDomainEvent(DomainEvent):
    """Event raised when a tool call is added to a message."""

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
        arguments: dict[str, Any],
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.message_id = message_id
        self.call_id = call_id
        self.tool_name = tool_name
        self.arguments = arguments


@cloudevent("conversation.tool.result.v1")
@dataclass
class ToolResultAddedDomainEvent(DomainEvent):
    """Event raised when a tool execution result is added."""

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
        success: bool,
        result: Any,
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


@cloudevent("conversation.message.status.updated.v1")
@dataclass
class MessageStatusUpdatedDomainEvent(DomainEvent):
    """Event raised when a message status is updated."""

    aggregate_id: str
    message_id: str
    new_status: str  # MessageStatus value

    def __init__(
        self,
        aggregate_id: str,
        message_id: str,
        new_status: str,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.message_id = message_id
        self.new_status = new_status


@cloudevent("conversation.cleared.v1")
@dataclass
class ConversationClearedDomainEvent(DomainEvent):
    """Event raised when conversation messages are cleared."""

    aggregate_id: str
    keep_system: bool

    def __init__(
        self,
        aggregate_id: str,
        keep_system: bool,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.keep_system = keep_system


@cloudevent("conversation.deleted.v1")
@dataclass
class ConversationDeletedDomainEvent(DomainEvent):
    """Event raised when a conversation is deleted."""

    aggregate_id: str

    def __init__(
        self,
        aggregate_id: str,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
