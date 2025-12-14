"""Access Policies API controller with dual authentication (Session + JWT)."""

from classy_fastapi.decorators import delete, get, post, put
from fastapi import Depends, Query
from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from neuroglia.mvc import ControllerBase
from pydantic import BaseModel, Field

from api.dependencies import require_roles
from application.commands import (
    ActivateAccessPolicyCommand,
    ClaimMatcherInput,
    DeactivateAccessPolicyCommand,
    DefineAccessPolicyCommand,
    DeleteAccessPolicyCommand,
    UpdateAccessPolicyCommand,
)
from application.queries import GetAccessPoliciesQuery, GetAccessPolicyByIdQuery


class ClaimMatcherRequest(BaseModel):
    """Request model for a claim matcher rule."""

    json_path: str = Field(..., description="JSONPath-like path to the claim (e.g., 'realm_access.roles')")
    operator: str = Field(..., description="Comparison operator: equals, contains, matches, not_equals, not_contains, in, not_in, exists")
    value: str = Field(..., description="Value to compare against")


class DefineAccessPolicyRequest(BaseModel):
    """Request model for defining a new access policy."""

    name: str = Field(..., min_length=1, max_length=255, description="Human-readable name for the policy")
    claim_matchers: list[ClaimMatcherRequest] = Field(..., min_length=1, description="List of claim matchers (evaluated with AND logic)")
    allowed_group_ids: list[str] = Field(..., min_length=1, description="Tool group IDs this policy grants access to")
    description: str | None = Field(None, max_length=1000, description="Description of the policy's purpose")
    priority: int = Field(0, ge=0, description="Evaluation order (higher = earlier). Default: 0")


class UpdateAccessPolicyRequest(BaseModel):
    """Request model for updating an access policy."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    claim_matchers: list[ClaimMatcherRequest] | None = None
    allowed_group_ids: list[str] | None = None
    priority: int | None = Field(None, ge=0)


class DeactivateAccessPolicyRequest(BaseModel):
    """Request model for deactivating an access policy."""

    reason: str | None = Field(None, max_length=500, description="Optional reason for deactivation")


class PoliciesController(ControllerBase):
    """Controller for access policy management endpoints with dual authentication.

    Access policies map JWT claims to allowed tool groups, enabling
    fine-grained access control for AI agents.

    **RBAC Protected**: Only users with 'admin' role can manage access policies.
    """

    def __init__(self, service_provider: ServiceProviderBase, mapper: Mapper, mediator: Mediator):
        super().__init__(service_provider, mapper, mediator)

    @get("/")
    async def get_policies(
        self,
        include_inactive: bool = Query(False, description="Include inactive policies"),
        group_id: str | None = Query(None, description="Filter by group ID"),
        user: dict = Depends(require_roles("admin")),
    ):
        """Get all access policies.

        **RBAC Protected**: Requires 'admin' role.

        Supports authentication via:
        - Session cookie (from OAuth2 login)
        - JWT Bearer token (for API clients)
        """
        query = GetAccessPoliciesQuery(
            include_inactive=include_inactive,
            group_id=group_id,
            user_info=user,
        )
        result = await self.mediator.execute_async(query)
        return self.process(result)

    @get("/{policy_id}")
    async def get_policy(
        self,
        policy_id: str,
        user: dict = Depends(require_roles("admin")),
    ):
        """Get a single access policy by ID.

        **RBAC Protected**: Requires 'admin' role.

        Supports authentication via:
        - Session cookie (from OAuth2 login)
        - JWT Bearer token (for API clients)
        """
        query = GetAccessPolicyByIdQuery(policy_id=policy_id, user_info=user)
        result = await self.mediator.execute_async(query)
        return self.process(result)

    @post("/")
    async def define_policy(
        self,
        request: DefineAccessPolicyRequest,
        user: dict = Depends(require_roles("admin")),
    ):
        """Define a new access policy.

        **RBAC Protected**: Requires 'admin' role.

        Creates a policy that maps JWT claims to allowed tool groups.
        All claim matchers are evaluated with AND logic (all must match).
        Multiple policies are evaluated with OR logic (any can grant access).

        Supports authentication via:
        - Session cookie (from OAuth2 login)
        - JWT Bearer token (for API clients)
        """
        # Convert request to command input
        matchers = [
            ClaimMatcherInput(
                json_path=m.json_path,
                operator=m.operator,
                value=m.value,
            )
            for m in request.claim_matchers
        ]

        command = DefineAccessPolicyCommand(
            name=request.name,
            claim_matchers=matchers,
            allowed_group_ids=request.allowed_group_ids,
            description=request.description,
            priority=request.priority,
            user_info=user,
        )

        result = await self.mediator.execute_async(command)
        return self.process(result)

    @put("/{policy_id}")
    async def update_policy(
        self,
        policy_id: str,
        request: UpdateAccessPolicyRequest,
        user: dict = Depends(require_roles("admin")),
    ):
        """Update an existing access policy.

        **RBAC Protected**: Requires 'admin' role.

        Only provided fields are updated.

        Supports authentication via:
        - Session cookie (from OAuth2 login)
        - JWT Bearer token (for API clients)
        """
        # Convert request matchers if provided
        matchers = None
        if request.claim_matchers is not None:
            matchers = [
                ClaimMatcherInput(
                    json_path=m.json_path,
                    operator=m.operator,
                    value=m.value,
                )
                for m in request.claim_matchers
            ]

        command = UpdateAccessPolicyCommand(
            policy_id=policy_id,
            name=request.name,
            description=request.description,
            claim_matchers=matchers,
            allowed_group_ids=request.allowed_group_ids,
            priority=request.priority,
            user_info=user,
        )

        result = await self.mediator.execute_async(command)
        return self.process(result)

    @post("/{policy_id}/activate")
    async def activate_policy(
        self,
        policy_id: str,
        user: dict = Depends(require_roles("admin")),
    ):
        """Activate an access policy.

        **RBAC Protected**: Requires 'admin' role.

        Only active policies participate in access resolution.

        Supports authentication via:
        - Session cookie (from OAuth2 login)
        - JWT Bearer token (for API clients)
        """
        command = ActivateAccessPolicyCommand(policy_id=policy_id, user_info=user)
        result = await self.mediator.execute_async(command)
        return self.process(result)

    @post("/{policy_id}/deactivate")
    async def deactivate_policy(
        self,
        policy_id: str,
        request: DeactivateAccessPolicyRequest | None = None,
        user: dict = Depends(require_roles("admin")),
    ):
        """Deactivate an access policy.

        **RBAC Protected**: Requires 'admin' role.

        Deactivated policies do not participate in access resolution.

        Supports authentication via:
        - Session cookie (from OAuth2 login)
        - JWT Bearer token (for API clients)
        """
        command = DeactivateAccessPolicyCommand(
            policy_id=policy_id,
            reason=request.reason if request else None,
            user_info=user,
        )
        result = await self.mediator.execute_async(command)
        return self.process(result)

    @delete("/{policy_id}")
    async def delete_policy(
        self,
        policy_id: str,
        user: dict = Depends(require_roles("admin")),
    ):
        """Delete an access policy.

        **RBAC Protected**: Requires 'admin' role.

        Supports authentication via:
        - Session cookie (from OAuth2 login)
        - JWT Bearer token (for API clients)
        """
        command = DeleteAccessPolicyCommand(policy_id=policy_id, user_info=user)
        result = await self.mediator.execute_async(command)
        return self.process(result)
