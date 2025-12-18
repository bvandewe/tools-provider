"""Delete conversation command with handler."""

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
from domain.repositories import ConversationRepository

log = logging.getLogger(__name__)


@dataclass
class DeleteConversationCommand(Command[OperationResult[bool]]):
    """Command to delete a conversation."""

    conversation_id: str
    user_info: dict[str, Any] | None = None


class DeleteConversationCommandHandler(
    CommandHandlerBase,
    CommandHandler[DeleteConversationCommand, OperationResult[bool]],
):
    """Handle conversation deletion.

    Deletes from both:
    - WriteModel (EventStoreDB) via Repository[Conversation, str] - honors configured delete_mode
    - ReadModel (MongoDB) via ConversationRepository
    """

    def __init__(
        self,
        mediator: Mediator,
        mapper: Mapper,
        cloud_event_bus: CloudEventBus,
        cloud_event_publishing_options: CloudEventPublishingOptions,
        write_repository: Repository[Conversation, str],  # EventStoreDB (WriteModel)
        read_repository: ConversationRepository,  # MongoDB (ReadModel)
    ):
        super().__init__(
            mediator,
            mapper,
            cloud_event_bus,
            cloud_event_publishing_options,
        )
        self.write_repository = write_repository
        self.read_repository = read_repository

    async def handle_async(self, request: DeleteConversationCommand) -> OperationResult[bool]:
        """Handle delete conversation command."""
        command = request

        # Try to get conversation from read model first (faster)
        conversation = await self.read_repository.get_async(command.conversation_id)
        if conversation is None:
            # Fallback: try write model
            conversation = await self.write_repository.get_async(command.conversation_id)
            if conversation is None:
                return self.not_found(Conversation, command.conversation_id)

        # Verify user owns the conversation
        user_info = command.user_info or {}
        user_id = user_info.get("sub") or user_info.get("user_id") or user_info.get("preferred_username")
        if user_id and conversation.state.user_id != user_id:
            return self.forbidden("You don't have access to this conversation")

        # Mark conversation as deleted (for event sourcing)
        conversation.delete()

        # Delete from WriteModel (EventStoreDB) - honors delete_mode (HARD/SOFT)
        try:
            await self.write_repository.remove_async(command.conversation_id)
            log.debug(f"Deleted conversation {command.conversation_id} from WriteModel (EventStoreDB)")
        except Exception as e:
            log.warning(f"Failed to delete from WriteModel (may not exist): {e}")  # nosec B608

        # Delete from ReadModel (MongoDB)
        try:
            await self.read_repository.remove_async(command.conversation_id)
            log.debug(f"Deleted conversation {command.conversation_id} from ReadModel (MongoDB)")
        except Exception as e:
            log.warning(f"Failed to delete from ReadModel: {e}")  # nosec B608

        return self.ok(True)

        return self.ok(True)
