"""MongoDB repository implementation for AgentDefinitionDto.

This is the ReadModel repository for AgentDefinitionDto, which is a projection
of the AgentDefinition aggregate events from EventStoreDB.
"""

import logging

from neuroglia.data.infrastructure.mongo import MotorRepository

from domain.repositories.agent_definition_dto_repository import AgentDefinitionDtoRepository
from integration.models.definition_dto import AgentDefinitionDto

logger = logging.getLogger(__name__)


class MotorAgentDefinitionDtoRepository(MotorRepository[AgentDefinitionDto, str], AgentDefinitionDtoRepository):
    """
    MongoDB-based repository for AgentDefinitionDto projections.

    Extends Neuroglia's MotorRepository to inherit standard CRUD operations
    and implements AgentDefinitionDtoRepository for custom query methods.

    This is the ReadModel repository - DTOs are projected from AgentDefinition
    aggregate events by the projection handlers.
    """

    async def get_all_async(self) -> list[AgentDefinitionDto]:
        """Retrieve all definition DTOs from MongoDB.

        Delegates to MotorRepository's built-in get_all_async method.
        """
        return await super().get_all_async()

    async def get_by_owner_async(self, owner_user_id: str) -> list[AgentDefinitionDto]:
        """Retrieve definition DTOs owned by a specific user.

        Args:
            owner_user_id: The user ID to filter by

        Returns:
            List of AgentDefinitionDtos owned by the user
        """
        cursor = self.collection.find({"owner_user_id": owner_user_id}).sort("name", 1)
        results = []
        async for doc in cursor:
            entity = self._deserialize_entity(doc)
            if entity:
                results.append(entity)
        return results

    async def get_public_async(self) -> list[AgentDefinitionDto]:
        """Retrieve all public definition DTOs.

        Returns:
            List of public AgentDefinitionDtos
        """
        cursor = self.collection.find({"is_public": True}).sort("name", 1)
        results = []
        async for doc in cursor:
            entity = self._deserialize_entity(doc)
            if entity:
                results.append(entity)
        return results
