"""Advance template command for moving to the next template item.

This command handles advancing the template progress after an item is completed.
"""

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
from integration.models.conversation_dto import ConversationDto

log = logging.getLogger(__name__)


@dataclass
class AdvanceTemplateCommand(Command[OperationResult[ConversationDto]]):
    """Command to advance to the next template item.

    This command persists the template progress by incrementing
    the current item index.

    Attributes:
        conversation_id: The conversation ID
        user_info: User authentication context
    """

    conversation_id: str
    user_info: dict[str, Any] | None = None


class AdvanceTemplateCommandHandler(
    CommandHandlerBase,
    CommandHandler[AdvanceTemplateCommand, OperationResult[ConversationDto]],
):
    """Handle advancing to the next template item."""

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

    async def handle_async(self, request: AdvanceTemplateCommand) -> OperationResult[ConversationDto]:
        """Handle advance template command."""
        command = request

        log.info(f"Advancing template: conversation={command.conversation_id}")

        # Get the conversation
        conversation = await self.conversation_repository.get_async(command.conversation_id)
        if conversation is None:
            return self.not_found(ConversationDto, command.conversation_id)

        # Advance the template
        conversation.advance_template()

        # Save the conversation
        await self.conversation_repository.update_async(conversation)

        # Construct DTO manually (no auto-mapper configuration for Conversation -> ConversationDto)
        dto = ConversationDto(
            id=conversation.id(),
            user_id=conversation.state.user_id,
            definition_id=conversation.state.definition_id,
            definition_name=getattr(conversation.state, "definition_name", None),
            definition_icon=getattr(conversation.state, "definition_icon", None),
            title=conversation.state.title,
            messages=conversation.state.messages,
            message_count=len(conversation.state.messages),
            created_at=conversation.state.created_at,
            updated_at=conversation.state.updated_at,
        )
        return self.ok(dto)
