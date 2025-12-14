"""Update tool group command with handler."""

import logging
import time
from dataclasses import dataclass
from typing import Any

from neuroglia.core import OperationResult
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_bus import CloudEventBus
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import CloudEventPublishingOptions
from neuroglia.mapping import Mapper
from neuroglia.mediation import Command, CommandHandler, Mediator
from neuroglia.observability.tracing import add_span_attributes
from observability import tool_group_processing_time, tool_groups_updated
from opentelemetry import trace

from domain.entities.tool_group import ToolGroup
from integration.models.tool_group_dto import ToolGroupDto

from ..command_handler_base import CommandHandlerBase

log = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


@dataclass
class UpdateToolGroupCommand(Command[OperationResult[ToolGroupDto]]):
    """Command to update a tool group's name and/or description."""

    group_id: str
    """ID of the group to update."""

    name: str | None = None
    """New name (None to keep current)."""

    description: str | None = None
    """New description (None to keep current)."""

    user_info: dict[str, Any] | None = None
    """User information from authentication context."""


class UpdateToolGroupCommandHandler(
    CommandHandlerBase,
    CommandHandler[UpdateToolGroupCommand, OperationResult[ToolGroupDto]],
):
    """Handler for updating tool group name/description."""

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

    async def handle_async(self, request: UpdateToolGroupCommand) -> OperationResult[ToolGroupDto]:
        """Handle the update tool group command."""
        command = request
        start_time = time.time()

        # Add business context to automatic span created by CQRS middleware
        add_span_attributes(
            {
                "tool_group.id": command.group_id,
                "tool_group.updating_name": command.name is not None,
                "tool_group.updating_description": command.description is not None,
                "tool_group.has_user_info": command.user_info is not None,
            }
        )

        # Load aggregate
        tool_group = await self.tool_group_repository.get_async(command.group_id)
        if not tool_group:
            return self.not_found(ToolGroup, command.group_id)

        # Get user ID from context
        updated_by = None
        if command.user_info:
            updated_by = command.user_info.get("sub") or command.user_info.get("email")

        # Create custom span for update logic
        with tracer.start_as_current_span("update_tool_group_entity") as span:
            span.set_attribute("tool_group.name", tool_group.state.name)
            span.set_attribute("tool_group.updated_by", updated_by or "unknown")

            # Apply update
            changed = tool_group.update(
                name=command.name,
                description=command.description,
                updated_by=updated_by,
            )

            span.set_attribute("tool_group.changed", changed)

        if not changed:
            return self.ok(self._to_dto(tool_group))  # No changes

        # Persist changes
        await self.tool_group_repository.update_async(tool_group)

        # Record metrics
        processing_time_ms = (time.time() - start_time) * 1000
        tool_groups_updated.add(1, {"changed": changed})
        tool_group_processing_time.record(processing_time_ms, {"operation": "update"})

        log.info(f"Updated tool group: {command.group_id}")
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
