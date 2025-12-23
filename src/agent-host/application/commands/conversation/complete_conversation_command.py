"""Command to mark a conversation as completed.

This command is used when:
- A proactive template flow completes all items
- A conversation is explicitly completed by the system

The completion status is persisted to enable proper handling on session resume,
particularly when continue_after_completion=False.
"""

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


@dataclass
class CompleteConversationCommand(Command[OperationResult[bool]]):
    """Command to mark a conversation as completed.

    Returns True if the conversation was successfully completed.
    """

    conversation_id: str
    summary: dict[str, Any] | None = field(default_factory=dict)
    user_info: dict[str, Any] | None = None


class CompleteConversationCommandHandler(
    CommandHandlerBase,
    CommandHandler[CompleteConversationCommand, OperationResult[bool]],
):
    """Handle marking a conversation as completed.

    This persists the ConversationCompletedDomainEvent to the conversation,
    ensuring the completed status is available on session resume.
    """

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

    async def handle_async(self, request: CompleteConversationCommand) -> OperationResult[bool]:
        """Handle complete conversation command."""
        command = request

        # Get the conversation
        conversation = await self.conversation_repository.get_async(command.conversation_id)
        if conversation is None:
            return self.not_found(ConversationDto, command.conversation_id)

        # Mark as completed
        conversation.complete(summary=command.summary)

        # Save the conversation
        await self.conversation_repository.update_async(conversation)

        return self.ok(True)
