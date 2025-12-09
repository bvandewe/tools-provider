"""Abstract repository for Conversation read model queries.

This follows CQRS where:
- Write model: Repository[Conversation, str] (EventSourcingRepository) persists to KurrentDB
- Read model: ConversationRepository queries from MongoDB
"""

from abc import ABC, abstractmethod

from neuroglia.data.infrastructure.abstractions import Repository

from domain.entities.conversation import Conversation


class ConversationRepository(Repository[Conversation, str], ABC):
    """Abstract repository for Conversation

    This repository provides optimized query methods for the Conversation Entity (MongoDB).
    It centralizes query logic that would otherwise be repeated across application handlers.
    """

    @abstractmethod
    async def get_all_async(self) -> list[Conversation]:
        """Retrieve all conversations from the read model."""
        pass

    @abstractmethod
    async def get_by_user_async(self, user_id: str) -> list[Conversation]:
        """Retrieve conversations for a specific user."""
        pass

    @abstractmethod
    async def get_recent_by_user_async(self, user_id: str, limit: int = 10) -> list[Conversation]:
        """Retrieve the most recent conversations for a user."""
        pass
