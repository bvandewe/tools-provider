"""MongoDB repository implementation for ConversationTemplate aggregate."""

from neuroglia.data.infrastructure.mongo import MotorRepository

from domain.entities import ConversationTemplate
from domain.repositories.template_repository import ConversationTemplateRepository


class MotorConversationTemplateRepository(MotorRepository[ConversationTemplate, str], ConversationTemplateRepository):
    """MongoDB-based repository for ConversationTemplate aggregate.

    Extends Neuroglia's MotorRepository to inherit standard CRUD operations
    and implements ConversationTemplateRepository for domain-specific query methods.

    Configured via MotorRepository.configure() in main.py.
    AggregateState fields are stored at the document root level.
    """

    async def get_all_async(self) -> list[ConversationTemplate]:
        """Retrieve all templates from MongoDB."""
        cursor = self.collection.find({})
        results = []
        async for doc in cursor:
            entity = self._deserialize_entity(doc)
            if entity:
                results.append(entity)
        return results

    async def get_proactive_async(self) -> list[ConversationTemplate]:
        """Retrieve all templates where agent_starts_first=True."""
        cursor = self.collection.find({"agent_starts_first": True})
        results = []
        async for doc in cursor:
            entity = self._deserialize_entity(doc)
            if entity:
                results.append(entity)
        return results

    async def get_assessments_async(self) -> list[ConversationTemplate]:
        """Retrieve all assessment templates (with scoring)."""
        # Assessment templates have passing_score_percent set (not None)
        cursor = self.collection.find({"passing_score_percent": {"$ne": None}})
        results = []
        async for doc in cursor:
            entity = self._deserialize_entity(doc)
            if entity:
                results.append(entity)
        return results

    async def get_by_creator_async(self, created_by: str) -> list[ConversationTemplate]:
        """Retrieve templates created by a specific user."""
        cursor = self.collection.find({"created_by": created_by})
        results = []
        async for doc in cursor:
            entity = self._deserialize_entity(doc)
            if entity:
                results.append(entity)
        return results
