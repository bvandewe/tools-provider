"""Domain entities for Agent Host.

Aggregate roots following the AggregateRoot[TState, TKey] pattern.
"""

from domain.entities.conversation import Conversation, ConversationState

__all__ = [
    "Conversation",
    "ConversationState",
]
