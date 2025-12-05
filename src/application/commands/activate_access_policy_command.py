"""Activate access policy command with handler."""

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
from integration.models.access_policy_dto import AccessPolicyDto

from .command_handler_base import CommandHandlerBase

log = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


@dataclass
class ActivateAccessPolicyCommand(Command[OperationResult[AccessPolicyDto]]):
    """Command to activate an access policy.

    Only active policies participate in access resolution.
    """

    policy_id: str
    """ID of the policy to activate."""

    user_info: Optional[Dict[str, Any]] = None
    """User information from authentication context."""


class ActivateAccessPolicyCommandHandler(
    CommandHandlerBase,
    CommandHandler[ActivateAccessPolicyCommand, OperationResult[AccessPolicyDto]],
):
    """Handler for activating access policies."""

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

    async def handle_async(self, request: ActivateAccessPolicyCommand) -> OperationResult[AccessPolicyDto]:
        """Handle the activate access policy command."""
        command = request
        start_time = time.time()

        # Add business context to automatic span
        add_span_attributes({"access_policy.id": command.policy_id, "access_policy.operation": "activate"})

        # Get user ID from context
        activated_by = None
        if command.user_info:
            activated_by = command.user_info.get("sub") or command.user_info.get("email")

        # Load existing policy
        policy = await self.access_policy_repository.get_async(command.policy_id)
        if not policy:
            return self.not_found(AccessPolicy, command.policy_id)

        with tracer.start_as_current_span("activate_access_policy_entity") as span:
            # Activate the policy
            was_activated = policy.activate(activated_by=activated_by)
            span.set_attribute("access_policy.was_activated", was_activated)

        if was_activated:
            # Persist changes
            await self.access_policy_repository.update_async(policy)
            log.info(f"AccessPolicy activated: {command.policy_id}")
        else:
            log.info(f"AccessPolicy was already active: {command.policy_id}")

        # Record metrics
        processing_time_ms = (time.time() - start_time) * 1000
        log.debug(f"AccessPolicy activation processed in {processing_time_ms:.2f}ms")

        # Map to DTO for response
        dto = AccessPolicyDto(
            id=policy.id(),
            name=policy.state.name,
            description=policy.state.description,
            claim_matchers=[m.to_dict() for m in policy.state.claim_matchers],
            allowed_group_ids=list(policy.state.allowed_group_ids),
            priority=policy.state.priority,
            is_active=policy.state.is_active,
            created_at=policy.state.created_at,
            updated_at=policy.state.updated_at,
            created_by=policy.state.created_by,
            matcher_count=len(policy.state.claim_matchers),
            group_count=len(policy.state.allowed_group_ids),
        )

        return self.ok(dto)
