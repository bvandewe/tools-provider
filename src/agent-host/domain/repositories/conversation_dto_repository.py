"""Abstract repository for ConversationDto read model queries.

This follows CQRS where:
- Write model: Repository[Conversation, str] (EventSourcingRepository) persists to EventStoreDB
- Read model: ConversationDtoRepository queries from MongoDB
"""

from abc import ABC, abstractmethod

from neuroglia.data.infrastructure.abstractions import Repository

from integration.models.conversation_dto import ConversationDto


class ConversationDtoRepository(Repository[ConversationDto, str], ABC):
    """Abstract repository for ConversationDto read model queries.

    This repository provides optimized query methods for the read model (MongoDB).
    It centralizes query logic that would otherwise be repeated across query handlers.

    For write operations (create, update, delete), use Repository[Conversation, str]
    which handles the write model (EventStoreDB) with automatic event publishing.
    """

    @abstractmethod
    async def get_all_async(self) -> list[ConversationDto]:
        """Retrieve all conversations from the read model."""
        pass

    @abstractmethod
    async def get_by_user_async(self, user_id: str) -> list[ConversationDto]:
        """Retrieve conversations for a specific user."""
        pass

    @abstractmethod
    async def get_recent_by_user_async(self, user_id: str, limit: int = 10) -> list[ConversationDto]:
        """Retrieve the most recent conversations for a user."""
        pass
