"""Update access policy command with handler."""

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from neuroglia.core import OperationResult
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_bus import CloudEventBus
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import CloudEventPublishingOptions
from neuroglia.mapping import Mapper
from neuroglia.mediation import Command, CommandHandler, Mediator
from neuroglia.observability.tracing import add_span_attributes
from opentelemetry import trace

from domain.entities.access_policy import AccessPolicy
from domain.enums import ClaimOperator
from domain.models import ClaimMatcher
from integration.models.access_policy_dto import AccessPolicyDto

from .command_handler_base import CommandHandlerBase
from .define_access_policy_command import ClaimMatcherInput

log = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


@dataclass
class UpdateAccessPolicyCommand(Command[OperationResult[AccessPolicyDto]]):
    """Command to update an existing access policy.

    Updates can include name, description, matchers, groups, and/or priority.
    Only provided fields are updated.
    """

    policy_id: str
    """ID of the policy to update."""

    name: Optional[str] = None
    """New name (optional)."""

    description: Optional[str] = None
    """New description (optional)."""

    claim_matchers: Optional[List[ClaimMatcherInput]] = None
    """New list of claim matchers (optional, replaces all existing)."""

    allowed_group_ids: Optional[List[str]] = None
    """New list of allowed group IDs (optional, replaces all existing)."""

    priority: Optional[int] = None
    """New priority (optional)."""

    user_info: Optional[Dict[str, Any]] = None
    """User information from authentication context."""


class UpdateAccessPolicyCommandHandler(
    CommandHandlerBase,
    CommandHandler[UpdateAccessPolicyCommand, OperationResult[AccessPolicyDto]],
):
    """Handler for updating access policies."""

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

    async def handle_async(self, request: UpdateAccessPolicyCommand) -> OperationResult[AccessPolicyDto]:
        """Handle the update access policy command."""
        command = request
        start_time = time.time()

        # Add business context to automatic span
        add_span_attributes(
            {
                "access_policy.id": command.policy_id,
                "access_policy.update_name": command.name is not None,
                "access_policy.update_matchers": command.claim_matchers is not None,
                "access_policy.update_groups": command.allowed_group_ids is not None,
                "access_policy.update_priority": command.priority is not None,
            }
        )

        # Get user ID from context
        updated_by = None
        if command.user_info:
            updated_by = command.user_info.get("sub") or command.user_info.get("email")

        # Load existing policy
        policy = await self.access_policy_repository.get_async(command.policy_id)
        if not policy:
            return self.not_found(AccessPolicy, command.policy_id)

        changes_made = False

        with tracer.start_as_current_span("update_access_policy_entity") as span:
            # Update basic info
            if command.name is not None or command.description is not None:
                if policy.update(name=command.name, description=command.description, updated_by=updated_by):
                    changes_made = True

            # Update matchers
            if command.claim_matchers is not None:
                if not command.claim_matchers:
                    return self.bad_request("At least one claim matcher is required")

                try:
                    matchers: List[ClaimMatcher] = []
                    for matcher_input in command.claim_matchers:
                        try:
                            operator = ClaimOperator(matcher_input.operator)
                        except ValueError:
                            return self.bad_request(f"Invalid operator: {matcher_input.operator}")

                        matchers.append(
                            ClaimMatcher(
                                json_path=matcher_input.json_path,
                                operator=operator,
                                value=matcher_input.value,
                            )
                        )

                    if policy.update_matchers(matchers, updated_by=updated_by):
                        changes_made = True
                except Exception as e:
                    return self.bad_request(f"Invalid claim matcher configuration: {str(e)}")

            # Update groups
            if command.allowed_group_ids is not None:
                if not command.allowed_group_ids:
                    return self.bad_request("At least one allowed group ID is required")

                if policy.update_groups(command.allowed_group_ids, updated_by=updated_by):
                    changes_made = True

            # Update priority
            if command.priority is not None:
                if policy.set_priority(command.priority, updated_by=updated_by):
                    changes_made = True

            span.set_attribute("access_policy.changes_made", changes_made)

        # Only persist if changes were made
        if changes_made:
            await self.access_policy_repository.update_async(policy)
            log.info(f"AccessPolicy updated: {command.policy_id}")
        else:
            log.info(f"AccessPolicy unchanged (no updates needed): {command.policy_id}")

        # Record metrics
        processing_time_ms = (time.time() - start_time) * 1000
        log.debug(f"AccessPolicy update processed in {processing_time_ms:.2f}ms")

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
