"""Delete conversation command with handler."""

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

log = logging.getLogger(__name__)


@dataclass
class DeleteConversationCommand(Command[OperationResult[bool]]):
    """Command to delete a conversation."""

    conversation_id: str
    user_info: Optional[dict[str, Any]] = None


class DeleteConversationCommandHandler(
    CommandHandlerBase,
    CommandHandler[DeleteConversationCommand, OperationResult[bool]],
):
    """Handle conversation deletion."""

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

    async def handle_async(self, request: DeleteConversationCommand) -> OperationResult[bool]:
        """Handle delete conversation command."""
        command = request

        # Get the conversation
        conversation = await self.conversation_repository.get_async(command.conversation_id)
        if conversation is None:
            return self.not_found(Conversation, command.conversation_id)

        # Verify user owns the conversation
        user_info = command.user_info or {}
        user_id = user_info.get("sub") or user_info.get("user_id") or user_info.get("preferred_username")
        if user_id and conversation.state.user_id != user_id:
            return self.forbidden("You don't have access to this conversation")

        # Mark conversation as deleted (event sourcing - soft delete)
        conversation.delete()

        # Remove from repository
        await self.conversation_repository.remove_async(command.conversation_id)

        return self.ok(True)
