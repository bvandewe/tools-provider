"""Get conversations query with handler."""

from dataclasses import dataclass
from typing import Any

from neuroglia.core import OperationResult
from neuroglia.mediation import Query, QueryHandler

from domain.repositories.conversation_dto_repository import ConversationDtoRepository
from integration.models.conversation_dto import ConversationDto


@dataclass
class GetConversationsQuery(Query[OperationResult[list[ConversationDto]]]):
    """Query to retrieve all conversations for a user."""

    user_info: dict[str, Any]
    limit: int | None = None


class GetConversationsQueryHandler(QueryHandler[GetConversationsQuery, OperationResult[list[ConversationDto]]]):
    """Handle conversations retrieval for a user.

    Uses ConversationDtoRepository for MongoDB queries (read model).
    """

    def __init__(self, conversation_repository: ConversationDtoRepository):
        super().__init__()
        self.conversation_repository = conversation_repository

    async def handle_async(self, request: GetConversationsQuery) -> OperationResult[list[ConversationDto]]:
        """Handle get conversations query."""
        query = request

        # Get user ID
        user_id = query.user_info.get("sub") or query.user_info.get("user_id") or query.user_info.get("preferred_username")
        if not user_id:
            return self.ok([])  # No user ID means no conversations

        # Get conversations for the user
        if query.limit:
            conversations = await self.conversation_repository.get_recent_by_user_async(user_id, query.limit)
        else:
            conversations = await self.conversation_repository.get_by_user_async(user_id)

        return self.ok(conversations)
