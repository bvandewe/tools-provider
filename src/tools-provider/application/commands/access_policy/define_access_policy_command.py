"""Define access policy command with handler."""

import logging
import time
from dataclasses import dataclass
from typing import Any

from neuroglia.core import OperationResult
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_bus import CloudEventBus
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import CloudEventPublishingOptions
from neuroglia.mapping import Mapper
from neuroglia.mediation import Command, CommandHandler, Mediator
from neuroglia.observability.tracing import add_span_attributes
from observability import access_policies_defined, access_policy_processing_time
from opentelemetry import trace

from domain.entities.access_policy import AccessPolicy
from domain.models import ClaimMatcher
from integration.models.access_policy_dto import AccessPolicyDto

from ..command_handler_base import CommandHandlerBase

log = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


@dataclass
class ClaimMatcherInput:
    """Input structure for creating a ClaimMatcher.

    This is the API-facing representation of a claim matcher rule.
    """

    json_path: str
    """JSONPath-like path to the claim (e.g., 'realm_access.roles')."""

    operator: str
    """Comparison operator: equals, contains, matches, not_equals, not_contains, in, not_in, exists."""

    value: str
    """Value to compare against (or pattern for 'matches' operator)."""


@dataclass
class DefineAccessPolicyCommand(Command[OperationResult[AccessPolicyDto]]):
    """Command to define a new access policy.

    Creates a policy that maps JWT claims to allowed tool groups.
    """

    name: str
    """Human-readable name for the policy."""

    claim_matchers: list[ClaimMatcherInput]
    """List of claim matchers (evaluated with AND logic)."""

    allowed_group_ids: list[str]
    """Tool group IDs this policy grants access to."""

    description: str | None = None
    """Description of the policy's purpose."""

    priority: int = 0
    """Evaluation order (higher = earlier). Default: 0."""

    policy_id: str | None = None
    """Optional specific ID (defaults to UUID)."""

    user_info: dict[str, Any] | None = None
    """User information from authentication context."""


class DefineAccessPolicyCommandHandler(
    CommandHandlerBase,
    CommandHandler[DefineAccessPolicyCommand, OperationResult[AccessPolicyDto]],
):
    """Handler for defining new access policies."""

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

    async def handle_async(self, request: DefineAccessPolicyCommand) -> OperationResult[AccessPolicyDto]:
        """Handle the define access policy command."""
        command = request
        start_time = time.time()

        # Add business context to automatic span created by CQRS middleware
        add_span_attributes(
            {
                "access_policy.name": command.name,
                "access_policy.matcher_count": len(command.claim_matchers),
                "access_policy.group_count": len(command.allowed_group_ids),
                "access_policy.priority": command.priority,
                "access_policy.has_user_info": command.user_info is not None,
            }
        )

        # Validate inputs
        if not command.name or not command.name.strip():
            return self.bad_request("Access policy name is required")

        if not command.claim_matchers:
            return self.bad_request("At least one claim matcher is required")

        if not command.allowed_group_ids:
            return self.bad_request("At least one allowed group ID is required")

        # Convert input matchers to domain value objects
        try:
            from domain.enums import ClaimOperator

            matchers: list[ClaimMatcher] = []
            for matcher_input in command.claim_matchers:
                try:
                    operator = ClaimOperator(matcher_input.operator)
                except ValueError:
                    return self.bad_request(f"Invalid operator: {matcher_input.operator}. Valid operators: equals, contains, matches, not_equals, not_contains, in, not_in, exists")

                matchers.append(
                    ClaimMatcher(
                        json_path=matcher_input.json_path,
                        operator=operator,
                        value=matcher_input.value,
                    )
                )
        except Exception as e:
            return self.bad_request(f"Invalid claim matcher configuration: {str(e)}")

        # Get user ID from context
        defined_by = None
        if command.user_info:
            defined_by = command.user_info.get("sub") or command.user_info.get("email")

        # Create custom span for access policy creation logic
        with tracer.start_as_current_span("create_access_policy_entity") as span:
            try:
                # Create the aggregate
                access_policy = AccessPolicy(
                    name=command.name.strip(),
                    claim_matchers=matchers,
                    allowed_group_ids=command.allowed_group_ids,
                    description=command.description,
                    priority=command.priority,
                    defined_by=defined_by,
                    policy_id=command.policy_id,
                )

                span.set_attribute("access_policy.id", access_policy.id())
                span.set_attribute("access_policy.defined_by", defined_by or "unknown")
            except ValueError as e:
                return self.bad_request(str(e))

        # Persist to event store
        await self.access_policy_repository.add_async(access_policy)

        # Record metrics
        processing_time_ms = (time.time() - start_time) * 1000
        access_policies_defined.add(
            1,
            {
                "has_description": bool(command.description),
                "matcher_count": str(len(command.claim_matchers)),
                "priority": str(command.priority),
            },
        )
        access_policy_processing_time.record(processing_time_ms, {"operation": "define"})
        log.info(f"AccessPolicy defined in {processing_time_ms:.2f}ms: {access_policy.id()}")

        # Map to DTO for response
        # Note: Read model will be updated by projection handler
        dto = AccessPolicyDto(
            id=access_policy.id(),
            name=access_policy.state.name,
            description=access_policy.state.description,
            claim_matchers=[m.to_dict() for m in access_policy.state.claim_matchers],
            allowed_group_ids=list(access_policy.state.allowed_group_ids),
            priority=access_policy.state.priority,
            is_active=access_policy.state.is_active,
            created_at=access_policy.state.created_at,
            updated_at=access_policy.state.updated_at,
            created_by=access_policy.state.created_by,
            matcher_count=len(access_policy.state.claim_matchers),
            group_count=len(access_policy.state.allowed_group_ids),
        )

        return self.created(dto)
