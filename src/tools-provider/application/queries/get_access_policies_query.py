"""Get access policies query with handler."""

from dataclasses import dataclass
from typing import Any, List, Optional

from domain.repositories import AccessPolicyDtoRepository
from integration.models.access_policy_dto import AccessPolicyDto
from neuroglia.core import OperationResult
from neuroglia.mediation import Query, QueryHandler


@dataclass
class GetAccessPoliciesQuery(Query[OperationResult[List[AccessPolicyDto]]]):
    """Query to retrieve access policies.

    Can filter by active status and/or group ID.
    """

    include_inactive: bool = False
    """Include inactive policies (default: False)."""

    group_id: Optional[str] = None
    """Filter by policies granting access to this group (optional)."""

    user_info: Optional[dict[str, Any]] = None
    """User information from authentication context."""


class GetAccessPoliciesQueryHandler(QueryHandler[GetAccessPoliciesQuery, OperationResult[List[AccessPolicyDto]]]):
    """Handle access policy retrieval.

    Uses AccessPolicyDtoRepository (read model) for efficient MongoDB queries.
    This follows CQRS: Commands use EventSourcingRepository, Queries use AccessPolicyDtoRepository.
    """

    def __init__(self, access_policy_repository: AccessPolicyDtoRepository):
        super().__init__()
        self.access_policy_repository = access_policy_repository

    async def handle_async(self, request: GetAccessPoliciesQuery) -> OperationResult[List[AccessPolicyDto]]:
        """Handle get access policies query."""
        query = request

        # Apply filters
        if query.group_id:
            # Get policies granting access to a specific group
            policies = await self.access_policy_repository.get_by_group_id_async(query.group_id)

            # Optionally filter out inactive
            if not query.include_inactive:
                policies = [p for p in policies if p.is_active]
        elif query.include_inactive:
            # Get all policies (including inactive)
            policies = await self.access_policy_repository.get_all_async()
        else:
            # Get only active policies
            policies = await self.access_policy_repository.get_active_async()

        return self.ok(policies)


@dataclass
class GetAccessPolicyByIdQuery(Query[OperationResult[AccessPolicyDto]]):
    """Query to retrieve a single access policy by ID."""

    policy_id: str
    """ID of the policy to retrieve."""

    user_info: Optional[dict[str, Any]] = None
    """User information from authentication context."""


class GetAccessPolicyByIdQueryHandler(QueryHandler[GetAccessPolicyByIdQuery, OperationResult[AccessPolicyDto]]):
    """Handle single access policy retrieval."""

    def __init__(self, access_policy_repository: AccessPolicyDtoRepository):
        super().__init__()
        self.access_policy_repository = access_policy_repository

    async def handle_async(self, request: GetAccessPolicyByIdQuery) -> OperationResult[AccessPolicyDto]:
        """Handle get access policy by ID query."""
        query = request

        policy = await self.access_policy_repository.get_async(query.policy_id)
        if not policy:
            return self.not_found(AccessPolicyDto, query.policy_id)

        return self.ok(policy)
