"""Update ConversationTemplate command with handler.

This command updates an existing ConversationTemplate in the repository.
Uses optimistic concurrency via version field.
Only admins should have access to this command (enforced at controller level).
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
from domain.models.conversation_item import ConversationItem
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
        conversation_template_repository: Repository[ConversationTemplate, str],
    ):
        super().__init__(
            mediator,
            mapper,
            cloud_event_bus,
            cloud_event_publishing_options,
        )
        self._repository = conversation_template_repository

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

        # Fetch existing template aggregate
        existing = await self._repository.get_async(template_id)
        if existing is None:
            return self.not_found(ConversationTemplate, template_id)

        # Optimistic concurrency check (using state.version)
        if existing.state.version != command.version:
            return self.conflict(
                f"Version mismatch. Expected version {command.version}, but current version is {existing.state.version}. The template was modified by another user. Please refresh and try again."
            )

        # Validate name if provided
        if command.name is not None and not command.name.strip():
            return self.bad_request("Name cannot be empty")

        # Apply updates using aggregate methods
        # 1. General field updates via update() method
        existing.update(
            name=command.name.strip() if command.name else None,
            description=(command.description.strip() if command.description else None) if not command.clear_description else "",
            agent_starts_first=command.agent_starts_first,
            allow_agent_switching=command.allow_agent_switching,
            allow_navigation=command.allow_navigation,
            allow_backward_navigation=command.allow_backward_navigation,
            enable_chat_input_initially=command.enable_chat_input_initially,
            continue_after_completion=command.continue_after_completion,
            min_duration_seconds=command.min_duration_seconds if not command.clear_min_duration else 0,
            max_duration_seconds=command.max_duration_seconds if not command.clear_max_duration else 0,
            shuffle_items=command.shuffle_items,
            display_progress_indicator=command.display_progress_indicator,
            display_item_score=command.display_item_score,
            display_item_title=command.display_item_title,
            display_final_score_report=command.display_final_score_report,
            include_feedback=command.include_feedback,
            append_items_to_view=command.append_items_to_view,
            introduction_message=(command.introduction_message if command.introduction_message else None) if not command.clear_introduction_message else "",
            completion_message=(command.completion_message if command.completion_message else None) if not command.clear_completion_message else "",
            passing_score_percent=command.passing_score_percent if not command.clear_passing_score else 0.0,
        )

        # 2. Handle items update using differential sync (add/update/remove only changed items)
        if command.items is not None:
            parsed_items = self._parse_items(command.items)
            self._sync_items_differential(existing, parsed_items)

        try:
            # Save to repository
            saved = await self._repository.update_async(existing)

            # Map from aggregate state to DTO for response
            dto = self._map_to_dto(saved.state)
            log.info(f"Updated ConversationTemplate: {template_id} by user {user_id} (v{saved.state.version})")

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

    def _sync_items_differential(self, aggregate: ConversationTemplate, incoming_items: list[ConversationItem]) -> None:
        """Synchronize items using differential updates.

        Instead of removing all items and re-adding them, this method:
        1. Identifies items that were removed (exist in aggregate but not in incoming)
        2. Identifies items that were added (exist in incoming but not in aggregate)
        3. Identifies items that were updated (exist in both, but content changed)
        4. Detects reordering if the item order changed

        This minimizes the number of domain events emitted.
        """
        # Build maps by item ID
        existing_map: dict[str, ConversationItem] = {item.id: item for item in aggregate.state.items}
        incoming_map: dict[str, ConversationItem] = {item.id: item for item in incoming_items}

        existing_ids = set(existing_map.keys())
        incoming_ids = set(incoming_map.keys())

        # Items to remove (exist in current, not in incoming)
        removed_ids = existing_ids - incoming_ids
        # Items to add (exist in incoming, not in current)
        added_ids = incoming_ids - existing_ids
        # Items potentially updated (exist in both)
        common_ids = existing_ids & incoming_ids

        # 1. Remove items that no longer exist
        for item_id in removed_ids:
            aggregate.remove_item(item_id)
            log.debug(f"Removed item {item_id}")

        # 2. Update items that changed
        for item_id in common_ids:
            existing_item = existing_map[item_id]
            incoming_item = incoming_map[item_id]

            # Compare via dict representation (includes all fields)
            if existing_item.to_dict() != incoming_item.to_dict():
                aggregate.update_item(item_id, incoming_item)
                log.debug(f"Updated item {item_id}")

        # 3. Add new items
        for item_id in added_ids:
            incoming_item = incoming_map[item_id]
            aggregate.add_item(incoming_item, order=incoming_item.order)
            log.debug(f"Added item {item_id} at order {incoming_item.order}")

        # 4. Check if order changed for remaining items
        # Get current order of IDs (after removes, before potential reorder)
        # We need to reorder if the sequence of common+added items differs
        incoming_order = [item.id for item in incoming_items]
        current_order = [item.id for item in aggregate.state.items if item.id in incoming_ids]

        # If order differs, emit reorder event
        if current_order != incoming_order:
            aggregate.reorder_items(incoming_order)
            log.debug(f"Reordered items: {incoming_order}")

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
