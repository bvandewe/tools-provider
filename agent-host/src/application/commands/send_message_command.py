"""Send message command with handler.

This command handles adding a user message to a conversation and
triggering the LLM response generation with tool execution.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from neuroglia.core import OperationResult
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_bus import CloudEventBus
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import CloudEventPublishingOptions
from neuroglia.mapping import Mapper
from neuroglia.mediation import Command, CommandHandler, Mediator

from application.commands.command_handler_base import CommandHandlerBase
from domain.entities.conversation import Conversation
from domain.models.message import MessageStatus

log = logging.getLogger(__name__)


@dataclass
class MessageResponseDto:
    """Response containing the assistant's reply and any tool executions."""

    conversation_id: str
    user_message_id: str
    assistant_message_id: str
    assistant_content: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    tool_results: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class SendMessageCommand(Command[OperationResult[MessageResponseDto]]):
    """Command to send a message in a conversation."""

    conversation_id: str
    content: str
    access_token: Optional[str] = None  # For tool execution
    user_info: Optional[dict[str, Any]] = None


class SendMessageCommandHandler(
    CommandHandlerBase,
    CommandHandler[SendMessageCommand, OperationResult[MessageResponseDto]],
):
    """Handle sending a message and generating LLM response.

    This handler:
    1. Adds the user message to the conversation
    2. Invokes the LLM service to generate a response
    3. Handles tool calls if the LLM requests them
    4. Persists all state changes via events
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

    async def handle_async(self, request: SendMessageCommand) -> OperationResult[MessageResponseDto]:
        """Handle send message command.

        Note: This is the synchronous command handler. For streaming responses,
        use the ChatService.send_message_stream() method directly via the API.
        """
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

        # Add user message to conversation
        user_message_id = conversation.add_user_message(command.content)

        # Create a placeholder assistant message
        # In a streaming scenario, the actual content would be filled progressively
        assistant_message_id = conversation.add_assistant_message(
            content="",  # Will be updated as LLM generates
            status=MessageStatus.PENDING,
        )

        # Save the conversation with the new messages
        await self.conversation_repository.update_async(conversation)

        # Build response (actual LLM invocation happens in streaming flow)
        response = MessageResponseDto(
            conversation_id=conversation.id(),
            user_message_id=user_message_id,
            assistant_message_id=assistant_message_id,
            assistant_content="",  # Empty for now - streaming fills this
            tool_calls=[],
            tool_results=[],
        )

        return self.ok(response)
