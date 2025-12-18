"""Abstract repository for AgentDefinition read model queries.

AgentDefinition is a state-based entity (stored in MongoDB, not event-sourced)
that defines agent behavior templates.
"""

from abc import ABC, abstractmethod

from neuroglia.data.infrastructure.abstractions import Repository

from domain.models.agent_definition import AgentDefinition


class DefinitionRepository(Repository[AgentDefinition, str], ABC):
    """Abstract repository for AgentDefinition.

    This repository provides query methods for AgentDefinitions stored in MongoDB.
    Unlike event-sourced aggregates, AgentDefinitions are simple state-based entities.
    """

    @abstractmethod
    async def get_all_async(self) -> list[AgentDefinition]:
        """Retrieve all definitions from the read model."""
        pass

    @abstractmethod
    async def get_by_owner_async(self, owner_user_id: str) -> list[AgentDefinition]:
        """Retrieve definitions owned by a specific user."""
        pass

    @abstractmethod
    async def get_public_async(self) -> list[AgentDefinition]:
        """Retrieve all public definitions."""
        pass

    @abstractmethod
    async def ensure_defaults_async(self) -> None:
        """Ensure default definitions exist in the database."""
        pass
