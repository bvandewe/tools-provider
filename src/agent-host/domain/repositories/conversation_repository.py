"""Abstract repository for Conversation aggregate.

This repository extends the generic Repository interface with
domain-specific query methods for Conversation entities.

Implementation: MotorConversationRepository (MongoDB)
Configuration: MotorRepository.configure() in main.py
"""

from abc import ABC, abstractmethod

from neuroglia.data.infrastructure.abstractions import Repository

from domain.entities.conversation import Conversation


class ConversationRepository(Repository[Conversation, str], ABC):
    """Abstract repository for Conversation aggregate.

    This repository provides domain-specific query methods for Conversation entities.
    It centralizes query logic that would otherwise be repeated across handlers.

    Implementation: MotorConversationRepository
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
