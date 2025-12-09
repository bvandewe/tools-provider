"""Delete label command with handler."""

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

from .command_handler_base import CommandHandlerBase

log = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


@dataclass
class DeleteLabelCommand(Command[OperationResult[None]]):
    """Command to delete a label.

    This soft-deletes the label. A separate process should handle
    removing this label from all associated tools.
    """

    label_id: str
    """ID of the label to delete."""

    user_info: Optional[Dict[str, Any]] = None
    """User information from authentication context."""


class DeleteLabelCommandHandler(
    CommandHandlerBase,
    CommandHandler[DeleteLabelCommand, OperationResult[None]],
):
    """Handler for deleting labels."""

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

    async def handle_async(self, request: DeleteLabelCommand) -> OperationResult[None]:
        """Handle the delete label command."""
        command = request

        # Add business context
        add_span_attributes({"label.id": command.label_id})

        # Load existing label
        label = await self.label_repository.get_async(command.label_id)
        if not label:
            return self.not_found(Label, command.label_id)

        if label.is_deleted:
            return self.ok(None)  # Already deleted, idempotent

        # Get user ID from context
        deleted_by = None
        if command.user_info:
            deleted_by = command.user_info.get("sub") or command.user_info.get("email")

        # Delete the label
        label.delete(deleted_by=deleted_by)

        # Persist changes
        await self.label_repository.update_async(label)

        log.info(f"Deleted label: {label.id}")
        return self.no_content()
