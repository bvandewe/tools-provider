"""Create ConversationTemplate command with handler.

This command creates a new ConversationTemplate in the repository.
Only admins should have access to this command (enforced at controller level).
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from neuroglia.core import OperationResult
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_bus import CloudEventBus
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import CloudEventPublishingOptions
from neuroglia.mapping import Mapper
from neuroglia.mediation import Command, CommandHandler, Mediator

from application.commands.command_handler_base import CommandHandlerBase
from domain.entities import ConversationTemplate
from domain.models.conversation_item import ConversationItem
from integration.models.template_dto import ConversationItemDto, ConversationTemplateDto, ItemContentDto

log = logging.getLogger(__name__)


# Regex for valid slug IDs: lowercase letters, numbers, hyphens
SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$")


@dataclass
class CreateTemplateCommand(Command[OperationResult[ConversationTemplateDto]]):
    """Command to create a new ConversationTemplate.

    Attributes:
        id: Unique slug identifier (immutable after creation)
        name: Display name for the template
        description: Longer description for UI
        agent_starts_first: If True, agent sends first message
        allow_agent_switching: If True, user can switch agents
        allow_navigation: If True, user can jump between items
        allow_backward_navigation: If True, user can go back
        enable_chat_input_initially: If True, chat input enabled at start
        min_duration_seconds: Minimum time before completion
        max_duration_seconds: Maximum time for conversation
        shuffle_items: If True, randomize item order
        display_progress_indicator: If True, show progress bar
        display_item_score: If True, show score per item
        display_item_title: If True, show item titles
        display_final_score_report: If True, show final score
        include_feedback: If True, provide feedback
        append_items_to_view: If True, keep previous items visible
        introduction_message: Message at start
        completion_message: Message on completion
        items: List of ConversationItem data
        passing_score_percent: Score needed to pass
        user_info: Authenticated user performing the action
    """

    # Required fields
    id: str
    name: str

    # Optional fields with defaults
    description: str | None = None
    agent_starts_first: bool = False
    allow_agent_switching: bool = False
    allow_navigation: bool = False
    allow_backward_navigation: bool = False
    enable_chat_input_initially: bool = True
    continue_after_completion: bool = False
    min_duration_seconds: int | None = None
    max_duration_seconds: int | None = None
    shuffle_items: bool = False
    display_progress_indicator: bool = True
    display_item_score: bool = False
    display_item_title: bool = True
    display_final_score_report: bool = False
    include_feedback: bool = True
    append_items_to_view: bool = True
    introduction_message: str | None = None
    completion_message: str | None = None
    items: list[dict[str, Any]] = field(default_factory=list)
    passing_score_percent: float | None = None

    # User context
    user_info: dict[str, Any] | None = None


class CreateTemplateCommandHandler(
    CommandHandlerBase,
    CommandHandler[CreateTemplateCommand, OperationResult[ConversationTemplateDto]],
):
    """Handler for CreateTemplateCommand."""

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

    async def handle_async(self, command: CreateTemplateCommand) -> OperationResult[ConversationTemplateDto]:
        """Handle the create template command.

        Validates the input and creates a new ConversationTemplate in the repository.
        """
        user_info = command.user_info or {}
        user_id = user_info.get("sub") or user_info.get("user_id") or "unknown"

        # Validate ID format (must be a valid slug)
        if not command.id or not command.id.strip():
            return self.bad_request("ID is required")

        slug_id = command.id.strip().lower()
        if len(slug_id) < 2:
            return self.bad_request("ID must be at least 2 characters")

        if not SLUG_PATTERN.match(slug_id):
            return self.bad_request("ID must be a valid slug: lowercase letters, numbers, and hyphens only. Cannot start or end with a hyphen.")

        # Validate required fields
        if not command.name or not command.name.strip():
            return self.bad_request("Name is required")

        # Check for existing template with same ID
        existing = await self._repository.get_async(slug_id)
        if existing is not None:
            return self.conflict(f"ConversationTemplate with ID '{slug_id}' already exists")

        # Parse items from dictionaries
        items = self._parse_items(command.items)

        # Create the new template aggregate (emits ConversationTemplateCreatedDomainEvent)
        template = ConversationTemplate(
            template_id=slug_id,
            name=command.name.strip(),
            description=command.description,
            agent_starts_first=command.agent_starts_first,
            allow_agent_switching=command.allow_agent_switching,
            allow_navigation=command.allow_navigation,
            allow_backward_navigation=command.allow_backward_navigation,
            enable_chat_input_initially=command.enable_chat_input_initially,
            continue_after_completion=command.continue_after_completion,
            min_duration_seconds=command.min_duration_seconds,
            max_duration_seconds=command.max_duration_seconds,
            shuffle_items=command.shuffle_items,
            display_progress_indicator=command.display_progress_indicator,
            display_item_score=command.display_item_score,
            display_item_title=command.display_item_title,
            display_final_score_report=command.display_final_score_report,
            include_feedback=command.include_feedback,
            append_items_to_view=command.append_items_to_view,
            introduction_message=command.introduction_message,
            completion_message=command.completion_message,
            items=items,
            passing_score_percent=command.passing_score_percent,
            created_by=user_id,
        )

        try:
            # Save to repository
            saved = await self._repository.add_async(template)

            # Map from aggregate state to DTO for response
            dto = self._map_to_dto(saved.state)
            log.info(f"Created ConversationTemplate: {slug_id} by user {user_id}")

            return self.ok(dto)

        except Exception as e:
            log.error(f"Failed to create ConversationTemplate {slug_id}: {e}")
            return self.internal_server_error(str(e))

    def _parse_items(self, items_data: list[dict[str, Any]]) -> list[ConversationItem]:
        """Parse items from dictionary data.

        Args:
            items_data: List of item dictionaries

        Returns:
            List of ConversationItem objects
        """
        items = []
        for item_data in items_data:
            item = ConversationItem.from_dict(item_data)
            items.append(item)
        return items

    def _map_to_dto(self, state: Any) -> ConversationTemplateDto:
        """Map a ConversationTemplateState to DTO.

        Args:
            state: The ConversationTemplateState to map

        Returns:
            ConversationTemplateDto
        """
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
