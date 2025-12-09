"""Sync tool group selectors command with handler.

This command performs a diff-based sync of selectors, only emitting
events for selectors that were added or removed.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from neuroglia.core import OperationResult
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_bus import CloudEventBus
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import CloudEventPublishingOptions
from neuroglia.mapping import Mapper
from neuroglia.mediation import Command, CommandHandler, Mediator
from neuroglia.observability.tracing import add_span_attributes
from observability import tool_group_processing_time, tool_group_selectors_added, tool_group_selectors_removed
from opentelemetry import trace

from domain.entities.tool_group import ToolGroup
from domain.models import ToolSelector
from integration.models.tool_group_dto import ToolGroupDto

from .command_handler_base import CommandHandlerBase
from .create_tool_group_command import SelectorInput

log = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


@dataclass
class SyncToolGroupSelectorsCommand(Command[OperationResult[ToolGroupDto]]):
    """Command to sync selectors for a tool group.

    Performs a diff between the current selectors and the desired state,
    emitting only the necessary add/remove events.
    """

    group_id: str
    """ID of the group to sync selectors for."""

    selectors: list[SelectorInput] = field(default_factory=list)
    """Desired selectors for the group."""

    user_info: dict[str, Any] | None = None
    """User information from authentication context."""


class SyncToolGroupSelectorsCommandHandler(
    CommandHandlerBase,
    CommandHandler[SyncToolGroupSelectorsCommand, OperationResult[ToolGroupDto]],
):
    """Handler for syncing tool group selectors.

    Computes the diff between current and desired selectors,
    then emits only the necessary add/remove events.
    """

    def __init__(
        self,
        mediator: Mediator,
        mapper: Mapper,
        cloud_event_bus: CloudEventBus,
        cloud_event_publishing_options: CloudEventPublishingOptions,
        tool_group_repository: Repository[ToolGroup, str],
    ):
        super().__init__(
            mediator,
            mapper,
            cloud_event_bus,
            cloud_event_publishing_options,
        )
        self.tool_group_repository = tool_group_repository

    async def handle_async(self, request: SyncToolGroupSelectorsCommand) -> OperationResult[ToolGroupDto]:
        """Handle the sync selectors command."""
        command = request
        start_time = time.time()

        # Add business context
        add_span_attributes(
            {
                "tool_group.id": command.group_id,
                "tool_group.desired_selector_count": len(command.selectors),
            }
        )

        # Load aggregate
        tool_group = await self.tool_group_repository.get_async(command.group_id)
        if not tool_group:
            return self.not_found(ToolGroup, command.group_id)

        # Get user ID from context
        user_id = None
        if command.user_info:
            user_id = command.user_info.get("sub") or command.user_info.get("email")

        with tracer.start_as_current_span("sync_tool_group_selectors") as span:
            span.set_attribute("tool_group.name", tool_group.state.name)
            span.set_attribute("tool_group.current_selector_count", len(tool_group.state.selectors))

            # Build sets for comparison
            # Current selectors: keyed by a hash of their defining properties
            current_selectors: dict[str, ToolSelector] = {}
            for selector in tool_group.state.selectors:
                key = self._selector_key(selector)
                current_selectors[key] = selector

            # Desired selectors: convert inputs to domain objects
            desired_selectors: dict[str, ToolSelector] = {}
            for selector_input in command.selectors:
                selector = selector_input.to_tool_selector()
                key = self._selector_key(selector)
                desired_selectors[key] = selector

            # Compute diff
            current_keys = set(current_selectors.keys())
            desired_keys = set(desired_selectors.keys())

            keys_to_remove = current_keys - desired_keys
            keys_to_add = desired_keys - current_keys

            span.set_attribute("selectors.to_remove", len(keys_to_remove))
            span.set_attribute("selectors.to_add", len(keys_to_add))

            # Remove selectors that are no longer desired
            selectors_removed = 0
            for key in keys_to_remove:
                selector = current_selectors[key]
                if tool_group.remove_selector(selector.id, removed_by=user_id):
                    selectors_removed += 1

            # Add new selectors
            selectors_added = 0
            for key in keys_to_add:
                selector = desired_selectors[key]
                if tool_group.add_selector(selector, added_by=user_id):
                    selectors_added += 1

            span.set_attribute("selectors.removed", selectors_removed)
            span.set_attribute("selectors.added", selectors_added)

        # Only persist if there were changes
        if selectors_removed > 0 or selectors_added > 0:
            await self.tool_group_repository.update_async(tool_group)

        # Record metrics
        processing_time_ms = (time.time() - start_time) * 1000
        if selectors_added > 0:
            tool_group_selectors_added.add(selectors_added)
        if selectors_removed > 0:
            tool_group_selectors_removed.add(selectors_removed)
        tool_group_processing_time.record(processing_time_ms, {"operation": "sync_selectors"})

        log.info(f"Synced selectors for tool group {command.group_id}: +{selectors_added}/-{selectors_removed}")
        return self.ok(self._to_dto(tool_group))

    def _selector_key(self, selector: ToolSelector) -> str:
        """Generate a unique key for a selector based on its matching criteria.

        We use the patterns and tags as the key, NOT the ID, because
        two selectors with different IDs but the same patterns are
        functionally identical.
        """
        # Sort tags for consistent hashing
        required_tags = ",".join(sorted(selector.required_tags))
        excluded_tags = ",".join(sorted(selector.excluded_tags))
        return f"{selector.source_pattern}|{selector.name_pattern}|{selector.path_pattern or ''}|{required_tags}|{excluded_tags}"

    def _to_dto(self, tool_group: ToolGroup) -> ToolGroupDto:
        """Convert aggregate to DTO."""
        return ToolGroupDto(
            id=tool_group.id(),
            name=tool_group.state.name,
            description=tool_group.state.description,
            selector_count=len(tool_group.state.selectors),
            explicit_tool_count=len(tool_group.state.explicit_tool_ids),
            excluded_tool_count=len(tool_group.state.excluded_tool_ids),
            selectors=[s.to_dict() for s in tool_group.state.selectors],
            explicit_tool_ids=[m.to_dict() for m in tool_group.state.explicit_tool_ids],
            excluded_tool_ids=[e.to_dict() for e in tool_group.state.excluded_tool_ids],
            is_active=tool_group.state.is_active,
            created_at=tool_group.state.created_at,
            updated_at=tool_group.state.updated_at,
            created_by=tool_group.state.created_by,
        )
