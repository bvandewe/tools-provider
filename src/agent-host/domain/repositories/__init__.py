"""Domain repositories package.

Contains abstract repository interfaces for the read model.
Implementations are in src/integration/repositories/.

This follows CQRS where:
- Write model: Repository[Conversation, str] (EventSourcingRepository) persists to KurrentDB
- Read model: ConversationDtoRepository queries from MongoDB
"""

from domain.repositories.conversation_repository import ConversationRepository

__all__: list[str] = [
    "ConversationRepository",
]
