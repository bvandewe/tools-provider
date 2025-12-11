"""Domain entities for Agent Host.

Aggregate roots following the AggregateRoot[TState, TKey] pattern.
"""

from domain.entities.conversation import Conversation, ConversationState
from domain.entities.session import DomainError, Session, SessionState

__all__ = [
    "Conversation",
    "ConversationState",
    "Session",
    "SessionState",
    "DomainError",
]
