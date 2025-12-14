"""Sync tool group tools command with handler.

This command performs a diff-based sync of explicit and excluded tools,
only emitting events for tools that were added or removed.
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
from observability import tool_group_processing_time, tool_group_tools_added, tool_group_tools_excluded, tool_group_tools_included, tool_group_tools_removed
from opentelemetry import trace

from domain.entities.tool_group import ToolGroup
from integration.models.tool_group_dto import ToolGroupDto

from ..command_handler_base import CommandHandlerBase

log = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


@dataclass
class SyncToolGroupToolsCommand(Command[OperationResult[ToolGroupDto]]):
    """Command to sync explicit and excluded tools for a tool group.

    Performs a diff between the current tools and the desired state,
    emitting only the necessary add/remove events.
    """

    group_id: str
    """ID of the group to sync tools for."""

    explicit_tool_ids: list[str] = field(default_factory=list)
    """Desired explicit tool IDs for the group."""

    excluded_tool_ids: list[str] = field(default_factory=list)
    """Desired excluded tool IDs for the group."""

    user_info: dict[str, Any] | None = None
    """User information from authentication context."""


class SyncToolGroupToolsCommandHandler(
    CommandHandlerBase,
    CommandHandler[SyncToolGroupToolsCommand, OperationResult[ToolGroupDto]],
):
    """Handler for syncing tool group explicit/excluded tools.

    Computes the diff between current and desired tools,
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

    async def handle_async(self, request: SyncToolGroupToolsCommand) -> OperationResult[ToolGroupDto]:
        """Handle the sync tools command."""
        command = request
        start_time = time.time()

        # Add business context
        add_span_attributes(
            {
                "tool_group.id": command.group_id,
                "tool_group.desired_explicit_count": len(command.explicit_tool_ids),
                "tool_group.desired_excluded_count": len(command.excluded_tool_ids),
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

        with tracer.start_as_current_span("sync_tool_group_tools") as span:
            span.set_attribute("tool_group.name", tool_group.state.name)
            span.set_attribute("tool_group.current_explicit_count", len(tool_group.state.explicit_tool_ids))
            span.set_attribute("tool_group.current_excluded_count", len(tool_group.state.excluded_tool_ids))

            # Track changes
            changes_made = 0

            # === Sync Explicit Tools ===
            current_explicit_ids: set[str] = {m.tool_id for m in tool_group.state.explicit_tool_ids}
            desired_explicit_ids: set[str] = set(command.explicit_tool_ids)

            explicit_to_remove = current_explicit_ids - desired_explicit_ids
            explicit_to_add = desired_explicit_ids - current_explicit_ids

            span.set_attribute("explicit.to_remove", len(explicit_to_remove))
            span.set_attribute("explicit.to_add", len(explicit_to_add))

            # Remove explicit tools no longer desired
            explicit_removed = 0
            for tool_id in explicit_to_remove:
                if tool_group.remove_tool(tool_id, removed_by=user_id):
                    explicit_removed += 1
                    changes_made += 1

            # Add new explicit tools
            explicit_added = 0
            for tool_id in explicit_to_add:
                if tool_group.add_tool(tool_id, added_by=user_id):
                    explicit_added += 1
                    changes_made += 1

            span.set_attribute("explicit.removed", explicit_removed)
            span.set_attribute("explicit.added", explicit_added)

            # === Sync Excluded Tools ===
            current_excluded_ids: set[str] = {e.tool_id for e in tool_group.state.excluded_tool_ids}
            desired_excluded_ids: set[str] = set(command.excluded_tool_ids)

            excluded_to_include = current_excluded_ids - desired_excluded_ids  # Remove from exclusion
            excluded_to_exclude = desired_excluded_ids - current_excluded_ids  # Add to exclusion

            span.set_attribute("excluded.to_include", len(excluded_to_include))
            span.set_attribute("excluded.to_exclude", len(excluded_to_exclude))

            # Include tools no longer excluded
            tools_included = 0
            for tool_id in excluded_to_include:
                if tool_group.include_tool(tool_id, included_by=user_id):
                    tools_included += 1
                    changes_made += 1

            # Exclude new tools
            tools_excluded = 0
            for tool_id in excluded_to_exclude:
                if tool_group.exclude_tool(tool_id, excluded_by=user_id):
                    tools_excluded += 1
                    changes_made += 1

            span.set_attribute("excluded.included", tools_included)
            span.set_attribute("excluded.excluded", tools_excluded)
            span.set_attribute("total_changes", changes_made)

        # Only persist if there were changes
        if changes_made > 0:
            await self.tool_group_repository.update_async(tool_group)

        # Record metrics
        processing_time_ms = (time.time() - start_time) * 1000
        if explicit_added > 0:
            tool_group_tools_added.add(explicit_added)
        if explicit_removed > 0:
            tool_group_tools_removed.add(explicit_removed)
        if tools_excluded > 0:
            tool_group_tools_excluded.add(tools_excluded)
        if tools_included > 0:
            tool_group_tools_included.add(tools_included)
        tool_group_processing_time.record(processing_time_ms, {"operation": "sync_tools"})

        log.info(f"Synced tools for tool group {command.group_id}: " f"explicit +{explicit_added}/-{explicit_removed}, " f"excluded +{tools_excluded}/-{tools_included}")
        return self.ok(self._to_dto(tool_group))

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
