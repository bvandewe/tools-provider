"""Abstract repository for AgentDefinition aggregate.

This repository extends the generic Repository interface with
domain-specific query methods for AgentDefinition entities.

Implementation: MotorRepository (via MotorRepository.configure in main.py)
"""

from abc import ABC, abstractmethod

from neuroglia.data.infrastructure.abstractions import Repository

from domain.entities import AgentDefinition


class AgentDefinitionRepository(Repository[AgentDefinition, str], ABC):
    """Abstract repository for AgentDefinition aggregate.

    This repository provides domain-specific query methods for AgentDefinition entities.
    It centralizes query logic that would otherwise be repeated across handlers.
    """

    @abstractmethod
    async def get_all_async(self) -> list[AgentDefinition]:
        """Retrieve all definitions from the repository."""
        pass

    @abstractmethod
    async def get_by_owner_async(self, owner_user_id: str) -> list[AgentDefinition]:
        """Retrieve definitions owned by a specific user."""
        pass

    @abstractmethod
    async def get_public_async(self) -> list[AgentDefinition]:
        """Retrieve all public definitions."""
        pass
