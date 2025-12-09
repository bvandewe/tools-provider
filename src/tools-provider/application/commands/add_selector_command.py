"""Add selector to tool group command with handler."""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import uuid4

from domain.entities.tool_group import ToolGroup
from domain.models import ToolSelector
from integration.models.tool_group_dto import ToolGroupDto
from neuroglia.core import OperationResult
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_bus import CloudEventBus
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import CloudEventPublishingOptions
from neuroglia.mapping import Mapper
from neuroglia.mediation import Command, CommandHandler, Mediator
from neuroglia.observability.tracing import add_span_attributes
from observability import tool_group_processing_time, tool_group_selectors_added
from opentelemetry import trace

from .command_handler_base import CommandHandlerBase

log = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


@dataclass
class AddSelectorCommand(Command[OperationResult[ToolGroupDto]]):
    """Command to add a pattern-based selector to a group."""

    group_id: str
    """ID of the group to modify."""

    selector_id: Optional[str] = None
    """Optional ID for the selector (defaults to UUID)."""

    source_pattern: str = "*"
    """Pattern for source name matching."""

    name_pattern: str = "*"
    """Pattern for tool name matching."""

    path_pattern: Optional[str] = None
    """Pattern for source path matching."""

    required_tags: List[str] = field(default_factory=list)
    """Tags that must be present."""

    excluded_tags: List[str] = field(default_factory=list)
    """Tags that must not be present."""

    user_info: Optional[Dict[str, Any]] = None
    """User information from authentication context."""


class AddSelectorCommandHandler(
    CommandHandlerBase,
    CommandHandler[AddSelectorCommand, OperationResult[ToolGroupDto]],
):
    """Handler for adding selectors to tool groups."""

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

    async def handle_async(self, request: AddSelectorCommand) -> OperationResult[ToolGroupDto]:
        """Handle the add selector command."""
        command = request
        start_time = time.time()

        # Add business context to automatic span created by CQRS middleware
        add_span_attributes(
            {
                "tool_group.id": command.group_id,
                "selector.source_pattern": command.source_pattern,
                "selector.name_pattern": command.name_pattern,
                "selector.has_path_pattern": command.path_pattern is not None,
                "selector.has_required_tags": len(command.required_tags) > 0,
                "selector.has_excluded_tags": len(command.excluded_tags) > 0,
            }
        )

        # Load aggregate
        tool_group = await self.tool_group_repository.get_async(command.group_id)
        if not tool_group:
            return self.not_found(ToolGroup, command.group_id)

        # Get user ID from context
        added_by = None
        if command.user_info:
            added_by = command.user_info.get("sub") or command.user_info.get("email")

        # Create custom span for selector creation
        with tracer.start_as_current_span("add_selector_to_tool_group") as span:
            span.set_attribute("tool_group.name", tool_group.state.name)
            span.set_attribute("tool_group.selector_count_before", len(tool_group.state.selectors))

            # Create selector
            selector = ToolSelector(
                id=command.selector_id or str(uuid4()),
                source_pattern=command.source_pattern,
                name_pattern=command.name_pattern,
                path_pattern=command.path_pattern,
                required_tags=command.required_tags,
                excluded_tags=command.excluded_tags,
            )

            span.set_attribute("selector.id", selector.id)

            # Add selector
            added = tool_group.add_selector(selector, added_by=added_by)
            span.set_attribute("selector.added", added)

        if not added:
            return self.bad_request(f"Selector with ID '{selector.id}' already exists in this group")

        # Persist changes
        await self.tool_group_repository.update_async(tool_group)

        # Record metrics
        processing_time_ms = (time.time() - start_time) * 1000
        tool_group_selectors_added.add(1)
        tool_group_processing_time.record(processing_time_ms, {"operation": "add_selector"})

        log.info(f"Added selector '{selector.id}' to tool group: {command.group_id}")
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
