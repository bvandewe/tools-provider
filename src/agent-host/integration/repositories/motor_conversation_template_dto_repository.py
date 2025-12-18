"""MongoDB repository implementation for ConversationTemplateDto.

This is the ReadModel repository for ConversationTemplateDto, which is a projection
of the ConversationTemplate aggregate events from EventStoreDB.
"""

import logging

from neuroglia.data.infrastructure.mongo import MotorRepository

from domain.repositories.conversation_template_dto_repository import ConversationTemplateDtoRepository
from integration.models.template_dto import ConversationTemplateDto

logger = logging.getLogger(__name__)


class MotorConversationTemplateDtoRepository(MotorRepository[ConversationTemplateDto, str], ConversationTemplateDtoRepository):
    """
    MongoDB-based repository for ConversationTemplateDto projections.

    Extends Neuroglia's MotorRepository to inherit standard CRUD operations
    and implements ConversationTemplateDtoRepository for custom query methods.

    This is the ReadModel repository - DTOs are projected from ConversationTemplate
    aggregate events by the projection handlers.
    """

    async def get_all_async(self) -> list[ConversationTemplateDto]:
        """Retrieve all template DTOs from MongoDB.

        Delegates to MotorRepository's built-in get_all_async method.
        """
        return await super().get_all_async()

    async def get_by_creator_async(self, created_by: str) -> list[ConversationTemplateDto]:
        """Retrieve template DTOs created by a specific user.

        Args:
            created_by: The user ID who created the templates

        Returns:
            List of ConversationTemplateDtos created by the user
        """
        cursor = self.collection.find({"created_by": created_by}).sort("name", 1)
        results = []
        async for doc in cursor:
            entity = self._deserialize_entity(doc)
            if entity:
                results.append(entity)
        return results

    async def get_proactive_async(self) -> list[ConversationTemplateDto]:
        """Retrieve all proactive template DTOs (agent_starts_first=True).

        Returns:
            List of proactive ConversationTemplateDtos
        """
        cursor = self.collection.find({"agent_starts_first": True}).sort("name", 1)
        results = []
        async for doc in cursor:
            entity = self._deserialize_entity(doc)
            if entity:
                results.append(entity)
        return results

    async def get_assessments_async(self) -> list[ConversationTemplateDto]:
        """Retrieve all assessment template DTOs (passing_score_percent is set).

        Returns:
            List of assessment ConversationTemplateDtos
        """
        cursor = self.collection.find({"passing_score_percent": {"$ne": None}}).sort("name", 1)
        results = []
        async for doc in cursor:
            entity = self._deserialize_entity(doc)
            if entity:
                results.append(entity)
        return results
