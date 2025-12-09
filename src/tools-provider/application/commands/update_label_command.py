"""Update label command with handler."""

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from domain.entities.label import Label
from integration.models.label_dto import LabelDto
from neuroglia.core import OperationResult
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_bus import CloudEventBus
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import CloudEventPublishingOptions
from neuroglia.mapping import Mapper
from neuroglia.mediation import Command, CommandHandler, Mediator
from neuroglia.observability.tracing import add_span_attributes
from opentelemetry import trace

from .command_handler_base import CommandHandlerBase

log = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


@dataclass
class UpdateLabelCommand(Command[OperationResult[LabelDto]]):
    """Command to update an existing label."""

    label_id: str
    """ID of the label to update."""

    name: Optional[str] = None
    """New name (if provided)."""

    description: Optional[str] = None
    """New description (if provided)."""

    color: Optional[str] = None
    """New color (if provided)."""

    user_info: Optional[Dict[str, Any]] = None
    """User information from authentication context."""


class UpdateLabelCommandHandler(
    CommandHandlerBase,
    CommandHandler[UpdateLabelCommand, OperationResult[LabelDto]],
):
    """Handler for updating labels."""

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

    async def handle_async(self, request: UpdateLabelCommand) -> OperationResult[LabelDto]:
        """Handle the update label command."""
        command = request

        # Add business context
        add_span_attributes(
            {
                "label.id": command.label_id,
                "label.update.has_name": command.name is not None,
                "label.update.has_description": command.description is not None,
                "label.update.has_color": command.color is not None,
            }
        )

        # Validate at least one field is being updated
        if command.name is None and command.description is None and command.color is None:
            return self.bad_request("At least one field (name, description, or color) must be provided")

        # Load existing label
        label = await self.label_repository.get_async(command.label_id)
        if not label:
            return self.not_found(Label, command.label_id)

        if label.is_deleted:
            return self.bad_request("Cannot update a deleted label")

        # Get user ID from context
        updated_by = None
        if command.user_info:
            updated_by = command.user_info.get("sub") or command.user_info.get("email")

        # Apply updates
        label.update(
            name=command.name.strip() if command.name else None,
            description=command.description if command.description is not None else None,
            color=command.color.strip() if command.color else None,
            updated_by=updated_by,
        )

        # Persist changes
        await self.label_repository.update_async(label)

        # Map to DTO for response
        dto = LabelDto(
            id=label.id,
            name=label.name,
            description=label.description,
            color=label.color,
            tool_count=0,  # Will be updated by read model
            created_at=label.state.created_at,
            updated_at=label.state.updated_at,
            created_by=label.state.created_by,
            is_deleted=False,
        )

        log.info(f"Updated label: {label.id}")
        return self.ok(dto)
