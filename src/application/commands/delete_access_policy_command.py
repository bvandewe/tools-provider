"""Delete access policy command with handler."""

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

from domain.entities.access_policy import AccessPolicy
from observability import access_policies_deleted, access_policy_processing_time

from .command_handler_base import CommandHandlerBase

log = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


@dataclass
class DeleteAccessPolicyCommand(Command[OperationResult[bool]]):
    """Command to delete an access policy."""

    policy_id: str
    """ID of the policy to delete."""

    user_info: Optional[Dict[str, Any]] = None
    """User information from authentication context."""


class DeleteAccessPolicyCommandHandler(
    CommandHandlerBase,
    CommandHandler[DeleteAccessPolicyCommand, OperationResult[bool]],
):
    """Handler for deleting access policies."""

    def __init__(
        self,
        mediator: Mediator,
        mapper: Mapper,
        cloud_event_bus: CloudEventBus,
        cloud_event_publishing_options: CloudEventPublishingOptions,
        access_policy_repository: Repository[AccessPolicy, str],
    ):
        super().__init__(
            mediator,
            mapper,
            cloud_event_bus,
            cloud_event_publishing_options,
        )
        self.access_policy_repository = access_policy_repository

    async def handle_async(self, request: DeleteAccessPolicyCommand) -> OperationResult[bool]:
        """Handle the delete access policy command."""
        command = request
        start_time = time.time()

        # Add business context to automatic span
        add_span_attributes({"access_policy.id": command.policy_id, "access_policy.operation": "delete"})

        # Get user ID from context
        deleted_by = None
        if command.user_info:
            deleted_by = command.user_info.get("sub") or command.user_info.get("email")

        # Load existing policy
        policy = await self.access_policy_repository.get_async(command.policy_id)
        if not policy:
            return self.not_found(AccessPolicy, command.policy_id)

        with tracer.start_as_current_span("delete_access_policy_entity") as span:
            # Mark for deletion (emits event)
            policy.mark_as_deleted(deleted_by=deleted_by)
            span.set_attribute("access_policy.deleted_by", deleted_by or "unknown")

        # Update to persist the deletion event
        await self.access_policy_repository.update_async(policy)

        # Remove from repository
        await self.access_policy_repository.remove_async(command.policy_id)
        log.info(f"AccessPolicy deleted: {command.policy_id}")

        # Record metrics
        processing_time_ms = (time.time() - start_time) * 1000
        access_policies_deleted.add(1)
        access_policy_processing_time.record(processing_time_ms, {"operation": "delete"})
        log.debug(f"AccessPolicy deletion processed in {processing_time_ms:.2f}ms")

        return self.ok(True)
