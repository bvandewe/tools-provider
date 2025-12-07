"""Disable tool command with handler."""

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

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
class DisableToolCommand(Command[OperationResult[SourceToolDto]]):
    """Command to disable an enabled tool."""

    tool_id: str
    """ID of the tool to disable (format: source_id:operation_id)."""

    reason: Optional[str] = None
    """Optional reason for disabling the tool."""

    user_info: Optional[Dict[str, Any]] = None
    """User information from authentication context."""


class DisableToolCommandHandler(
    CommandHandlerBase,
    CommandHandler[DisableToolCommand, OperationResult[SourceToolDto]],
):
    """Handler for disabling tools."""

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

    async def handle_async(self, request: DisableToolCommand) -> OperationResult[SourceToolDto]:
        """Handle the disable tool command."""
        command = request
        start_time = time.time()

        # Add business context to automatic span created by CQRS middleware
        add_span_attributes(
            {
                "source_tool.id": command.tool_id,
                "source_tool.operation": "disable",
                "source_tool.has_reason": command.reason is not None,
                "source_tool.has_user_info": command.user_info is not None,
            }
        )

        # Load aggregate
        source_tool = await self.source_tool_repository.get_async(command.tool_id)
        if not source_tool:
            return self.not_found(SourceTool, command.tool_id)

        # Get user ID from context
        disabled_by = None
        if command.user_info:
            disabled_by = command.user_info.get("sub") or command.user_info.get("email")

        # Create custom span for disable logic
        with tracer.start_as_current_span("disable_source_tool_entity") as span:
            span.set_attribute("source_tool.name", source_tool.state.tool_name)
            span.set_attribute("source_tool.was_enabled", source_tool.state.is_enabled)
            span.set_attribute("source_tool.disabled_by", disabled_by or "unknown")
            span.set_attribute("source_tool.reason", command.reason or "")

            # Disable
            disabled = source_tool.disable(disabled_by=disabled_by, reason=command.reason)
            span.set_attribute("source_tool.disabled", disabled)

        if not disabled:
            return self.bad_request("Tool is already disabled")

        # Persist changes
        await self.source_tool_repository.update_async(source_tool)

        # Record metrics
        processing_time_ms = (time.time() - start_time) * 1000
        log.info(f"Tool {command.tool_id} disabled by {disabled_by} in {processing_time_ms:.2f}ms (reason: {command.reason})")

        # Map to DTO and return
        dto = self.mapper.map(source_tool.state, SourceToolDto)
        return self.ok(dto)
