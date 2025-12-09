"""Conversation aggregate definition using the AggregateState pattern.

DomainEvents are appended/aggregated in the Conversation and the
repository publishes them via Mediator after the Conversation was persisted.
"""

from datetime import datetime, timezone
from typing import Any, Optional, cast
from uuid import uuid4

from domain.events.conversation import (
    ConversationClearedDomainEvent,
    ConversationCreatedDomainEvent,
    ConversationDeletedDomainEvent,
    ConversationTitleUpdatedDomainEvent,
    MessageAddedDomainEvent,
    MessageStatusUpdatedDomainEvent,
    ToolCallAddedDomainEvent,
    ToolResultAddedDomainEvent,
)
from domain.models.message import Message, MessageRole, MessageStatus
from multipledispatch import dispatch
from neuroglia.data.abstractions import AggregateRoot, AggregateState


class ConversationState(AggregateState[str]):
    """Encapsulates the persisted state for the Conversation aggregate."""

    id: str
    user_id: str
    title: Optional[str]
    system_prompt: Optional[str]
    messages: list[dict[str, Any]]  # Serialized message data
    created_at: datetime
    updated_at: datetime

    def __init__(self) -> None:
        super().__init__()
        self.id = ""
        self.user_id = ""
        self.title = None
        self.system_prompt = None
        self.messages = []
        now = datetime.now(timezone.utc)
        self.created_at = now
        self.updated_at = now

    @dispatch(ConversationCreatedDomainEvent)
    def on(self, event: ConversationCreatedDomainEvent) -> None:  # type: ignore[override]
        """Apply the creation event to the state."""
        self.id = event.aggregate_id
        self.user_id = event.user_id
        self.title = event.title
        self.system_prompt = event.system_prompt
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
        self.updated_at = datetime.now(timezone.utc)

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
        self.updated_at = datetime.now(timezone.utc)

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
        self.updated_at = datetime.now(timezone.utc)

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
        self.updated_at = datetime.now(timezone.utc)

    @dispatch(MessageStatusUpdatedDomainEvent)
    def on(self, event: MessageStatusUpdatedDomainEvent) -> None:  # type: ignore[override]
        """Apply the message status updated event to the state."""
        for msg in self.messages:
            if msg["id"] == event.message_id:
                msg["status"] = event.new_status
                break
        self.updated_at = datetime.now(timezone.utc)

    @dispatch(ConversationClearedDomainEvent)
    def on(self, event: ConversationClearedDomainEvent) -> None:  # type: ignore[override]
        """Apply the conversation cleared event to the state."""
        if event.keep_system:
            self.messages = [m for m in self.messages if m["role"] == MessageRole.SYSTEM.value]
        else:
            self.messages = []
        self.updated_at = datetime.now(timezone.utc)

    @dispatch(ConversationDeletedDomainEvent)
    def on(self, event: ConversationDeletedDomainEvent) -> None:  # type: ignore[override]
        """Apply the deleted event to the state."""
        self.updated_at = datetime.now(timezone.utc)


class Conversation(AggregateRoot[ConversationState, str]):
    """Conversation aggregate root following the AggregateState pattern."""

    def __init__(
        self,
        user_id: str,
        title: Optional[str] = None,
        system_prompt: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        conversation_id: Optional[str] = None,
    ) -> None:
        super().__init__()
        aggregate_id = conversation_id or str(uuid4())
        created_time = created_at or datetime.now(timezone.utc)
        updated_time = updated_at or created_time

        self.state.on(
            self.register_event(  # type: ignore
                ConversationCreatedDomainEvent(
                    aggregate_id=aggregate_id,
                    user_id=user_id,
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
        message_id: Optional[str] = None,
        status: MessageStatus = MessageStatus.COMPLETED,
        metadata: Optional[dict[str, Any]] = None,
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
                    created_at=datetime.now(timezone.utc),
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
        call_id: Optional[str] = None,
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
        error: Optional[str] = None,
        execution_time_ms: Optional[float] = None,
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

    def get_last_user_message(self) -> Optional[Message]:
        """Get the last user message in the conversation."""
        messages = self.get_messages()
        for message in reversed(messages):
            if message.role == MessageRole.USER:
                return message
        return None

    def __len__(self) -> int:
        """Return the number of messages in the conversation."""
        return len(self.state.messages)
