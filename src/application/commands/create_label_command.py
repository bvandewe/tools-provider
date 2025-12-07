"""Create label command with handler."""

import logging
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

from domain.entities.label import Label
from integration.models.label_dto import LabelDto

from .command_handler_base import CommandHandlerBase

log = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


@dataclass
class CreateLabelCommand(Command[OperationResult[LabelDto]]):
    """Command to create a new label.

    Labels are user-defined tags for categorizing tools.
    """

    name: str
    """Display name for the label."""

    description: str = ""
    """Description of what tools should have this label."""

    color: str = "#6b7280"
    """CSS color for visual styling (hex or named color)."""

    label_id: Optional[str] = None
    """Optional specific ID (defaults to UUID)."""

    user_info: Optional[Dict[str, Any]] = None
    """User information from authentication context."""


class CreateLabelCommandHandler(
    CommandHandlerBase,
    CommandHandler[CreateLabelCommand, OperationResult[LabelDto]],
):
    """Handler for creating new labels."""

    def __init__(
        self,
        mediator: Mediator,
        mapper: Mapper,
        cloud_event_bus: CloudEventBus,
        cloud_event_publishing_options: CloudEventPublishingOptions,
        label_repository: Repository[Label, str],
    ):
        super().__init__(
            mediator,
            mapper,
            cloud_event_bus,
            cloud_event_publishing_options,
        )
        self.label_repository = label_repository

    async def handle_async(self, request: CreateLabelCommand) -> OperationResult[LabelDto]:
        """Handle the create label command."""
        command = request

        # Add business context to automatic span created by CQRS middleware
        add_span_attributes(
            {
                "label.name": command.name,
                "label.color": command.color,
                "label.has_custom_id": command.label_id is not None,
            }
        )

        # Validate name
        if not command.name or not command.name.strip():
            return self.bad_request("Label name is required")

        # Validate color format (basic validation)
        color = command.color.strip()
        if not color:
            color = "#6b7280"

        # Get user ID from context
        created_by = None
        if command.user_info:
            created_by = command.user_info.get("sub") or command.user_info.get("email")

        # Create custom span for label creation logic
        with tracer.start_as_current_span("create_label_entity") as span:
            # Create the aggregate
            label = Label.create(
                name=command.name.strip(),
                description=command.description or "",
                color=color,
                label_id=command.label_id,
                created_by=created_by,
            )

            span.set_attribute("label.id", label.id)
            span.set_attribute("label.created_by", created_by or "unknown")

        # Persist to event store
        await self.label_repository.add_async(label)

        # Map to DTO for response
        dto = LabelDto(
            id=label.id,
            name=label.name,
            description=label.description,
            color=label.color,
            tool_count=0,
            created_at=label.state.created_at,
            updated_at=label.state.updated_at,
            created_by=created_by,
            is_deleted=False,
        )

        log.info(f"Created label: {label.id}")
        return self.created(dto)
