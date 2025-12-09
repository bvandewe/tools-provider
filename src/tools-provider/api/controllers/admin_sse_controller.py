"""Admin SSE controller for real-time admin dashboard updates.

This controller provides Server-Sent Events (SSE) for the admin UI to receive
real-time notifications when sources, tools, groups, or policies change.

Unlike the BFF SSE endpoint (which streams tool lists for AI agents), this
endpoint streams administrative events for the dashboard UI.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from api.dependencies import require_roles
from classy_fastapi.decorators import get
from classy_fastapi.routable import Routable
from fastapi import Depends, Request
from fastapi.responses import StreamingResponse
from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from neuroglia.mvc import ControllerBase
from neuroglia.mvc.controller_base import generate_unique_id_function
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# ============================================================================
# SSE EVENT MODELS
# ============================================================================


class AdminSSEEvent(BaseModel):
    """SSE event structure for admin notifications."""

    event: str
    data: str
    id: Optional[str] = None
    retry: Optional[int] = None

    def format(self) -> str:
        """Format as SSE message."""
        lines = []
        if self.id:
            lines.append(f"id: {self.id}")
        if self.retry:
            lines.append(f"retry: {self.retry}")
        lines.append(f"event: {self.event}")
        lines.append(f"data: {self.data}")
        return "\n".join(lines) + "\n\n"


@dataclass
class AdminEventPayload:
    """Payload structure for admin events."""

    entity_type: str  # source, tool, group, policy
    action: str  # created, updated, deleted, enabled, disabled, etc.
    entity_id: str
    entity_name: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


# ============================================================================
# ADMIN SSE CONNECTION MANAGER
# ============================================================================


class AdminSSEManager:
    """Manages admin SSE connections and broadcasts events.

    This is a singleton that maintains active admin connections and
    provides methods to broadcast events to all connected admins.
    """

    _instance: Optional["AdminSSEManager"] = None
    _lock = asyncio.Lock()

    def __init__(self) -> None:
        """Initialize connection tracking."""
        if not hasattr(self, "_initialized"):
            self._connections: Set[asyncio.Queue] = set()
            self._event_counter: int = 0
            self._shutting_down: bool = False
            self._initialized = True

    def __new__(cls) -> "AdminSSEManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "AdminSSEManager":
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def is_shutting_down(self) -> bool:
        """Check if the manager is shutting down."""
        return self._shutting_down

    async def shutdown(self) -> None:
        """Gracefully shutdown all SSE connections.

        Called during application shutdown to close all active connections
        without waiting for clients to disconnect.
        """
        logger.info(f"Shutting down Admin SSE Manager with {len(self._connections)} active connections")
        self._shutting_down = True

        async with self._lock:
            # Send shutdown event to all connections
            shutdown_event = AdminSSEEvent(
                event="shutdown",
                data=json.dumps(
                    {
                        "message": "Server is shutting down",
                        "timestamp": time.time(),
                    }
                ),
            )

            for queue in self._connections:
                try:
                    queue.put_nowait(shutdown_event)
                except asyncio.QueueFull:
                    pass

            # Clear all connections
            self._connections.clear()

        logger.info("Admin SSE Manager shutdown complete")

    async def add_connection(self) -> asyncio.Queue:
        """Add a new admin connection and return its event queue."""
        if self._shutting_down:
            raise RuntimeError("SSE Manager is shutting down")

        async with self._lock:
            queue: asyncio.Queue = asyncio.Queue()
            self._connections.add(queue)
            logger.info(f"Admin SSE connection added. Total connections: {len(self._connections)}")
            return queue

    async def remove_connection(self, queue: asyncio.Queue) -> None:
        """Remove an admin connection."""
        async with self._lock:
            self._connections.discard(queue)
            logger.info(f"Admin SSE connection removed. Total connections: {len(self._connections)}")

    async def broadcast(self, payload: AdminEventPayload) -> None:
        """Broadcast an event to all connected admins."""
        async with self._lock:
            self._event_counter += 1
            event_id = str(self._event_counter)

            event = AdminSSEEvent(
                event=f"{payload.entity_type}_{payload.action}",
                data=json.dumps(
                    {
                        "entity_type": payload.entity_type,
                        "action": payload.action,
                        "entity_id": payload.entity_id,
                        "entity_name": payload.entity_name,
                        "details": payload.details,
                        "timestamp": payload.timestamp,
                    }
                ),
                id=event_id,
            )

            dead_connections: List[asyncio.Queue] = []

            for queue in self._connections:
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    # Connection is backed up, mark for removal
                    dead_connections.append(queue)
                    logger.warning("Admin SSE queue full, removing connection")

            # Remove dead connections
            for queue in dead_connections:
                self._connections.discard(queue)

    @property
    def connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self._connections)


# Global instance for easy access from event handlers
admin_sse_manager = AdminSSEManager.get_instance()


# ============================================================================
# CONTROLLER
# ============================================================================


class AdminSSEController(ControllerBase):
    """Controller for Admin SSE streaming endpoint.

    Provides real-time event streaming for the admin dashboard:
    - Source events (registered, updated, deleted, health changes)
    - Tool events (discovered, enabled, disabled, deprecated)
    - Group events (created, updated, activated, deactivated)
    - Policy events (defined, updated, activated, deactivated)

    **RBAC Protected**: Only users with 'admin' or 'manager' roles can connect.
    """

    def __init__(self, service_provider: ServiceProviderBase, mapper: Mapper, mediator: Mediator):
        self.service_provider = service_provider
        self.mapper = mapper
        self.mediator = mediator
        self.name = "Admin SSE"
        self.sse_manager = AdminSSEManager.get_instance()

        # Call Routable.__init__ directly with custom prefix
        Routable.__init__(
            self,
            prefix="/admin",
            tags=["Admin - Real-time Events"],
            generate_unique_id_function=generate_unique_id_function,
        )

    @get("/sse", response_class=StreamingResponse)
    async def sse_endpoint(
        self,
        request: Request,
        user: dict = Depends(require_roles("admin", "manager")),
    ):
        """Server-Sent Events endpoint for admin dashboard real-time updates.

        Provides a persistent connection for the admin UI to receive
        notifications when sources, tools, groups, or policies change.

        **Usage:**
        ```
        GET /api/admin/sse
        Authorization: Bearer <admin_jwt>
        Accept: text/event-stream
        ```

        **Event Types:**
        - `connected`: Initial connection acknowledgment
        - `source_registered`, `source_updated`, `source_deleted`, `source_health_changed`
        - `tool_discovered`, `tool_enabled`, `tool_disabled`, `tool_deprecated`
        - `group_created`, `group_updated`, `group_activated`, `group_deactivated`
        - `policy_defined`, `policy_updated`, `policy_activated`, `policy_deactivated`
        - `heartbeat`: Keep-alive signal (every 30 seconds)

        **Example SSE Events:**
        ```
        event: connected
        data: {"message": "Connected to Admin SSE", "timestamp": 1234567890}

        event: source_registered
        data: {"entity_type": "source", "action": "registered", "entity_id": "...", ...}

        event: heartbeat
        data: {"timestamp": 1234567890}
        ```

        **RBAC Protected**: Requires 'admin' or 'manager' role.
        """
        # Get user info for logging
        username = user.get("preferred_username") or user.get("email") or "unknown"
        logger.info(f"Admin SSE connection initiated by {username}")

        # Define heartbeat interval
        heartbeat_interval = 30  # seconds

        async def event_generator():
            """Generate SSE events for admin dashboard."""
            queue: Optional[asyncio.Queue] = None
            try:
                # Add connection to manager
                queue = await self.sse_manager.add_connection()

                # Send connected event
                yield AdminSSEEvent(
                    event="connected",
                    data=json.dumps(
                        {
                            "message": "Connected to Admin SSE",
                            "timestamp": time.time(),
                            "user": username,
                            "active_connections": self.sse_manager.connection_count,
                        }
                    ),
                ).format()

                # Main event loop
                last_heartbeat = time.time()

                while True:
                    # Check if server is shutting down
                    if self.sse_manager.is_shutting_down:
                        logger.info(f"Admin SSE shutting down, closing connection for {username}")
                        break

                    # Check if client disconnected
                    if await request.is_disconnected():
                        logger.info(f"Admin SSE client {username} disconnected")
                        break

                    try:
                        # Wait for event with timeout for heartbeat
                        event = await asyncio.wait_for(queue.get(), timeout=1.0)
                        yield event.format()

                        # Check if this is a shutdown event
                        if event.event == "shutdown":
                            break
                    except asyncio.TimeoutError:
                        # No event, check if heartbeat needed
                        current_time = time.time()
                        if current_time - last_heartbeat >= heartbeat_interval:
                            yield AdminSSEEvent(
                                event="heartbeat",
                                data=json.dumps(
                                    {
                                        "timestamp": current_time,
                                        "active_connections": self.sse_manager.connection_count,
                                    }
                                ),
                            ).format()
                            last_heartbeat = current_time

            except RuntimeError as e:
                # Handle "SSE Manager is shutting down" error
                logger.info(f"Admin SSE connection rejected for {username}: {e}")
            except asyncio.CancelledError:
                logger.info(f"Admin SSE connection cancelled for {username}")
            except Exception as e:
                logger.error(f"Admin SSE error for {username}: {e}")
                yield AdminSSEEvent(
                    event="error",
                    data=json.dumps({"message": str(e), "timestamp": time.time()}),
                ).format()
            finally:
                # Cleanup connection
                if queue:
                    await self.sse_manager.remove_connection(queue)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            },
        )

    @get("/sse/stats")
    async def get_sse_stats(
        self,
        user: dict = Depends(require_roles("admin")),
    ):
        """Get admin SSE connection statistics.

        Returns the number of active admin connections.

        **Admin Only**: Only users with 'admin' role can view stats.
        """
        return {
            "active_connections": self.sse_manager.connection_count,
            "timestamp": time.time(),
        }


# ============================================================================
# HELPER FUNCTIONS FOR EVENT BROADCASTING
# ============================================================================


async def broadcast_source_event(action: str, source_id: str, source_name: str, details: Optional[Dict[str, Any]] = None) -> None:
    """Broadcast a source event to all connected admins."""
    await admin_sse_manager.broadcast(
        AdminEventPayload(
            entity_type="source",
            action=action,
            entity_id=source_id,
            entity_name=source_name,
            details=details or {},
        )
    )


async def broadcast_tool_event(action: str, tool_id: str, tool_name: str, details: Optional[Dict[str, Any]] = None) -> None:
    """Broadcast a tool event to all connected admins."""
    await admin_sse_manager.broadcast(
        AdminEventPayload(
            entity_type="tool",
            action=action,
            entity_id=tool_id,
            entity_name=tool_name,
            details=details or {},
        )
    )


async def broadcast_group_event(action: str, group_id: str, group_name: str, details: Optional[Dict[str, Any]] = None) -> None:
    """Broadcast a group event to all connected admins."""
    await admin_sse_manager.broadcast(
        AdminEventPayload(
            entity_type="group",
            action=action,
            entity_id=group_id,
            entity_name=group_name,
            details=details or {},
        )
    )


async def broadcast_policy_event(action: str, policy_id: str, policy_name: str, details: Optional[Dict[str, Any]] = None) -> None:
    """Broadcast a policy event to all connected admins."""
    await admin_sse_manager.broadcast(
        AdminEventPayload(
            entity_type="policy",
            action=action,
            entity_id=policy_id,
            entity_name=policy_name,
            details=details or {},
        )
    )
