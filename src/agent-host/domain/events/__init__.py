"""Domain events for Agent Host."""

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
from domain.events.user import UserLoggedInDomainEvent, UserLoggedOutDomainEvent

__all__ = [
    # Conversation events
    "ConversationCreatedDomainEvent",
    "ConversationTitleUpdatedDomainEvent",
    "MessageAddedDomainEvent",
    "ToolCallAddedDomainEvent",
    "ToolResultAddedDomainEvent",
    "MessageStatusUpdatedDomainEvent",
    "ConversationClearedDomainEvent",
    "ConversationDeletedDomainEvent",
    # Session events
    "SessionCreatedDomainEvent",
    "SessionStartedDomainEvent",
    "SessionCompletedDomainEvent",
    "SessionTerminatedDomainEvent",
    "SessionExpiredDomainEvent",
    "SessionItemStartedDomainEvent",
    "SessionItemCompletedDomainEvent",
    "PendingActionSetDomainEvent",
    "PendingActionClearedDomainEvent",
    "ResponseSubmittedDomainEvent",
    "SessionStatusChangedDomainEvent",
    # User events
    "UserLoggedInDomainEvent",
    "UserLoggedOutDomainEvent",
]
