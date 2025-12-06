"""Create conversation command with handler."""

import logging
from dataclasses import dataclass
from typing import Any, Optional

from neuroglia.core import OperationResult
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_bus import CloudEventBus
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import CloudEventPublishingOptions
from neuroglia.mapping import Mapper
from neuroglia.mediation import Command, CommandHandler, Mediator

from application.commands.command_handler_base import CommandHandlerBase
from domain.entities.conversation import Conversation
from integration.models.conversation_dto import ConversationDto

log = logging.getLogger(__name__)


@dataclass
class CreateConversationCommand(Command[OperationResult[ConversationDto]]):
    """Command to create a new conversation."""

    title: Optional[str] = None
    system_prompt: Optional[str] = None
    user_info: Optional[dict[str, Any]] = None


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
    ):
        super().__init__(
            mediator,
            mapper,
            cloud_event_bus,
            cloud_event_publishing_options,
        )
        self.conversation_repository = conversation_repository

    async def handle_async(self, request: CreateConversationCommand) -> OperationResult[ConversationDto]:
        """Handle create conversation command."""
        command = request
        user_info = command.user_info or {}

        # Get user ID from various possible fields in user_info
        user_id = user_info.get("sub") or user_info.get("user_id") or user_info.get("preferred_username") or "anonymous"

        # Create new conversation
        conversation = Conversation(
            user_id=user_id,
            title=command.title,
            system_prompt=command.system_prompt,
        )

        # Save conversation (repository handles event publishing)
        saved_conversation = await self.conversation_repository.add_async(conversation)

        # Map to DTO
        dto = ConversationDto(
            id=saved_conversation.id(),
            user_id=saved_conversation.state.user_id,
            title=saved_conversation.state.title,
            system_prompt=saved_conversation.state.system_prompt,
            messages=saved_conversation.state.messages,
            created_at=saved_conversation.state.created_at,
            updated_at=saved_conversation.state.updated_at,
        )

        return self.ok(dto)
