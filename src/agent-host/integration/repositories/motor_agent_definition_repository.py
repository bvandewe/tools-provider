"""MongoDB repository implementation for AgentDefinition aggregate."""

from neuroglia.data.infrastructure.mongo import MotorRepository

from domain.entities import AgentDefinition
from domain.repositories.definition_repository import AgentDefinitionRepository


class MotorAgentDefinitionRepository(MotorRepository[AgentDefinition, str], AgentDefinitionRepository):
    """MongoDB-based repository for AgentDefinition aggregate.

    Extends Neuroglia's MotorRepository to inherit standard CRUD operations
    and implements AgentDefinitionRepository for domain-specific query methods.

    Configured via MotorRepository.configure() in main.py.
    AggregateState fields are stored at the document root level.
    """

    async def get_all_async(self) -> list[AgentDefinition]:
        """Retrieve all definitions from MongoDB."""
        cursor = self.collection.find({})
        results = []
        async for doc in cursor:
            entity = self._deserialize_entity(doc)
            if entity:
                results.append(entity)
        return results

    async def get_by_owner_async(self, owner_user_id: str) -> list[AgentDefinition]:
        """Retrieve definitions owned by a specific user."""
        cursor = self.collection.find({"owner_user_id": owner_user_id})
        results = []
        async for doc in cursor:
            entity = self._deserialize_entity(doc)
            if entity:
                results.append(entity)
        return results

    async def get_public_async(self) -> list[AgentDefinition]:
        """Retrieve all public definitions."""
        cursor = self.collection.find({"is_public": True})
        results = []
        async for doc in cursor:
            entity = self._deserialize_entity(doc)
            if entity:
                results.append(entity)
        return results
