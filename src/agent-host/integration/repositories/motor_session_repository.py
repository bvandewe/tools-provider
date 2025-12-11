"""MongoDB repository implementation for Session."""

from neuroglia.data.infrastructure.mongo import MotorRepository

from domain.entities.session import Session
from domain.repositories.session_repository import SessionRepository


class MotorSessionRepository(MotorRepository[Session, str], SessionRepository):
    """
    MongoDB-based repository for Session entities.

    Extends Neuroglia's MotorRepository to inherit standard CRUD operations
    and implements SessionRepository for custom query methods.

    Uses state-based persistence with MongoDB.

    Access AggregateState fields directly at the document root.
    """

    async def get_all_async(self) -> list[Session]:
        """Retrieve all sessions from MongoDB.

        Delegates to MotorRepository's built-in get_all_async method.
        """
        return await super().get_all_async()

    async def get_by_user_async(self, user_id: str) -> list[Session]:
        """Retrieve sessions for a specific user.

        Uses native MongoDB filter. The Neuroglia MotorRepository flattens
        the AggregateState fields to the document root, so we query user_id
        directly (not state.user_id).
        """
        cursor = self.collection.find({"user_id": user_id}).sort("created_at", -1)
        results = []
        async for doc in cursor:
            entity = self._deserialize_entity(doc)
            if entity:
                results.append(entity)
        return results

    async def get_active_by_user_async(self, user_id: str) -> list[Session]:
        """Retrieve active sessions for a user.

        Active sessions are those with status in:
        - pending
        - active
        - awaiting_client_action
        """
        active_statuses = ["pending", "active", "awaiting_client_action"]
        cursor = self.collection.find({"user_id": user_id, "status": {"$in": active_statuses}}).sort("created_at", -1)
        results = []
        async for doc in cursor:
            entity = self._deserialize_entity(doc)
            if entity:
                results.append(entity)
        return results

    async def get_by_conversation_async(self, conversation_id: str) -> Session | None:
        """Retrieve a session by its linked conversation ID."""
        doc = await self.collection.find_one({"conversation_id": conversation_id})
        if doc is None:
            return None
        return self._deserialize_entity(doc)

    async def get_by_type_async(self, user_id: str, session_type: str) -> list[Session]:
        """Retrieve sessions of a specific type for a user."""
        cursor = self.collection.find({"user_id": user_id, "session_type": session_type}).sort("created_at", -1)
        results = []
        async for doc in cursor:
            entity = self._deserialize_entity(doc)
            if entity:
                results.append(entity)
        return results
