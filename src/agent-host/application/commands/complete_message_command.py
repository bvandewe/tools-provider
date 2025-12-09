"""Complete message command for finalizing LLM response.

This command handles updating a message with the final LLM response
after streaming completes, including tool calls and results.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from application.commands.command_handler_base import CommandHandlerBase
from domain.entities.conversation import Conversation
from domain.models.message import MessageStatus
from integration.models.conversation_dto import ConversationDto
from neuroglia.core import OperationResult
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_bus import CloudEventBus
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import CloudEventPublishingOptions
from neuroglia.mapping import Mapper
from neuroglia.mediation import Command, CommandHandler, Mediator

log = logging.getLogger(__name__)


@dataclass
class ToolCallData:
    """Data for a tool call."""

    tool_name: str
    arguments: dict[str, Any]
    call_id: Optional[str] = None


@dataclass
class ToolResultData:
    """Data for a tool result."""

    call_id: str
    tool_name: str
    success: bool
    result: Any
    error: Optional[str] = None
    execution_time_ms: Optional[float] = None


@dataclass
class CompleteMessageCommand(Command[OperationResult[ConversationDto]]):
    """Command to complete a message with final content and tool results."""

    conversation_id: str
    message_id: str
    content: str
    tool_calls: list[ToolCallData] = field(default_factory=list)
    tool_results: list[ToolResultData] = field(default_factory=list)
    status: str = "completed"
    user_info: Optional[dict[str, Any]] = None


class CompleteMessageCommandHandler(
    CommandHandlerBase,
    CommandHandler[CompleteMessageCommand, OperationResult[ConversationDto]],
):
    """Handle completing a message after LLM streaming finishes."""

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

    async def handle_async(self, request: CompleteMessageCommand) -> OperationResult[ConversationDto]:
        """Handle complete message command."""
        command = request

        # Get the conversation
        conversation = await self.conversation_repository.get_async(command.conversation_id)
        if conversation is None:
            return self.not_found(ConversationDto, command.conversation_id)

        # Add tool calls to the message
        for tc in command.tool_calls:
            conversation.add_tool_call(
                message_id=command.message_id,
                tool_name=tc.tool_name,
                arguments=tc.arguments,
                call_id=tc.call_id,
            )

        # Add tool results to the message
        for tr in command.tool_results:
            conversation.add_tool_result(
                message_id=command.message_id,
                call_id=tr.call_id,
                tool_name=tr.tool_name,
                success=tr.success,
                result=tr.result,
                error=tr.error,
                execution_time_ms=tr.execution_time_ms,
            )

        # Update message status
        new_status = MessageStatus(command.status) if command.status else MessageStatus.COMPLETED
        conversation.update_message_status(command.message_id, new_status)

        # Save the updated conversation
        await self.conversation_repository.update_async(conversation)

        # Build response DTO
        dto = ConversationDto(
            id=conversation.id(),
            user_id=conversation.state.user_id,
            title=conversation.state.title,
            system_prompt=conversation.state.system_prompt,
            messages=conversation.state.messages,
            created_at=conversation.state.created_at,
            updated_at=conversation.state.updated_at,
        )

        return self.ok(dto)
