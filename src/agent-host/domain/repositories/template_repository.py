"""Abstract repository for ConversationTemplate aggregate.

This repository extends the generic Repository interface with
domain-specific query methods for ConversationTemplate entities.

Implementation: MotorRepository (via MotorRepository.configure in main.py)
"""

from abc import ABC, abstractmethod

from neuroglia.data.infrastructure.abstractions import Repository

from domain.entities import ConversationTemplate


class ConversationTemplateRepository(Repository[ConversationTemplate, str], ABC):
    """Abstract repository for ConversationTemplate aggregate.

    This repository provides domain-specific query methods for ConversationTemplate entities.
    It centralizes query logic that would otherwise be repeated across handlers.
    """

    @abstractmethod
    async def get_all_async(self) -> list[ConversationTemplate]:
        """Retrieve all templates from the repository."""
        pass

    @abstractmethod
    async def get_proactive_async(self) -> list[ConversationTemplate]:
        """Retrieve all templates where agent_starts_first=True."""
        pass

    @abstractmethod
    async def get_assessments_async(self) -> list[ConversationTemplate]:
        """Retrieve all assessment templates (with scoring)."""
        pass

    @abstractmethod
    async def get_by_creator_async(self, created_by: str) -> list[ConversationTemplate]:
        """Retrieve templates created by a specific user."""
        pass
