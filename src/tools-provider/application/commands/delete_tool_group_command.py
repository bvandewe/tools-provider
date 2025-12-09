"""Delete tool group command with handler."""

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from domain.entities.tool_group import ToolGroup
from neuroglia.core import OperationResult
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_bus import CloudEventBus
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import CloudEventPublishingOptions
from neuroglia.mapping import Mapper
from neuroglia.mediation import Command, CommandHandler, Mediator
from neuroglia.observability.tracing import add_span_attributes
from observability import tool_group_processing_time, tool_groups_deleted
from opentelemetry import trace

from .command_handler_base import CommandHandlerBase

log = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


@dataclass
class DeleteToolGroupCommand(Command[OperationResult[None]]):
    """Command to delete a tool group."""

    group_id: str
    """ID of the group to delete."""

    user_info: Optional[Dict[str, Any]] = None
    """User information from authentication context."""


class DeleteToolGroupCommandHandler(
    CommandHandlerBase,
    CommandHandler[DeleteToolGroupCommand, OperationResult[None]],
):
    """Handler for deleting tool groups."""

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

    async def handle_async(self, request: DeleteToolGroupCommand) -> OperationResult[None]:
        """Handle the delete tool group command."""
        command = request
        start_time = time.time()

        # Add business context to automatic span created by CQRS middleware
        add_span_attributes(
            {
                "tool_group.id": command.group_id,
                "tool_group.has_user_info": command.user_info is not None,
            }
        )

        # Load aggregate
        tool_group = await self.tool_group_repository.get_async(command.group_id)
        if not tool_group:
            return self.not_found(ToolGroup, command.group_id)

        # Get user ID from context
        deleted_by = None
        if command.user_info:
            deleted_by = command.user_info.get("sub") or command.user_info.get("email")

        # Create custom span for delete logic
        with tracer.start_as_current_span("delete_tool_group_entity") as span:
            span.set_attribute("tool_group.name", tool_group.state.name)
            span.set_attribute("tool_group.selector_count", len(tool_group.state.selectors))
            span.set_attribute("tool_group.deleted_by", deleted_by or "unknown")

            # Mark for deletion
            tool_group.mark_as_deleted(deleted_by=deleted_by)

        # Persist and delete
        await self.tool_group_repository.update_async(tool_group)
        await self.tool_group_repository.remove_async(command.group_id)

        # Record metrics
        processing_time_ms = (time.time() - start_time) * 1000
        tool_groups_deleted.add(1)
        tool_group_processing_time.record(processing_time_ms, {"operation": "delete"})

        log.info(f"Deleted tool group: {command.group_id}")
        return self.no_content()
