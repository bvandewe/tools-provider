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
from domain.repositories import ConversationRepository

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

    Uses CQRS pattern:
    - ReadModel (ConversationRepository): For fast ownership validation (read only)
    - WriteModel (Repository[Conversation, str]): For event-sourced delete operations

    The ReadModel is updated automatically by projection handlers when
    ConversationDeletedDomainEvent is published for each conversation.
    """

    def __init__(
        self,
        mediator: Mediator,
        mapper: Mapper,
        cloud_event_bus: CloudEventBus,
        cloud_event_publishing_options: CloudEventPublishingOptions,
        conversation_repository: Repository[Conversation, str],  # WriteModel (EventStoreDB)
        conversation_dto_repository: ConversationRepository,  # ReadModel (MongoDB) - READ ONLY
    ):
        super().__init__(
            mediator,
            mapper,
            cloud_event_bus,
            cloud_event_publishing_options,
        )
        self.conversation_repository = conversation_repository
        self.conversation_dto_repository = conversation_dto_repository

    async def handle_async(self, request: DeleteConversationsCommand) -> OperationResult[DeleteConversationsResult]:
        """Handle delete conversations command.

        Flow for each conversation:
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

        deleted_count = 0
        failed_ids: list[str] = []

        for conversation_id in command.conversation_ids:
            try:
                # Load conversation from repository
                conversation = await self.conversation_dto_repository.get_async(conversation_id)

                if conversation is None:
                    log.warning(f"Conversation not found: {conversation_id}")
                    failed_ids.append(conversation_id)
                    continue

                # Verify user owns the conversation (access via aggregate state)
                if user_id and conversation.state.user_id != user_id:
                    log.warning(f"User {user_id} doesn't own conversation {conversation_id}")
                    failed_ids.append(conversation_id)
                    continue

                # Mark conversation as deleted (emits ConversationDeletedDomainEvent)
                conversation.delete()

                # Save to WriteModel - persists the deletion event and publishes it
                # The projection handler will update the ReadModel automatically
                await self.conversation_repository.update_async(conversation)

                # Remove the event stream from WriteModel
                await self.conversation_repository.remove_async(conversation_id)
                log.debug(f"Deleted conversation {conversation_id} from WriteModel")
                deleted_count += 1

            except Exception as e:
                log.error(f"Failed to delete conversation {conversation_id}: {e}")
                failed_ids.append(conversation_id)

        result = DeleteConversationsResult(deleted_count=deleted_count, failed_ids=failed_ids)
        return self.ok(result)
