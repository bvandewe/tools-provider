"""Get conversation query with handler."""

from dataclasses import dataclass
from typing import Any, Optional

from domain.entities.conversation import Conversation
from domain.repositories.conversation_repository import ConversationRepository
from neuroglia.core import OperationResult
from neuroglia.mediation import Query, QueryHandler


@dataclass
class GetConversationQuery(Query[OperationResult[Optional[Conversation]]]):
    """Query to retrieve a specific conversation."""

    conversation_id: str
    user_info: dict[str, Any]


class GetConversationQueryHandler(QueryHandler[GetConversationQuery, OperationResult[Optional[Conversation]]]):
    """Handle conversation retrieval with ownership validation.

    Uses ConversationRepository for MongoDB queries.
    """

    def __init__(self, conversation_repository: ConversationRepository):
        super().__init__()
        self.conversation_repository = conversation_repository

    async def handle_async(self, request: GetConversationQuery) -> OperationResult[Optional[Conversation]]:
        """Handle get conversation query."""
        query = request

        # Get the conversation
        conversation = await self.conversation_repository.get_async(query.conversation_id)
        if conversation is None:
            return self.not_found(Conversation, query.conversation_id)

        # Verify user owns the conversation
        user_id = query.user_info.get("sub") or query.user_info.get("user_id") or query.user_info.get("preferred_username")
        if user_id and conversation.state.user_id != user_id:
            return self.forbidden("You don't have access to this conversation")

        return self.ok(conversation)
