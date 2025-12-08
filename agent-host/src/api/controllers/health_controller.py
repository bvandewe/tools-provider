"""Health check controller for system component status."""

import logging
import time
from enum import Enum
from typing import Any, Optional

import httpx
from classy_fastapi.decorators import get
from fastapi import Depends
from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from neuroglia.mvc import ControllerBase
from pydantic import BaseModel

from api.dependencies import get_access_token, get_current_user
from application.settings import app_settings

logger = logging.getLogger(__name__)


class ComponentStatus(str, Enum):
    """Status of a system component."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ComponentHealth(BaseModel):
    """Health status of a single component."""

    name: str
    status: ComponentStatus
    message: str
    latency_ms: Optional[float] = None
    details: Optional[dict[str, Any]] = None


class SystemHealthResponse(BaseModel):
    """Complete system health status."""

    overall_status: ComponentStatus
    message: str
    components: list[ComponentHealth]
    checked_at: str


class HealthController(ControllerBase):
    """Controller for system health check endpoints.

    Provides health status for all dependent components so the UI
    can show users what's working and what's not.

    Components checked:
    1. Agent Host (this service) - always healthy if responding
    2. Ollama LLM - checks model availability
    3. Tools Provider - checks API connectivity
    4. Token Exchange - checks if tokens can be refreshed
    """

    def __init__(self, service_provider: ServiceProviderBase, mapper: Mapper, mediator: Mediator):
        super().__init__(service_provider, mapper, mediator)

    @get("/components")
    async def check_components(
        self,
        user: dict[str, Any] = Depends(get_current_user),
        access_token: str = Depends(get_access_token),
    ) -> SystemHealthResponse:
        """
        Check health of all system components.

        Requires authentication to check components that need user context
        (like token refresh and Tools Provider access).

        Returns status for each component in the request chain:
        - Agent Host: This service
        - Ollama: The LLM backend
        - Tools Provider: Tool discovery and execution
        - Token Refresh: OAuth2 token lifecycle
        """
        components: list[ComponentHealth] = []
        from datetime import datetime, timezone

        # 1. Agent Host - always healthy if we're responding
        components.append(
            ComponentHealth(
                name="Agent Host",
                status=ComponentStatus.HEALTHY,
                message="Service is running",
                details={"version": app_settings.app_version},
            )
        )

        # 2. Check Ollama LLM
        ollama_health = await self._check_ollama()
        components.append(ollama_health)

        # 3. Check Tools Provider
        tools_provider_health = await self._check_tools_provider(access_token)
        components.append(tools_provider_health)

        # 4. Check Token Refresh (implicit - if we got here with valid token)
        components.append(
            ComponentHealth(
                name="Authentication",
                status=ComponentStatus.HEALTHY,
                message="Session is valid",
                details={"user": user.get("preferred_username", user.get("email", "unknown"))},
            )
        )

        # Calculate overall status
        statuses = [c.status for c in components]
        if all(s == ComponentStatus.HEALTHY for s in statuses):
            overall = ComponentStatus.HEALTHY
            message = "All systems operational"
        elif any(s == ComponentStatus.UNHEALTHY for s in statuses):
            overall = ComponentStatus.UNHEALTHY
            unhealthy = [c.name for c in components if c.status == ComponentStatus.UNHEALTHY]
            message = f"Issues detected: {', '.join(unhealthy)}"
        else:
            overall = ComponentStatus.DEGRADED
            message = "Some components have warnings"

        return SystemHealthResponse(
            overall_status=overall,
            message=message,
            components=components,
            checked_at=datetime.now(timezone.utc).isoformat(),
        )

    async def _check_ollama(self) -> ComponentHealth:
        """Check Ollama LLM availability and model status."""
        start = time.time()

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Check if Ollama is running
                response = await client.get(f"{app_settings.ollama_url}/api/tags")
                latency = (time.time() - start) * 1000

                if response.status_code != 200:
                    return ComponentHealth(
                        name="AI Model (Ollama)",
                        status=ComponentStatus.UNHEALTHY,
                        message=f"Ollama returned status {response.status_code}",
                        latency_ms=latency,
                    )

                data = response.json()
                models = data.get("models", [])
                model_names = [m.get("name", "") for m in models]

                # Check if configured model is available
                configured_model = app_settings.ollama_model
                model_base = configured_model.split(":")[0]

                model_found = any(configured_model in m or m.startswith(model_base) for m in model_names)

                if not model_found:
                    return ComponentHealth(
                        name="AI Model (Ollama)",
                        status=ComponentStatus.UNHEALTHY,
                        message=f"Model '{configured_model}' not found",
                        latency_ms=latency,
                        details={
                            "configured_model": configured_model,
                            "available_models": model_names[:5],  # Show first 5
                            "hint": f"Run: ollama pull {configured_model}",
                        },
                    )

                return ComponentHealth(
                    name="AI Model (Ollama)",
                    status=ComponentStatus.HEALTHY,
                    message=f"Model '{configured_model}' ready",
                    latency_ms=latency,
                    details={"model": configured_model, "models_available": len(models)},
                )

        except httpx.ConnectError:
            return ComponentHealth(
                name="AI Model (Ollama)",
                status=ComponentStatus.UNHEALTHY,
                message="Cannot connect to Ollama",
                details={
                    "url": app_settings.ollama_url,
                    "hint": "Ensure Ollama is running (ollama serve)",
                },
            )
        except httpx.TimeoutException:
            return ComponentHealth(
                name="AI Model (Ollama)",
                status=ComponentStatus.UNHEALTHY,
                message="Ollama connection timed out",
                details={"url": app_settings.ollama_url},
            )
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return ComponentHealth(
                name="AI Model (Ollama)",
                status=ComponentStatus.UNKNOWN,
                message=f"Health check error: {str(e)}",
            )

    async def _check_tools_provider(self, access_token: str) -> ComponentHealth:
        """Check Tools Provider API connectivity."""
        start = time.time()

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{app_settings.tools_provider_url}/api/agent/tools",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                latency = (time.time() - start) * 1000

                if response.status_code == 200:
                    data = response.json()
                    tools = data.get("data", data) if isinstance(data, dict) else data
                    tool_count = len(tools) if isinstance(tools, list) else 0

                    return ComponentHealth(
                        name="Tools Provider",
                        status=ComponentStatus.HEALTHY,
                        message=f"{tool_count} tools available",
                        latency_ms=latency,
                        details={"tool_count": tool_count},
                    )
                elif response.status_code == 401:
                    return ComponentHealth(
                        name="Tools Provider",
                        status=ComponentStatus.UNHEALTHY,
                        message="Authentication failed",
                        latency_ms=latency,
                        details={"hint": "Token may be invalid or expired"},
                    )
                elif response.status_code == 403:
                    return ComponentHealth(
                        name="Tools Provider",
                        status=ComponentStatus.DEGRADED,
                        message="No tools accessible (check permissions)",
                        latency_ms=latency,
                    )
                else:
                    return ComponentHealth(
                        name="Tools Provider",
                        status=ComponentStatus.UNHEALTHY,
                        message=f"Returned status {response.status_code}",
                        latency_ms=latency,
                    )

        except httpx.ConnectError:
            return ComponentHealth(
                name="Tools Provider",
                status=ComponentStatus.UNHEALTHY,
                message="Cannot connect to Tools Provider",
                details={
                    "url": app_settings.tools_provider_url,
                    "hint": "Ensure Tools Provider service is running",
                },
            )
        except httpx.TimeoutException:
            return ComponentHealth(
                name="Tools Provider",
                status=ComponentStatus.UNHEALTHY,
                message="Connection timed out",
                details={"url": app_settings.tools_provider_url},
            )
        except Exception as e:
            logger.error(f"Tools Provider health check failed: {e}")
            return ComponentHealth(
                name="Tools Provider",
                status=ComponentStatus.UNKNOWN,
                message=f"Health check error: {str(e)}",
            )
