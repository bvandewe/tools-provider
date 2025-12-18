"""Update ConversationTemplate command with handler.

This command updates an existing ConversationTemplate in the repository.
Uses optimistic concurrency via version field.
Only admins should have access to this command (enforced at controller level).
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from neuroglia.core import OperationResult
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_bus import CloudEventBus
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import CloudEventPublishingOptions
from neuroglia.mapping import Mapper
from neuroglia.mediation import Command, CommandHandler, Mediator

from application.commands.command_handler_base import CommandHandlerBase
from domain.models.conversation_item import ConversationItem
from domain.models.conversation_template import ConversationTemplate
from domain.repositories import TemplateRepository
from integration.models.template_dto import ConversationItemDto, ConversationTemplateDto, ItemContentDto

log = logging.getLogger(__name__)


@dataclass
class UpdateTemplateCommand(Command[OperationResult[ConversationTemplateDto]]):
    """Command to update an existing ConversationTemplate.

    The ID is immutable - to change an ID, delete and recreate.
    Uses optimistic concurrency: provide the current version to ensure
    no concurrent modifications occurred.

    Attributes:
        id: The ID of the template to update (immutable, for lookup only)
        version: Current version for optimistic concurrency check
        name: Updated display name
        description: Updated description
        agent_starts_first: Updated behavior flag
        allow_agent_switching: Updated flag
        allow_navigation: Updated flag
        allow_backward_navigation: Updated flag
        enable_chat_input_initially: Updated flag
        min_duration_seconds: Updated timing
        max_duration_seconds: Updated timing
        shuffle_items: Updated flag
        display_progress_indicator: Updated flag
        display_item_score: Updated flag
        display_item_title: Updated flag
        display_final_score_report: Updated flag
        include_feedback: Updated flag
        append_items_to_view: Updated flag
        introduction_message: Updated message
        completion_message: Updated message
        items: Updated items list (full replacement)
        passing_score_percent: Updated scoring
        user_info: Authenticated user performing the action
    """

    # Identity (for lookup - not changed)
    id: str

    # Optimistic concurrency
    version: int

    # Fields that can be updated (None = not provided)
    name: str | None = None
    description: str | None = None
    agent_starts_first: bool | None = None
    allow_agent_switching: bool | None = None
    allow_navigation: bool | None = None
    allow_backward_navigation: bool | None = None
    enable_chat_input_initially: bool | None = None
    continue_after_completion: bool | None = None
    min_duration_seconds: int | None = None
    max_duration_seconds: int | None = None
    shuffle_items: bool | None = None
    display_progress_indicator: bool | None = None
    display_item_score: bool | None = None
    display_item_title: bool | None = None
    display_final_score_report: bool | None = None
    include_feedback: bool | None = None
    append_items_to_view: bool | None = None
    introduction_message: str | None = None
    completion_message: str | None = None
    items: list[dict[str, Any]] | None = None
    passing_score_percent: float | None = None

    # Sentinel for explicit null (to differentiate from "not provided")
    clear_description: bool = False
    clear_introduction_message: bool = False
    clear_completion_message: bool = False
    clear_min_duration: bool = False
    clear_max_duration: bool = False
    clear_passing_score: bool = False

    # User context
    user_info: dict[str, Any] | None = None


class UpdateTemplateCommandHandler(
    CommandHandlerBase,
    CommandHandler[UpdateTemplateCommand, OperationResult[ConversationTemplateDto]],
):
    """Handler for UpdateTemplateCommand."""

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

    async def handle_async(self, command: UpdateTemplateCommand) -> OperationResult[ConversationTemplateDto]:
        """Handle the update template command.

        Validates version for optimistic concurrency and applies updates.
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

        # Optimistic concurrency check
        if existing.version != command.version:
            return self.conflict(
                f"Version mismatch. Expected version {command.version}, but current version is {existing.version}. The template was modified by another user. Please refresh and try again."
            )

        # Apply updates (only non-None fields)
        if command.name is not None:
            if not command.name.strip():
                return self.bad_request("Name cannot be empty")
            existing.name = command.name.strip()

        if command.description is not None:
            existing.description = command.description.strip() if command.description else None
        elif command.clear_description:
            existing.description = None

        # Flow configuration
        if command.agent_starts_first is not None:
            existing.agent_starts_first = command.agent_starts_first

        if command.allow_agent_switching is not None:
            existing.allow_agent_switching = command.allow_agent_switching

        if command.allow_navigation is not None:
            existing.allow_navigation = command.allow_navigation

        if command.allow_backward_navigation is not None:
            existing.allow_backward_navigation = command.allow_backward_navigation

        if command.enable_chat_input_initially is not None:
            existing.enable_chat_input_initially = command.enable_chat_input_initially

        if command.continue_after_completion is not None:
            existing.continue_after_completion = command.continue_after_completion

        # Timing
        if command.min_duration_seconds is not None:
            existing.min_duration_seconds = command.min_duration_seconds
        elif command.clear_min_duration:
            existing.min_duration_seconds = None

        if command.max_duration_seconds is not None:
            existing.max_duration_seconds = command.max_duration_seconds
        elif command.clear_max_duration:
            existing.max_duration_seconds = None

        # Display options
        if command.shuffle_items is not None:
            existing.shuffle_items = command.shuffle_items

        if command.display_progress_indicator is not None:
            existing.display_progress_indicator = command.display_progress_indicator

        if command.display_item_score is not None:
            existing.display_item_score = command.display_item_score

        if command.display_item_title is not None:
            existing.display_item_title = command.display_item_title

        if command.display_final_score_report is not None:
            existing.display_final_score_report = command.display_final_score_report

        if command.include_feedback is not None:
            existing.include_feedback = command.include_feedback

        if command.append_items_to_view is not None:
            existing.append_items_to_view = command.append_items_to_view

        # Messages
        if command.introduction_message is not None:
            existing.introduction_message = command.introduction_message if command.introduction_message else None
        elif command.clear_introduction_message:
            existing.introduction_message = None

        if command.completion_message is not None:
            existing.completion_message = command.completion_message if command.completion_message else None
        elif command.clear_completion_message:
            existing.completion_message = None

        # Items (full replacement)
        if command.items is not None:
            existing.items = self._parse_items(command.items)

        # Scoring
        if command.passing_score_percent is not None:
            existing.passing_score_percent = command.passing_score_percent
        elif command.clear_passing_score:
            existing.passing_score_percent = None

        # Update audit fields
        existing.updated_at = datetime.now(UTC)
        existing.version += 1

        try:
            # Save to repository
            await self._repository.update_async(existing)

            # Map to DTO for response
            dto = self._map_to_dto(existing)
            log.info(f"Updated ConversationTemplate: {template_id} by user {user_id} (v{existing.version})")

            return self.ok(dto)

        except Exception as e:
            log.error(f"Failed to update ConversationTemplate {template_id}: {e}")
            return self.internal_server_error(str(e))

    def _parse_items(self, items_data: list[dict[str, Any]]) -> list[ConversationItem]:
        """Parse items from dictionary data."""
        items = []
        for item_data in items_data:
            item = ConversationItem.from_dict(item_data)
            items.append(item)
        return items

    def _map_to_dto(self, template: ConversationTemplate) -> ConversationTemplateDto:
        """Map a ConversationTemplate to DTO."""
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
            continue_after_completion=template.continue_after_completion,
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
