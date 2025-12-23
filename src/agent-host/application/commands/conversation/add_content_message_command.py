"""Command to add an item content message to a conversation.

Item content messages are the streamed content from template items during
a proactive flow. This includes:
- Message widgets (informational text shown to the user)
- Widget presentations (interactive widgets shown to the user)

These messages preserve the widget structure for read-only display on resume.
"""

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
from domain.entities.conversation import Conversation, MessageStatus
from domain.models.message import MessageRole
from integration.models.conversation_dto import ConversationDto

log = logging.getLogger(__name__)


@dataclass
class WidgetConfig:
    """Widget configuration for persisting widget state."""

    widget_id: str
    widget_type: str
    item_id: str
    item_index: int
    stem: str | None = None
    options: list[dict[str, Any]] | None = None
    correct_answer: Any | None = None
    widget_config: dict[str, Any] | None = None
    required: bool = False
    skippable: bool = False
    initial_value: Any | None = None
    show_user_response: bool = True


@dataclass
class AddContentMessageCommand(Command[OperationResult[str]]):
    """Command to add an item content message.

    This command persists content from template items, including
    widget configurations for read-only display on resume.

    Returns the message_id of the created message.

    Attributes:
        conversation_id: The conversation ID
        content: The message content (stem text for widgets)
        role: Message role (typically 'assistant' for item content)
        item_id: The template item ID this content belongs to
        item_index: The 0-based index of the item
        widget_config: Optional widget configuration for interactive widgets
        message_type: Type of content (item_content, widget_content, etc.)
        user_info: User authentication context
    """

    conversation_id: str
    content: str
    role: str = "assistant"
    item_id: str | None = None
    item_index: int | None = None
    widget_config: WidgetConfig | None = None
    message_type: str = "item_content"
    metadata: dict[str, Any] | None = field(default_factory=dict)
    user_info: dict[str, Any] | None = None


class AddContentMessageCommandHandler(
    CommandHandlerBase,
    CommandHandler[AddContentMessageCommand, OperationResult[str]],
):
    """Handle adding item content messages to a conversation.

    Item content messages include the full widget structure so they can
    be rendered as read-only widgets when resuming a conversation.
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

    async def handle_async(self, request: AddContentMessageCommand) -> OperationResult[str]:
        """Handle add content message command."""
        command = request

        log.debug(f"Adding content message to conversation {command.conversation_id}: type={command.message_type}")

        # Get the conversation
        conversation = await self.conversation_repository.get_async(command.conversation_id)
        if conversation is None:
            return self.not_found(ConversationDto, command.conversation_id)

        # Build metadata
        metadata = command.metadata or {}
        metadata["message_type"] = command.message_type
        metadata["item_content"] = True

        # Add item context
        if command.item_id:
            metadata["item_id"] = command.item_id
        if command.item_index is not None:
            metadata["item_index"] = command.item_index

        # Add widget configuration for read-only display on resume
        if command.widget_config:
            widget_data = {
                "widget_id": command.widget_config.widget_id,
                "widget_type": command.widget_config.widget_type,
                "item_id": command.widget_config.item_id,
                "item_index": command.widget_config.item_index,
                "stem": command.widget_config.stem,
                "required": command.widget_config.required,
                "skippable": command.widget_config.skippable,
                "initial_value": command.widget_config.initial_value,
                "show_user_response": command.widget_config.show_user_response,
            }
            # Include options if present (for multiple choice, etc.)
            if command.widget_config.options:
                widget_data["options"] = command.widget_config.options
            # Include widget_config settings if present
            if command.widget_config.widget_config:
                widget_data["widget_config"] = command.widget_config.widget_config

            metadata["widget"] = widget_data

        # Determine the message role
        role = MessageRole.ASSISTANT if command.role == "assistant" else MessageRole.USER

        # Add the message with metadata
        message_id = conversation.add_message(
            role=role,
            content=command.content,
            status=MessageStatus.COMPLETED,
            metadata=metadata,
        )

        # Save the conversation
        await self.conversation_repository.update_async(conversation)

        log.debug(f"📝 Persisted {command.message_type} message {message_id} for {command.conversation_id}")

        return self.ok(message_id)
