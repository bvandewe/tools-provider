"""Get conversation query with handler."""

from dataclasses import dataclass
from typing import Any

from neuroglia.core import OperationResult
from neuroglia.mediation import Query, QueryHandler

from domain.entities.conversation import Conversation
from domain.repositories.conversation_repository import ConversationRepository
from integration.models.conversation_dto import ConversationDto


@dataclass
class GetConversationQuery(Query[OperationResult[ConversationDto | None]]):
    """Query to retrieve a specific conversation."""

    conversation_id: str
    user_info: dict[str, Any]


class GetConversationQueryHandler(QueryHandler[GetConversationQuery, OperationResult[ConversationDto | None]]):
    """Handle conversation retrieval with ownership validation.

    Uses ConversationRepository for MongoDB queries.
    """

    def __init__(self, conversation_repository: ConversationRepository):
        super().__init__()
        self.conversation_repository = conversation_repository

    async def handle_async(self, request: GetConversationQuery) -> OperationResult[ConversationDto | None]:
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

        # Map aggregate to DTO
        dto = _map_conversation_to_dto(conversation)
        return self.ok(dto)


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
        status=state.status,
        template_progress=state.template_progress,
        template_config=state.template_config,
        created_at=state.created_at,
        updated_at=state.updated_at,
    )
