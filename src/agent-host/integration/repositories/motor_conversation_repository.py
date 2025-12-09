"""MongoDB repository implementation for Conversation."""

from neuroglia.data.infrastructure.mongo import MotorRepository

from domain.entities.conversation import Conversation
from domain.repositories.conversation_repository import ConversationRepository


class MotorConversationRepository(MotorRepository[Conversation, str], ConversationRepository):
    """
    MongoDB-based repository for Conversation entities.

    Extends Neuroglia's MotorRepository to inherit standard CRUD operations
    and implements ConversationRepository for custom query methods.

    Uses state-based persistence with MongoDB (simplified from CQRS).

    Access AggregateState fields directly at the document root.
    """

    async def get_all_async(self) -> list[Conversation]:
        """Retrieve all conversations from MongoDB.

        Delegates to MotorRepository's built-in get_all_async method.
        """
        return await super().get_all_async()

    async def get_by_user_async(self, user_id: str) -> list[Conversation]:
        """Retrieve conversations for a specific user.

        Uses native MongoDB filter. The Neuroglia MotorRepository flattens
        the AggregateState fields to the document root, so we query user_id
        directly (not state.user_id).
        """
        # Query user_id at root level (Neuroglia flattens state to root)
        # Sort by updated_at descending (most recent first)
        cursor = self.collection.find({"user_id": user_id}).sort("updated_at", -1)
        results = []
        async for doc in cursor:
            entity = self._deserialize_entity(doc)
            if entity:
                results.append(entity)
        return results

    async def get_recent_by_user_async(self, user_id: str, limit: int = 10) -> list[Conversation]:
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
