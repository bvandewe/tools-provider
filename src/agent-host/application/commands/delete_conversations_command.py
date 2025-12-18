"""Delete multiple conversations command with handler."""

import logging
from dataclasses import dataclass, field
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
class DeleteConversationsResult:
    """Result of bulk delete operation."""

    deleted_count: int
    failed_ids: list[str] = field(default_factory=list)


@dataclass
class DeleteConversationsCommand(Command[OperationResult[DeleteConversationsResult]]):
    """Command to delete multiple conversations by their IDs."""

    conversation_ids: list[str]
    user_info: dict[str, Any] | None = None


class DeleteConversationsCommandHandler(
    CommandHandlerBase,
    CommandHandler[DeleteConversationsCommand, OperationResult[DeleteConversationsResult]],
):
    """Handle bulk conversation deletion.

    Deletes from:
    - WriteModel (EventStoreDB) if the conversation exists there
    - ReadModel (MongoDB) directly for legacy conversations not in EventStoreDB

    For conversations in EventStoreDB, the ReadModel is also updated via the
    ConversationDeletedProjectionHandler when it receives the domain event.
    """

    def __init__(
        self,
        mediator: Mediator,
        mapper: Mapper,
        cloud_event_bus: CloudEventBus,
        cloud_event_publishing_options: CloudEventPublishingOptions,
        conversation_repository: Repository[Conversation, str],  # EventStoreDB (WriteModel)
        read_repository: Repository[ConversationDto, str],  # MongoDB (ReadModel)
    ):
        super().__init__(
            mediator,
            mapper,
            cloud_event_bus,
            cloud_event_publishing_options,
        )
        self.conversation_repository = conversation_repository
        self.read_repository = read_repository

    async def handle_async(self, request: DeleteConversationsCommand) -> OperationResult[DeleteConversationsResult]:
        """Handle delete conversations command."""
        command = request

        # Get user ID for authorization
        user_info = command.user_info or {}
        user_id = user_info.get("sub") or user_info.get("user_id") or user_info.get("preferred_username")

        deleted_count = 0
        failed_ids: list[str] = []

        for conversation_id in command.conversation_ids:
            try:
                # First check ReadModel for ownership validation (faster than EventStoreDB)
                conversation_dto = await self.read_repository.get_async(conversation_id)

                if conversation_dto:
                    # Verify user owns the conversation
                    if user_id and conversation_dto.user_id != user_id:
                        log.warning(f"User {user_id} doesn't own conversation {conversation_id}")
                        failed_ids.append(conversation_id)
                        continue

                # Try to get from WriteModel (EventStoreDB)
                conversation = await self.conversation_repository.get_async(conversation_id)

                if conversation:
                    # Conversation exists in WriteModel - follow event sourcing pattern
                    # Mark conversation as deleted (emits ConversationDeletedDomainEvent)
                    conversation.delete()

                    # Save the deletion event to EventStoreDB
                    # This publishes ConversationDeletedDomainEvent via Mediator,
                    # which triggers the projection handler to remove from ReadModel
                    await self.conversation_repository.update_async(conversation)

                    # Hard delete: physically remove the event stream from EventStoreDB
                    await self.conversation_repository.remove_async(conversation_id)
                    log.debug(f"Deleted conversation {conversation_id} from WriteModel (EventStoreDB)")
                    deleted_count += 1

                elif conversation_dto:
                    # Conversation only exists in ReadModel (legacy data)
                    # Delete directly from MongoDB
                    await self.read_repository.remove_async(conversation_id)
                    log.debug(f"Deleted legacy conversation {conversation_id} from ReadModel (MongoDB)")
                    deleted_count += 1

                else:
                    # Conversation not found in either repository
                    log.warning(f"Conversation not found in any repository: {conversation_id}")
                    failed_ids.append(conversation_id)

            except Exception as e:
                log.error(f"Failed to delete conversation {conversation_id}: {e}")
                failed_ids.append(conversation_id)

        result = DeleteConversationsResult(deleted_count=deleted_count, failed_ids=failed_ids)
        return self.ok(result)
