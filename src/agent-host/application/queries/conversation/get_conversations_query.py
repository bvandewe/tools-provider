"""Get conversations query with handler."""

from dataclasses import dataclass
from typing import Any

from neuroglia.core import OperationResult
from neuroglia.mediation import Query, QueryHandler

from domain.entities.conversation import Conversation
from domain.repositories.conversation_repository import ConversationRepository
from integration.models.conversation_dto import ConversationDto


@dataclass
class GetConversationsQuery(Query[OperationResult[list[ConversationDto]]]):
    """Query to retrieve all conversations for a user."""

    user_info: dict[str, Any]
    limit: int | None = None


class GetConversationsQueryHandler(QueryHandler[GetConversationsQuery, OperationResult[list[ConversationDto]]]):
    """Handle conversations retrieval for a user.

    Uses ConversationRepository for MongoDB queries.
    """

    def __init__(self, conversation_repository: ConversationRepository):
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

        # Map aggregates to DTOs
        dtos = [_map_conversation_to_dto(c) for c in conversations]
        return self.ok(dtos)


def _map_conversation_to_dto(conv: Conversation) -> ConversationDto:
    """Map Conversation aggregate to DTO."""
    state = conv.state
    return ConversationDto(
        id=conv.id(),
        user_id=state.user_id,
        definition_id=state.definition_id,
        # Note: definition_name/icon are not in aggregate state,
        # they would need to be fetched from AgentDefinition if needed
        definition_name="Agent",
        definition_icon="bi-robot",
        title=state.title,
        messages=state.messages,
        message_count=len(state.messages),
        created_at=state.created_at,
        updated_at=state.updated_at,
    )
