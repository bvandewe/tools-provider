"""MongoDB repository implementation for AgentDefinition."""

import logging

from neuroglia.data.infrastructure.mongo import MotorRepository

from domain.models.agent_definition import (
    DEFAULT_REACTIVE_AGENT,
    AgentDefinition,
)
from domain.repositories.definition_repository import DefinitionRepository

logger = logging.getLogger(__name__)


class MotorDefinitionRepository(MotorRepository[AgentDefinition, str], DefinitionRepository):
    """
    MongoDB-based repository for AgentDefinition entities.

    Extends Neuroglia's MotorRepository to inherit standard CRUD operations
    and implements DefinitionRepository for custom query methods.

    AgentDefinitions are state-based entities (not event-sourced) that define
    agent behavior templates.
    """

    # Default definitions seeded on startup
    # Note: Proactive agents require ConversationTemplates (seeded separately)
    DEFAULT_DEFINITIONS = [
        DEFAULT_REACTIVE_AGENT,
    ]

    async def get_all_async(self) -> list[AgentDefinition]:
        """Retrieve all definitions from MongoDB.

        Delegates to MotorRepository's built-in get_all_async method.
        """
        return await super().get_all_async()

    async def get_by_owner_async(self, owner_user_id: str) -> list[AgentDefinition]:
        """Retrieve definitions owned by a specific user.

        Args:
            owner_user_id: The user ID to filter by

        Returns:
            List of AgentDefinitions owned by the user
        """
        cursor = self.collection.find({"owner_user_id": owner_user_id}).sort("name", 1)
        results = []
        async for doc in cursor:
            entity = self._deserialize_entity(doc)
            if entity:
                results.append(entity)
        return results

    async def get_public_async(self) -> list[AgentDefinition]:
        """Retrieve all public definitions.

        Returns:
            List of public AgentDefinitions
        """
        cursor = self.collection.find({"is_public": True}).sort("name", 1)
        results = []
        async for doc in cursor:
            entity = self._deserialize_entity(doc)
            if entity:
                results.append(entity)
        return results

    async def ensure_defaults_async(self) -> None:
        """Ensure default definitions exist in MongoDB.

        Called on application startup to seed default agents.
        Uses upsert to avoid duplicates.
        """
        for defn in self.DEFAULT_DEFINITIONS:
            existing = await self.get_async(defn.id)
            if existing is None:
                await self.add_async(defn)
                logger.info(f"Created default definition: {defn.id} ({defn.name})")
            else:
                logger.debug(f"Default definition already exists: {defn.id}")
