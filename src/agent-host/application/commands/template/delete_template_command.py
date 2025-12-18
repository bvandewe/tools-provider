"""Delete ConversationTemplate command with handler.

This command deletes an existing ConversationTemplate from the repository.
Only admins should have access to this command (enforced at controller level).

Note: If a template is referenced by an AgentDefinition (via template_id),
the definition's template_id will become a dangling reference. Consider
updating related definitions or implementing cascading updates if needed.
"""

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
from domain.entities import ConversationTemplate
from integration.models.template_dto import ConversationItemDto, ConversationTemplateDto, ItemContentDto

log = logging.getLogger(__name__)


@dataclass
class DeleteTemplateCommand(Command[OperationResult[ConversationTemplateDto]]):
    """Command to delete an existing ConversationTemplate.

    Attributes:
        id: The ID of the template to delete
        user_info: Authenticated user performing the action
    """

    id: str
    user_info: dict[str, Any] | None = None


class DeleteTemplateCommandHandler(
    CommandHandlerBase,
    CommandHandler[DeleteTemplateCommand, OperationResult[ConversationTemplateDto]],
):
    """Handler for DeleteTemplateCommand."""

    def __init__(
        self,
        mediator: Mediator,
        mapper: Mapper,
        cloud_event_bus: CloudEventBus,
        cloud_event_publishing_options: CloudEventPublishingOptions,
        conversation_template_repository: Repository[ConversationTemplate, str],
    ):
        super().__init__(
            mediator,
            mapper,
            cloud_event_bus,
            cloud_event_publishing_options,
        )
        self._repository = conversation_template_repository

    async def handle_async(self, command: DeleteTemplateCommand) -> OperationResult[ConversationTemplateDto]:
        """Handle the delete template command.

        Returns the deleted template in the response.
        """
        user_info = command.user_info or {}
        user_id = user_info.get("sub") or user_info.get("user_id") or "unknown"

        # Validate ID
        if not command.id or not command.id.strip():
            return self.bad_request("ID is required")

        template_id = command.id.strip()

        # Fetch existing template aggregate
        existing = await self._repository.get_async(template_id)
        if existing is None:
            return self.not_found(ConversationTemplate, template_id)

        try:
            # Call delete on aggregate (emits ConversationTemplateDeletedDomainEvent)
            existing.delete(deleted_by=user_id)

            # Save and then remove from repository
            await self._repository.update_async(existing)
            await self._repository.remove_async(template_id)

            # Map from aggregate state to DTO for response (return the deleted entity)
            dto = self._map_to_dto(existing.state)
            log.info(f"Deleted ConversationTemplate: {template_id} by user {user_id}")

            return self.ok(dto)

        except Exception as e:
            log.error(f"Failed to delete ConversationTemplate {template_id}: {e}")
            return self.internal_server_error(str(e))

    def _map_to_dto(self, state: Any) -> ConversationTemplateDto:
        """Map a ConversationTemplateState to DTO."""
        items_dto = []
        for item in state.items:
            contents_dto = []
            for content in item.contents:
                content_dto = ItemContentDto(
                    id=content.id,
                    order=content.order,
                    is_templated=content.is_templated,
                    source_id=content.source_id,
                    widget_type=content.widget_type,
                    widget_config=content.widget_config,
                    skippable=content.skippable,
                    required=content.required,
                    max_score=content.max_score,
                    stem=content.stem,
                    options=content.options,
                    correct_answer=content.correct_answer,
                    explanation=content.explanation,
                    initial_value=content.initial_value,
                )
                contents_dto.append(content_dto)

            item_dto = ConversationItemDto(
                id=item.id,
                order=item.order,
                title=item.title,
                enable_chat_input=item.enable_chat_input,
                show_expiration_warning=item.show_expiration_warning,
                expiration_warning_seconds=item.expiration_warning_seconds,
                warning_message=item.warning_message,
                provide_feedback=item.provide_feedback,
                reveal_correct_answer=item.reveal_correct_answer,
                time_limit_seconds=item.time_limit_seconds,
                contents=contents_dto,
            )
            items_dto.append(item_dto)

        return ConversationTemplateDto(
            id=state.id,
            name=state.name,
            description=state.description,
            agent_starts_first=state.agent_starts_first,
            allow_agent_switching=state.allow_agent_switching,
            allow_navigation=state.allow_navigation,
            allow_backward_navigation=state.allow_backward_navigation,
            enable_chat_input_initially=state.enable_chat_input_initially,
            continue_after_completion=state.continue_after_completion,
            min_duration_seconds=state.min_duration_seconds,
            max_duration_seconds=state.max_duration_seconds,
            shuffle_items=state.shuffle_items,
            display_progress_indicator=state.display_progress_indicator,
            display_item_score=state.display_item_score,
            display_item_title=state.display_item_title,
            display_final_score_report=state.display_final_score_report,
            include_feedback=state.include_feedback,
            append_items_to_view=state.append_items_to_view,
            introduction_message=state.introduction_message,
            completion_message=state.completion_message,
            items=items_dto,
            passing_score_percent=state.passing_score_percent,
            created_by=state.created_by,
            created_at=state.created_at,
            updated_at=state.updated_at,
            version=state.version,
        )
