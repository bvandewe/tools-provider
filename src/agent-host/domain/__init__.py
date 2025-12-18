"""Domain layer for Agent Host.

Contains:
- entities/: Aggregate roots using AggregateRoot[TState, TKey] pattern
- enums/: Domain enumerations (AgentType, AgentStatus, etc.)
- events/: Domain events with @cloudevent decorators
- exceptions/: Domain-specific exceptions
- models/: Value objects and domain models
- repositories/: Abstract repository interfaces for read model
"""

from domain.entities import Conversation, ConversationState
from domain.enums import AgentStatus, AssignmentRole
from domain.events import (
    # Conversation events
    ConversationClearedDomainEvent,
    ConversationCreatedDomainEvent,
    ConversationDeletedDomainEvent,
    ConversationTitleUpdatedDomainEvent,
    MessageAddedDomainEvent,
    MessageStatusUpdatedDomainEvent,
    ToolCallAddedDomainEvent,
    ToolResultAddedDomainEvent,
)
from domain.exceptions import (
    AgentArchivedError,
    AgentNotFoundError,
    DomainError,
    InvalidAssignmentRoleError,
    InvalidToolCallIdError,
    NoActiveSessionError,
    NotSuspendedError,
    SessionAlreadyActiveError,
    UserAlreadyAssignedError,
)
from domain.models import (
    ClientAction,
    ClientResponse,
    ExecutionState,
    LlmMessageSnapshot,
    Message,
    MessageRole,
    MessageStatus,
    PendingToolCall,
    Tool,
    ToolCall,
    ToolResult,
)
from domain.repositories import ConversationRepository

__all__ = [
    # Entities
    "Conversation",
    "ConversationState",
    # Enums
    "AgentStatus",
    "AssignmentRole",
    # Exceptions
    "DomainError",
    "AgentNotFoundError",
    "AgentArchivedError",
    "SessionAlreadyActiveError",
    "NoActiveSessionError",
    "InvalidToolCallIdError",
    "NotSuspendedError",
    "UserAlreadyAssignedError",
    "InvalidAssignmentRoleError",
    # Conversation events
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
    # Value objects (new)
    "ClientAction",
    "ClientResponse",
    "ExecutionState",
    "LlmMessageSnapshot",
    "PendingToolCall",
    # Repositories
    "ConversationRepository",
]
