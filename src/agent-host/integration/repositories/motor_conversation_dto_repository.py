"""MongoDB repository implementation for ConversationDto read model."""

from neuroglia.data.infrastructure.mongo import MotorRepository

from domain.repositories.conversation_dto_repository import ConversationDtoRepository
from integration.models.conversation_dto import ConversationDto


class MotorConversationDtoRepository(MotorRepository[ConversationDto, str], ConversationDtoRepository):
    """
    MongoDB-based repository for ConversationDto read model queries.

    Extends Neuroglia's MotorRepository to inherit standard CRUD operations
    and implements ConversationDtoRepository for custom query methods.

    This follows CQRS: Query handlers use this repository to query the read model,
    while command handlers use EventSourcingRepository for the write model.
    """

    async def get_all_async(self) -> list[ConversationDto]:
        """Retrieve all conversations from MongoDB.

        Delegates to MotorRepository's built-in get_all_async method.
        """
        return await super().get_all_async()

    async def get_by_user_async(self, user_id: str) -> list[ConversationDto]:
        """Retrieve conversations for a specific user.

        Uses native MongoDB filter with sort by updated_at descending.
        """
        cursor = self.collection.find({"user_id": user_id}).sort("updated_at", -1)
        results = []
        async for doc in cursor:
            entity = self._deserialize_entity(doc)
            if entity:
                results.append(entity)
        return results

    async def get_recent_by_user_async(self, user_id: str, limit: int = 10) -> list[ConversationDto]:
        """Retrieve the most recent conversations for a user.

        Uses native MongoDB filter with sort and limit.
        """
        cursor = self.collection.find({"user_id": user_id}).sort("updated_at", -1).limit(limit)
        results = []
        async for doc in cursor:
            entity = self._deserialize_entity(doc)
            if entity:
                results.append(entity)
        return results
