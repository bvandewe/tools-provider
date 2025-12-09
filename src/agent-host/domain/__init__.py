"""Domain layer for Agent Host.

Contains:
- entities/: Aggregate roots using AggregateRoot[TState, TKey] pattern
- events/: Domain events with @cloudevent decorators
- models/: Value objects and domain models
- repositories/: Abstract repository interfaces for read model
"""

from domain.entities import Conversation, ConversationState
from domain.events import (
    ConversationClearedDomainEvent,
    ConversationCreatedDomainEvent,
    ConversationDeletedDomainEvent,
    ConversationTitleUpdatedDomainEvent,
    MessageAddedDomainEvent,
    MessageStatusUpdatedDomainEvent,
    ToolCallAddedDomainEvent,
    ToolResultAddedDomainEvent,
)
from domain.models import Message, MessageRole, MessageStatus, Tool, ToolCall, ToolResult
from domain.repositories import ConversationRepository

__all__ = [
    # Entities
    "Conversation",
    "ConversationState",
    # Events
    "ConversationCreatedDomainEvent",
    "ConversationTitleUpdatedDomainEvent",
    "MessageAddedDomainEvent",
    "ToolCallAddedDomainEvent",
    "ToolResultAddedDomainEvent",
    "MessageStatusUpdatedDomainEvent",
    "ConversationClearedDomainEvent",
    "ConversationDeletedDomainEvent",
    # Models
    "Message",
    "MessageRole",
    "MessageStatus",
    "Tool",
    "ToolCall",
    "ToolResult",
    # Repositories
    "ConversationRepository",
]
