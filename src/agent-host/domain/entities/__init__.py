"""Domain entities for Agent Host.

Aggregate roots following the AggregateRoot[TState, TKey] pattern.

The simplified architecture uses Conversation as the single AggregateRoot.
Agent is now a stateless service, not an entity.
"""

from domain.entities.conversation import Conversation, ConversationState

__all__ = [
    # Conversation aggregate - the only aggregate root
    "Conversation",
    "ConversationState",
]
