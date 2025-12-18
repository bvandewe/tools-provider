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
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_bus import CloudEventBus
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import CloudEventPublishingOptions
from neuroglia.mapping import Mapper
from neuroglia.mediation import Command, CommandHandler, Mediator

from application.commands.command_handler_base import CommandHandlerBase
from domain.models.conversation_template import ConversationTemplate
from domain.repositories import TemplateRepository
from integration.models.template_dto import ConversationTemplateDto

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
        template_repository: TemplateRepository,
    ):
        super().__init__(
            mediator,
            mapper,
            cloud_event_bus,
            cloud_event_publishing_options,
        )
        self._repository = template_repository

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

        # Fetch existing template
        existing = await self._repository.get_async(template_id)
        if existing is None:
            return self.not_found(ConversationTemplate, template_id)

        try:
            # Delete from repository
            await self._repository.remove_async(template_id)

            # Map to DTO for response (return the deleted entity)
            dto = self._map_to_dto(existing)
            log.info(f"Deleted ConversationTemplate: {template_id} by user {user_id}")

            return self.ok(dto)

        except Exception as e:
            log.error(f"Failed to delete ConversationTemplate {template_id}: {e}")
            return self.internal_server_error(str(e))

    def _map_to_dto(self, template: ConversationTemplate) -> ConversationTemplateDto:
        """Map a ConversationTemplate to DTO."""
        from integration.models.template_dto import ConversationItemDto, ItemContentDto

        items_dto = []
        for item in template.items:
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
            id=template.id,
            name=template.name,
            description=template.description,
            agent_starts_first=template.agent_starts_first,
            allow_agent_switching=template.allow_agent_switching,
            allow_navigation=template.allow_navigation,
            allow_backward_navigation=template.allow_backward_navigation,
            enable_chat_input_initially=template.enable_chat_input_initially,
            min_duration_seconds=template.min_duration_seconds,
            max_duration_seconds=template.max_duration_seconds,
            shuffle_items=template.shuffle_items,
            display_progress_indicator=template.display_progress_indicator,
            display_item_score=template.display_item_score,
            display_item_title=template.display_item_title,
            display_final_score_report=template.display_final_score_report,
            include_feedback=template.include_feedback,
            append_items_to_view=template.append_items_to_view,
            introduction_message=template.introduction_message,
            completion_message=template.completion_message,
            items=items_dto,
            passing_score_percent=template.passing_score_percent,
            created_by=template.created_by,
            created_at=template.created_at,
            updated_at=template.updated_at,
            version=template.version,
        )
