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
from domain.repositories import ConversationDtoRepository

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

    Uses CQRS pattern:
    - ReadModel (ConversationDtoRepository): For fast ownership validation (read only)
    - WriteModel (Repository[Conversation, str]): For event-sourced delete operation

    The ReadModel is updated automatically by projection handlers when the
    ConversationDeletedDomainEvent is published.
    """

    def __init__(
        self,
        mediator: Mediator,
        mapper: Mapper,
        cloud_event_bus: CloudEventBus,
        cloud_event_publishing_options: CloudEventPublishingOptions,
        conversation_repository: Repository[Conversation, str],  # WriteModel (EventStoreDB)
        conversation_dto_repository: ConversationDtoRepository,  # ReadModel (MongoDB) - READ ONLY
    ):
        super().__init__(
            mediator,
            mapper,
            cloud_event_bus,
            cloud_event_publishing_options,
        )
        self.conversation_repository = conversation_repository
        self.conversation_dto_repository = conversation_dto_repository

    async def handle_async(self, request: DeleteConversationCommand) -> OperationResult[bool]:
        """Handle delete conversation command.

        Flow:
        1. Read from ReadModel for fast ownership validation
        2. Load aggregate from WriteModel
        3. Call delete() on aggregate (emits domain event)
        4. Save to WriteModel (persists event, triggers projection)
        5. Projection handler updates ReadModel automatically
        """
        command = request

        # Get user ID for authorization
        user_info = command.user_info or {}
        user_id = user_info.get("sub") or user_info.get("user_id") or user_info.get("preferred_username")

        # Read from ReadModel for fast ownership validation
        conversation_dto = await self.conversation_dto_repository.get_async(command.conversation_id)
        if conversation_dto is None:
            return self.not_found(Conversation, command.conversation_id)

        # Verify user owns the conversation
        if user_id and conversation_dto.user_id != user_id:
            return self.forbidden("You don't have access to this conversation")

        # Load aggregate from WriteModel
        conversation = await self.conversation_repository.get_async(command.conversation_id)
        if conversation is None:
            # Aggregate not in WriteModel - this shouldn't happen in a consistent system
            log.warning(f"Conversation {command.conversation_id} exists in ReadModel but not WriteModel")
            return self.not_found(Conversation, command.conversation_id)

        # Mark conversation as deleted (emits ConversationDeletedDomainEvent)
        conversation.delete()

        # Save to WriteModel - this persists the deletion event and publishes it
        # The projection handler will update the ReadModel automatically
        await self.conversation_repository.update_async(conversation)

        # Remove the event stream from WriteModel (honors delete_mode: HARD/SOFT)
        await self.conversation_repository.remove_async(command.conversation_id)
        log.info(f"Deleted conversation {command.conversation_id} from WriteModel")

        return self.ok(True)
