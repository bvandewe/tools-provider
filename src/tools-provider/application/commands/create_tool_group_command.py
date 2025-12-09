"""Create tool group command with handler."""

import logging
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from neuroglia.core import OperationResult
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_bus import CloudEventBus
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import CloudEventPublishingOptions
from neuroglia.mapping import Mapper
from neuroglia.mediation import Command, CommandHandler, Mediator
from neuroglia.observability.tracing import add_span_attributes
from observability import tool_group_processing_time, tool_group_selectors_added, tool_group_tools_added, tool_group_tools_excluded, tool_groups_created
from opentelemetry import trace

from domain.entities.tool_group import ToolGroup
from domain.models import ToolSelector
from integration.models.tool_group_dto import ToolGroupDto

from .command_handler_base import CommandHandlerBase

log = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


@dataclass
class SelectorInput:
    """Input for creating a selector.

    Supports both full format (with all fields) and simplified format
    (with just source_pattern, name_pattern, etc.).
    """

    source_pattern: str = "*"
    """Pattern for source name matching (glob or regex:pattern)."""

    name_pattern: str = "*"
    """Pattern for tool name matching."""

    path_pattern: str | None = None
    """Pattern for source path matching."""

    required_tags: list[str] = field(default_factory=list)
    """Tags that must be present."""

    excluded_tags: list[str] = field(default_factory=list)
    """Tags that must not be present."""

    selector_id: str | None = None
    """Optional ID (auto-generated if not provided)."""

    def to_tool_selector(self) -> ToolSelector:
        """Convert to domain ToolSelector."""
        return ToolSelector(
            id=self.selector_id or str(uuid4()),
            source_pattern=self.source_pattern,
            name_pattern=self.name_pattern,
            path_pattern=self.path_pattern,
            required_tags=self.required_tags,
            excluded_tags=self.excluded_tags,
        )


@dataclass
class CreateToolGroupCommand(Command[OperationResult[ToolGroupDto]]):
    """Command to create a new tool group.

    Creates a group with optional initial selectors, explicit tools,
    and excluded tools.
    """

    name: str
    """Human-readable name for the group."""

    description: str = ""
    """Description of the group's purpose."""

    group_id: str | None = None
    """Optional specific ID (defaults to UUID)."""

    selectors: list[SelectorInput] = field(default_factory=list)
    """Initial selectors to add to the group."""

    explicit_tool_ids: list[str] = field(default_factory=list)
    """Initial explicit tools to add to the group."""

    excluded_tool_ids: list[str] = field(default_factory=list)
    """Initial tools to exclude from the group."""

    user_info: dict[str, Any] | None = None
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
                "tool_group.selector_count": len(command.selectors),
                "tool_group.explicit_tool_count": len(command.explicit_tool_ids),
                "tool_group.excluded_tool_count": len(command.excluded_tool_ids),
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

            # Add initial selectors
            selectors_added = 0
            for selector_input in command.selectors:
                selector = selector_input.to_tool_selector()
                if tool_group.add_selector(selector, added_by=created_by):
                    selectors_added += 1

            span.set_attribute("tool_group.selectors_added", selectors_added)

            # Add initial explicit tools
            tools_added = 0
            for tool_id in command.explicit_tool_ids:
                if tool_group.add_tool(tool_id, added_by=created_by):
                    tools_added += 1

            span.set_attribute("tool_group.tools_added", tools_added)

            # Add initial exclusions
            tools_excluded = 0
            for tool_id in command.excluded_tool_ids:
                if tool_group.exclude_tool(tool_id, excluded_by=created_by, reason="Initial exclusion"):
                    tools_excluded += 1

            span.set_attribute("tool_group.tools_excluded", tools_excluded)

        # Persist to event store (all events are persisted atomically)
        await self.tool_group_repository.add_async(tool_group)

        # Record metrics
        processing_time_ms = (time.time() - start_time) * 1000
        tool_groups_created.add(1, {"has_description": bool(command.description)})
        if selectors_added > 0:
            tool_group_selectors_added.add(selectors_added)
        if tools_added > 0:
            tool_group_tools_added.add(tools_added)
        if tools_excluded > 0:
            tool_group_tools_excluded.add(tools_excluded)
        tool_group_processing_time.record(processing_time_ms, {"operation": "create"})

        # Map to DTO for response
        dto = ToolGroupDto(
            id=tool_group.id(),
            name=tool_group.state.name,
            description=tool_group.state.description,
            selector_count=len(tool_group.state.selectors),
            explicit_tool_count=len(tool_group.state.explicit_tool_ids),
            excluded_tool_count=len(tool_group.state.excluded_tool_ids),
            selectors=[s.to_dict() for s in tool_group.state.selectors],
            explicit_tool_ids=[m.to_dict() for m in tool_group.state.explicit_tool_ids],
            excluded_tool_ids=[e.to_dict() for e in tool_group.state.excluded_tool_ids],
            is_active=True,
            created_at=tool_group.state.created_at,
            updated_at=tool_group.state.updated_at,
            created_by=created_by,
        )

        log.info(f"Created tool group: {tool_group.id()} with {selectors_added} selectors, {tools_added} explicit tools, {tools_excluded} excluded tools")
        return self.created(dto)
