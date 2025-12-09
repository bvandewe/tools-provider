"""Update tool command with handler.

Allows admins to update the display name and description of a tool,
enabling fine-tuning of auto-discovered values from upstream OpenAPI specs.
"""

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
from opentelemetry import trace

from domain.entities.source_tool import SourceTool
from integration.models.source_tool_dto import SourceToolDto

from .command_handler_base import CommandHandlerBase

log = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


@dataclass
class UpdateToolCommand(Command[OperationResult[SourceToolDto]]):
    """Command to update a tool's display name and/or description."""

    tool_id: str
    """ID of the tool to update (format: source_id:operation_id)."""

    tool_name: str | None = None
    """New display name for the tool (None to keep current)."""

    description: str | None = None
    """New description for the tool (None to keep current)."""

    user_info: dict[str, Any] | None = None
    """User information from authentication context."""


class UpdateToolCommandHandler(
    CommandHandlerBase,
    CommandHandler[UpdateToolCommand, OperationResult[SourceToolDto]],
):
    """Handler for updating tool display name and description."""

    def __init__(
        self,
        mediator: Mediator,
        mapper: Mapper,
        cloud_event_bus: CloudEventBus,
        cloud_event_publishing_options: CloudEventPublishingOptions,
        source_tool_repository: Repository[SourceTool, str],
    ):
        super().__init__(
            mediator,
            mapper,
            cloud_event_bus,
            cloud_event_publishing_options,
        )
        self.source_tool_repository = source_tool_repository

    async def handle_async(self, request: UpdateToolCommand) -> OperationResult[SourceToolDto]:
        """Handle the update tool command."""
        command = request
        start_time = time.time()

        # Add business context to automatic span created by CQRS middleware
        add_span_attributes(
            {
                "source_tool.id": command.tool_id,
                "source_tool.operation": "update",
                "source_tool.has_user_info": command.user_info is not None,
                "source_tool.updating_name": command.tool_name is not None,
                "source_tool.updating_description": command.description is not None,
            }
        )

        # Load aggregate
        source_tool = await self.source_tool_repository.get_async(command.tool_id)
        if not source_tool:
            return self.not_found(SourceTool, command.tool_id)

        # Get user ID from context
        updated_by = None
        if command.user_info:
            updated_by = command.user_info.get("sub") or command.user_info.get("email")

        # Create custom span for update logic
        with tracer.start_as_current_span("update_source_tool_entity") as span:
            span.set_attribute("source_tool.name", source_tool.state.tool_name)
            span.set_attribute("source_tool.new_name", command.tool_name or "(unchanged)")
            span.set_attribute("source_tool.updated_by", updated_by or "unknown")

            # Update
            updated = source_tool.update(
                tool_name=command.tool_name,
                description=command.description,
                updated_by=updated_by,
            )
            span.set_attribute("source_tool.updated", updated)

        if not updated:
            return self.bad_request("No changes to apply")

        # Persist changes
        await self.source_tool_repository.update_async(source_tool)

        # Record metrics
        processing_time_ms = (time.time() - start_time) * 1000
        log.info(f"Tool {command.tool_id} updated by {updated_by} in {processing_time_ms:.2f}ms")

        # Build DTO from state (can't use mapper as state has complex types)
        state = source_tool.state
        definition = state.definition
        dto = SourceToolDto(
            id=state.id,
            source_id=state.source_id,
            source_name="",  # Not available in state, will be updated by projection
            tool_name=state.tool_name,
            operation_id=state.operation_id,
            description=state.description,  # Use state description (admin-editable)
            input_schema=definition.input_schema if definition else {},
            method=definition.execution_profile.method if definition else "",
            path=definition.source_path if definition else "",
            tags=definition.tags if definition else [],
            execution_mode=definition.execution_profile.mode.value if definition else "sync_http",
            required_audience=definition.execution_profile.required_audience if definition else "",
            timeout_seconds=definition.execution_profile.timeout_seconds if definition else 30,
            is_enabled=state.is_enabled,
            status=state.status.value if hasattr(state.status, "value") else str(state.status),
            label_ids=state.label_ids or [],
            discovered_at=state.discovered_at,
            last_seen_at=state.last_seen_at,
            updated_at=state.updated_at,
            enabled_by=state.enabled_by,
            disabled_by=state.disabled_by,
            disable_reason=state.disable_reason,
            definition=definition.to_dict() if definition else None,
        )
        return self.ok(dto)
