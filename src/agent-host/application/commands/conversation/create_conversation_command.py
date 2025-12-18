"""Create conversation command with handler."""

import logging
from dataclasses import dataclass
from typing import Any

from neuroglia.core import OperationResult
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_bus import CloudEventBus
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import CloudEventPublishingOptions
from neuroglia.mapping import Mapper
from neuroglia.mediation import Command, CommandHandler, Mediator

from application.commands.command_handler_base import CommandHandlerBase
from domain.entities.conversation import Conversation
from domain.repositories import AgentDefinitionRepository
from integration.models.conversation_dto import ConversationDto

log = logging.getLogger(__name__)


@dataclass
class CreateConversationCommand(Command[OperationResult[ConversationDto]]):
    """Command to create a new conversation."""

    title: str | None = None
    system_prompt: str | None = None
    definition_id: str | None = None
    user_info: dict[str, Any] | None = None


class CreateConversationCommandHandler(
    CommandHandlerBase,
    CommandHandler[CreateConversationCommand, OperationResult[ConversationDto]],
):
    """Handle conversation creation."""

    def __init__(
        self,
        mediator: Mediator,
        mapper: Mapper,
        cloud_event_bus: CloudEventBus,
        cloud_event_publishing_options: CloudEventPublishingOptions,
        conversation_repository: Repository[Conversation, str],
        definition_repository: AgentDefinitionRepository,
    ):
        super().__init__(
            mediator,
            mapper,
            cloud_event_bus,
            cloud_event_publishing_options,
        )
        self.conversation_repository = conversation_repository
        self.definition_repository = definition_repository

    async def handle_async(self, request: CreateConversationCommand) -> OperationResult[ConversationDto]:
        """Handle create conversation command."""
        command = request
        user_info = command.user_info or {}

        # Get user ID from various possible fields in user_info
        user_id = user_info.get("sub") or user_info.get("user_id") or user_info.get("preferred_username") or "anonymous"

        # Fetch AgentDefinition if provided to get display name and icon
        definition_name = "Agent"
        definition_icon = "bi-robot"
        if command.definition_id:
            agent_definition = await self.definition_repository.get_async(command.definition_id)
            if agent_definition:
                definition_name = agent_definition.state.name or "Agent"
                definition_icon = agent_definition.state.icon or "bi-robot"

        # Create new conversation
        conversation = Conversation(
            user_id=user_id,
            definition_id=command.definition_id or "",
            title=command.title,
            system_prompt=command.system_prompt,
        )

        # Save conversation (repository handles event publishing)
        # Neuroglia's reconciliator automatically syncs to ReadModel (MongoDB)
        saved_conversation = await self.conversation_repository.add_async(conversation)

        # Map to DTO with display fields for frontend
        dto = ConversationDto(
            id=saved_conversation.id(),
            user_id=saved_conversation.state.user_id,
            definition_id=saved_conversation.state.definition_id,
            definition_name=definition_name,
            definition_icon=definition_icon,
            title=saved_conversation.state.title,
            # system_prompt=saved_conversation.state.system_prompt,  # Do not expose system prompt in DTO
            messages=saved_conversation.state.messages,
            message_count=len(saved_conversation.state.messages),
            created_at=saved_conversation.state.created_at,
            updated_at=saved_conversation.state.updated_at,
        )

        return self.ok(dto)
