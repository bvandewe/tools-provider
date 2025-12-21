"""Record item response command for persisting widget responses.

This command handles recording user responses to template items,
including scoring and correctness validation.
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
from domain.entities.conversation import Conversation
from integration.models.conversation_dto import ConversationDto

log = logging.getLogger(__name__)


@dataclass
class WidgetResponse:
    """A single widget response within an item."""

    widget_id: str
    value: Any
    content_id: str | None = None
    is_correct: bool | None = None
    score: float | None = None
    max_score: float | None = None


@dataclass
class RecordItemResponseCommand(Command[OperationResult[ConversationDto]]):
    """Command to record user's response to a template item.

    This command persists the responses and scores for a completed item.
    It should be dispatched when all required widgets in an item have been answered.

    Attributes:
        conversation_id: The conversation ID
        item_id: The template item ID
        item_index: The 0-based index of the item
        responses: List of widget responses
        response_time_ms: Time taken to respond to the item
        user_info: User authentication context
    """

    conversation_id: str
    item_id: str
    item_index: int
    responses: list[WidgetResponse] = field(default_factory=list)
    response_time_ms: int | None = None
    user_info: dict[str, Any] | None = None


class RecordItemResponseCommandHandler(
    CommandHandlerBase,
    CommandHandler[RecordItemResponseCommand, OperationResult[ConversationDto]],
):
    """Handle recording item responses."""

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

    async def handle_async(self, request: RecordItemResponseCommand) -> OperationResult[ConversationDto]:
        """Handle record item response command."""
        command = request

        log.info(f"Recording item response: conversation={command.conversation_id}, item={command.item_id}")

        # Get the conversation
        conversation = await self.conversation_repository.get_async(command.conversation_id)
        if conversation is None:
            return self.not_found(ConversationDto, command.conversation_id)

        # Aggregate the responses into a single answer record
        # For simplicity, we concatenate widget values or use the primary response
        combined_response = ""
        total_score = 0.0
        max_score = 0.0
        any_correct = None

        for response in command.responses:
            if response.value:
                combined_response += f"{response.widget_id}:{response.value};"

            if response.score is not None:
                total_score += response.score
            if response.max_score is not None:
                max_score += response.max_score
            if response.is_correct is not None:
                if any_correct is None:
                    any_correct = response.is_correct
                else:
                    # Item is correct only if all widgets are correct
                    any_correct = any_correct and response.is_correct

        # Record the item answer
        conversation.record_item_answer(
            item_id=command.item_id,
            user_response=combined_response.rstrip(";"),
            is_correct=any_correct,
            response_time_ms=command.response_time_ms,
        )

        # Record individual scores for each widget response
        for response in command.responses:
            if response.score is not None and response.max_score is not None:
                conversation.record_item_score(
                    item_id=command.item_id,
                    content_id=response.content_id or response.widget_id,
                    score=response.score,
                    max_score=response.max_score,
                    is_correct=response.is_correct,
                )

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
