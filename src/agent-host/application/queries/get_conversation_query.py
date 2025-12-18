"""Get conversation query with handler."""

from dataclasses import dataclass
from typing import Any

from neuroglia.core import OperationResult
from neuroglia.mediation import Query, QueryHandler

from domain.repositories.conversation_dto_repository import ConversationDtoRepository
from integration.models.conversation_dto import ConversationDto


@dataclass
class GetConversationQuery(Query[OperationResult[ConversationDto | None]]):
    """Query to retrieve a specific conversation."""

    conversation_id: str
    user_info: dict[str, Any]


class GetConversationQueryHandler(QueryHandler[GetConversationQuery, OperationResult[ConversationDto | None]]):
    """Handle conversation retrieval with ownership validation.

    Uses ConversationDtoRepository for MongoDB queries (read model).
    """

    def __init__(self, conversation_repository: ConversationDtoRepository):
        super().__init__()
        self.conversation_repository = conversation_repository

    async def handle_async(self, request: GetConversationQuery) -> OperationResult[ConversationDto | None]:
        """Handle get conversation query."""
        query = request

        # Get the conversation
        conversation = await self.conversation_repository.get_async(query.conversation_id)
        if conversation is None:
            return self.not_found(ConversationDto, query.conversation_id)

        # Verify user owns the conversation
        user_id = query.user_info.get("sub") or query.user_info.get("user_id") or query.user_info.get("preferred_username")
        if user_id and conversation.user_id != user_id:
            return self.forbidden("You don't have access to this conversation")

        return self.ok(conversation)
