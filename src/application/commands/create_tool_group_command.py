"""Create tool group command with handler."""

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

from domain.entities.tool_group import ToolGroup
from integration.models.tool_group_dto import ToolGroupDto
from observability import tool_group_processing_time, tool_groups_created

from .command_handler_base import CommandHandlerBase

log = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


@dataclass
class CreateToolGroupCommand(Command[OperationResult[ToolGroupDto]]):
    """Command to create a new tool group.

    Creates an empty group that can be populated with selectors
    and explicit tools.
    """

    name: str
    """Human-readable name for the group."""

    description: str = ""
    """Description of the group's purpose."""

    group_id: Optional[str] = None
    """Optional specific ID (defaults to UUID)."""

    user_info: Optional[Dict[str, Any]] = None
    """User information from authentication context."""


class CreateToolGroupCommandHandler(
    CommandHandlerBase,
    CommandHandler[CreateToolGroupCommand, OperationResult[ToolGroupDto]],
):
    """Handler for creating new tool groups."""

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

    async def handle_async(self, request: CreateToolGroupCommand) -> OperationResult[ToolGroupDto]:
        """Handle the create tool group command."""
        command = request
        start_time = time.time()

        # Add business context to automatic span created by CQRS middleware
        add_span_attributes(
            {
                "tool_group.name": command.name,
                "tool_group.has_custom_id": command.group_id is not None,
                "tool_group.has_user_info": command.user_info is not None,
            }
        )

        # Validate name
        if not command.name or not command.name.strip():
            return self.bad_request("Tool group name is required")

        # Get user ID from context
        created_by = None
        if command.user_info:
            created_by = command.user_info.get("sub") or command.user_info.get("email")

        # Create custom span for tool group creation logic
        with tracer.start_as_current_span("create_tool_group_entity") as span:
            # Create the aggregate
            tool_group = ToolGroup(
                name=command.name.strip(),
                description=command.description or "",
                created_by=created_by,
                group_id=command.group_id,
            )

            span.set_attribute("tool_group.id", tool_group.id())
            span.set_attribute("tool_group.created_by", created_by or "unknown")

        # Persist to event store
        await self.tool_group_repository.add_async(tool_group)

        # Record metrics
        processing_time_ms = (time.time() - start_time) * 1000
        tool_groups_created.add(1, {"has_description": bool(command.description)})
        tool_group_processing_time.record(processing_time_ms, {"operation": "create"})

        # Map to DTO for response
        # Note: Read model will be updated by projection handler
        dto = ToolGroupDto(
            id=tool_group.id(),
            name=tool_group.state.name,
            description=tool_group.state.description,
            selector_count=0,
            explicit_tool_count=0,
            excluded_tool_count=0,
            selectors=[],
            explicit_tool_ids=[],
            excluded_tool_ids=[],
            is_active=True,
            created_at=tool_group.state.created_at,
            updated_at=tool_group.state.updated_at,
            created_by=created_by,
        )

        log.info(f"Created tool group: {tool_group.id()}")
        return self.created(dto)
