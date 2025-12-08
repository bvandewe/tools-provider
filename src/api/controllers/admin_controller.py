"""Admin controller for system administration endpoints.

This controller provides administrative endpoints for:
- Circuit breaker monitoring and reset
- System health checks
- Cache management

All endpoints require admin or manager role.
"""

import logging
from typing import Any, Dict, Optional

from classy_fastapi.decorators import get, post
from fastapi import Depends, HTTPException
from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from neuroglia.mvc import ControllerBase
from pydantic import BaseModel

from api.dependencies import require_roles
from application.services.tool_executor import ToolExecutor
from infrastructure.adapters.keycloak_token_exchanger import KeycloakTokenExchanger

logger = logging.getLogger(__name__)


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================


class CircuitBreakerState(BaseModel):
    """Circuit breaker state information."""

    state: str
    failure_count: int
    last_failure_time: Optional[float] = None


class CircuitBreakersResponse(BaseModel):
    """Response containing all circuit breaker states."""

    token_exchange: CircuitBreakerState
    tool_execution: Dict[str, CircuitBreakerState]


class ResetCircuitBreakerRequest(BaseModel):
    """Request to reset a specific circuit breaker."""

    type: str  # "token_exchange" or "tool_execution"
    key: Optional[str] = None  # For tool_execution, the source key


class ResetCircuitBreakerResponse(BaseModel):
    """Response after resetting circuit breaker(s)."""

    success: bool
    message: str
    new_state: Optional[Dict[str, Any]] = None


# ============================================================================
# ADMIN CONTROLLER
# ============================================================================


class AdminController(ControllerBase):
    """Controller for administrative operations.

    Provides endpoints for monitoring and managing:
    - Circuit breakers (token exchange and tool execution)
    - System health and diagnostics
    """

    def __init__(self, service_provider: ServiceProviderBase, mapper: Mapper, mediator: Mediator):
        super().__init__(service_provider, mapper, mediator)
        self._tool_executor: Optional[ToolExecutor] = None
        self._token_exchanger: Optional[KeycloakTokenExchanger] = None

    def _get_tool_executor(self) -> ToolExecutor:
        """Lazy-load ToolExecutor from service provider."""
        if self._tool_executor is None:
            self._tool_executor = self.service_provider.get_required_service(ToolExecutor)
        assert self._tool_executor is not None
        return self._tool_executor

    def _get_token_exchanger(self) -> KeycloakTokenExchanger:
        """Lazy-load KeycloakTokenExchanger from service provider."""
        if self._token_exchanger is None:
            self._token_exchanger = self.service_provider.get_required_service(KeycloakTokenExchanger)
        assert self._token_exchanger is not None
        return self._token_exchanger

    @get(
        "/circuit-breakers",
        response_model=CircuitBreakersResponse,
        summary="Get circuit breaker states",
        description="Returns the current state of all circuit breakers in the system.",
    )
    async def get_circuit_breakers(
        self,
        user: dict = Depends(require_roles("admin", "manager")),
    ) -> CircuitBreakersResponse:
        """Get all circuit breaker states for monitoring.

        Circuit breakers protect the system from cascading failures:
        - **token_exchange**: Protects Keycloak token exchange calls
        - **tool_execution**: Per-source circuit breakers for upstream API calls

        States:
        - **closed**: Normal operation, requests flow through
        - **open**: Circuit tripped, requests are rejected immediately
        - **half_open**: Testing if the service has recovered
        """
        token_exchanger = self._get_token_exchanger()
        tool_executor = self._get_tool_executor()

        token_exchange_state = token_exchanger.get_circuit_state()
        tool_execution_states = tool_executor.get_circuit_states()

        return CircuitBreakersResponse(
            token_exchange=CircuitBreakerState(**token_exchange_state),
            tool_execution={key: CircuitBreakerState(**state) for key, state in tool_execution_states.items()},
        )

    @post(
        "/circuit-breakers/reset",
        response_model=ResetCircuitBreakerResponse,
        summary="Reset a circuit breaker",
        description="Manually reset a circuit breaker to closed state after resolving the underlying issue.",
    )
    async def reset_circuit_breaker(
        self,
        request: ResetCircuitBreakerRequest,
        user: dict = Depends(require_roles("admin")),
    ) -> ResetCircuitBreakerResponse:
        """Reset a circuit breaker to closed state.

        **Warning**: Only reset a circuit breaker after you've verified that the
        underlying issue has been resolved. If the problem persists, the circuit
        will open again after hitting the failure threshold.

        Args:
            type: The type of circuit breaker to reset:
                - "token_exchange": Reset the Keycloak token exchange circuit breaker
                - "tool_execution": Reset a tool execution circuit breaker (requires key)
            key: For tool_execution type, the source key to reset.
                 Use "all" to reset all tool execution circuit breakers.
        """
        reset_by = user.get("preferred_username") or user.get("email") or user.get("sub", "unknown")

        if request.type == "token_exchange":
            token_exchanger = self._get_token_exchanger()
            new_state = await token_exchanger.reset_circuit_breaker(reset_by=reset_by)
            logger.info(f"Admin '{reset_by}' reset token exchange circuit breaker")
            return ResetCircuitBreakerResponse(
                success=True,
                message="Token exchange circuit breaker reset to closed state",
                new_state=new_state,
            )

        elif request.type == "tool_execution":
            tool_executor = self._get_tool_executor()

            if not request.key:
                raise HTTPException(status_code=400, detail="Key is required for tool_execution circuit breaker reset")

            if request.key == "all":
                new_states = await tool_executor.reset_all_circuit_breakers(reset_by=reset_by)
                logger.info(f"Admin '{reset_by}' reset all tool execution circuit breakers")
                return ResetCircuitBreakerResponse(
                    success=True,
                    message=f"Reset {len(new_states)} tool execution circuit breakers",
                    new_state=new_states,
                )
            else:
                new_state = await tool_executor.reset_circuit_breaker(request.key, reset_by=reset_by)
                if new_state is None:
                    raise HTTPException(status_code=404, detail=f"No circuit breaker found for key: {request.key}")

                logger.info(f"Admin '{reset_by}' reset circuit breaker for '{request.key}'")
                return ResetCircuitBreakerResponse(
                    success=True,
                    message=f"Circuit breaker for '{request.key}' reset to closed state",
                    new_state=new_state,
                )

        else:
            raise HTTPException(status_code=400, detail=f"Invalid circuit breaker type: {request.type}. Use 'token_exchange' or 'tool_execution'")

    @get(
        "/health/token-exchange",
        summary="Token exchange health check",
        description="Check the health of the token exchange service including circuit breaker state.",
    )
    async def token_exchange_health(
        self,
        user: dict = Depends(require_roles("admin", "manager")),
    ) -> Dict[str, Any]:
        """Get token exchange service health status.

        Returns detailed information about:
        - Circuit breaker state
        - Token endpoint configuration
        - Local cache size
        """
        token_exchanger = self._get_token_exchanger()
        return await token_exchanger.health_check()
