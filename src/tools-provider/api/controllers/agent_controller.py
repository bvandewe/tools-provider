"""Agent API controller for Host Applications to discover and execute tools.

This controller provides the REST API that Host Applications use to interact
with the MCP Tools Provider on behalf of authenticated end users.

Endpoints:
1. GET /agent/tools - List tools accessible to the authenticated user
2. POST /agent/tools/call - Execute a tool with identity delegation
3. GET /agent/sse - SSE stream for real-time tool updates

See docs/architecture/mcp-protocol-decision.md for why this is NOT MCP-compliant.
"""

import asyncio
import json
import logging
import time
from typing import Any

from classy_fastapi.decorators import get, post
from fastapi import Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from neuroglia.mvc import ControllerBase
from pydantic import BaseModel, Field

from api.dependencies import get_current_user
from application.commands.execute_tool_command import ExecuteToolCommand
from application.queries.get_agent_tools_query import GetAgentToolsQuery, ToolManifestEntry

logger = logging.getLogger(__name__)


class ToolCallRequest(BaseModel):
    """Request model for executing a tool.

    Supports both our native format (tool_id) and MCP-style format (name).
    """

    tool_id: str | None = Field(None, description="ID of the tool to execute (native format)")
    name: str | None = Field(None, description="Name of the tool (MCP-style format)")
    arguments: dict[str, Any] = Field(default_factory=dict, description="Arguments to pass to the tool")
    validate_schema: bool | None = Field(None, description="Override schema validation (None = use tool default)")

    def get_tool_id(self) -> str:
        """Get the effective tool_id, preferring tool_id over name."""
        return self.tool_id or self.name or ""

    def model_post_init(self, __context) -> None:
        """Validate that either tool_id or name is provided."""
        if not self.tool_id and not self.name:
            raise ValueError("Either 'tool_id' or 'name' must be provided")


class ToolCallResponse(BaseModel):
    """Response model for tool execution."""

    tool_id: str
    status: str = Field(..., description="Execution status: completed, failed, pending")
    result: Any | None = Field(None, description="Tool execution result")
    error: dict[str, Any] | None = Field(None, description="Error details if failed")
    execution_time_ms: float | None = Field(None, description="Execution time in milliseconds")
    upstream_status: int | None = Field(None, description="HTTP status from upstream service")


class SSEEvent(BaseModel):
    """SSE event structure."""

    event: str
    data: str
    id: str | None = None
    retry: int | None = None

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


class AgentController(ControllerBase):
    """Controller for Host Application (BFF) tool discovery and execution.

    This controller provides the REST API that Host Applications use to:
    1. Discover available tools for a specific end user
    2. Execute tools with identity delegation via token exchange

    **Important:** This is NOT an MCP-compliant endpoint. Standard MCP clients
    (Claude Desktop, VS Code) cannot use this API directly because they cannot
    provide end-user JWT tokens. See docs/architecture/mcp-protocol-decision.md.

    **Required Integration Pattern:**
    Host Applications must:
    1. Authenticate users via OAuth2/Keycloak
    2. Obtain the user's JWT access token
    3. Pass the JWT in Authorization header to this API

    Authentication: JWT Bearer token only (no session support).
    """

    def __init__(self, service_provider: ServiceProviderBase, mapper: Mapper, mediator: Mediator):
        super().__init__(service_provider, mapper, mediator)

    @get("/tools")
    async def get_tools(
        self,
        user: dict = Depends(get_current_user),
    ):
        """Get the list of available tools for the authenticated end user.

        This endpoint returns tools that the user has access to based on:
        - Access policies matching the user's JWT claims
        - Enabled tool groups and sources

        **Usage:**
        ```
        GET /api/bff/tools
        Authorization: Bearer <user_jwt>
        ```

        Returns:
            List of tool manifests with tool_id, name, description, input_schema
        """
        query = GetAgentToolsQuery(claims=user)
        result = await self.mediator.execute_async(query)
        return self.process(result)

    @get("/sse", response_class=StreamingResponse)
    async def sse_endpoint(
        self,
        request: Request,
        user: dict = Depends(get_current_user),
    ):
        """Server-Sent Events endpoint for real-time tool discovery.

        Provides a persistent connection for Host Applications to receive
        tool list updates in real-time as access policies or tools change.

        **Usage:**
        ```
        GET /api/bff/sse
        Authorization: Bearer <user_jwt>
        Accept: text/event-stream
        ```

        **Event Types:**
        - `connected`: Initial connection acknowledgment
        - `tool_list`: List of available tools (sent on connect and on updates)
        - `heartbeat`: Keep-alive signal (every 30 seconds)
        - `error`: Error notification

        **Example SSE Events:**
        ```
        event: connected
        data: {"message": "Connected to MCP Tools Provider", "timestamp": 1234567890}

        event: tool_list
        data: {"tools": [...], "count": 42, "timestamp": 1234567890}

        event: heartbeat
        data: {"timestamp": 1234567890}
        ```
        """
        # Resolve initial tool list
        query = GetAgentToolsQuery(claims=user)
        result = await self.mediator.execute_async(query)

        if result.status != 200:
            raise HTTPException(
                status_code=result.status,
                detail=getattr(result, "errors", None) or "Failed to resolve tools",
            )

        initial_tools = result.data if result.data else []

        # Define heartbeat interval at outer scope
        heartbeat_interval = 30  # seconds

        # Get user info for logging
        username = user.get("preferred_username") or user.get("email") or "unknown"

        async def event_generator():
            """Generate SSE events."""
            pubsub = None

            try:
                # Send connected event
                yield SSEEvent(
                    event="connected",
                    data=json.dumps({"message": "Connected to MCP Tools Provider", "timestamp": time.time()}),
                ).format()

                # Send initial tool list
                yield SSEEvent(
                    event="tool_list",
                    data=json.dumps(
                        {
                            "tools": [self._tool_to_dict(t) for t in initial_tools],
                            "count": len(initial_tools),
                            "timestamp": time.time(),
                        }
                    ),
                ).format()

                # Subscribe to Redis pub/sub for updates
                redis_cache = self._get_redis_cache()

                if redis_cache:
                    try:
                        pubsub = await redis_cache.subscribe_to_updates("group_updated:*", "source_updated:*", "tool_updated:*")

                        # Listen for updates with heartbeat
                        last_heartbeat = time.time()

                        while True:
                            # Check for client disconnect
                            if await request.is_disconnected():
                                logger.info(f"Agent SSE client {username} disconnected")
                                break

                            # Check for pubsub messages (non-blocking)
                            try:
                                message = await asyncio.wait_for(pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0), timeout=2.0)

                                if message and message["type"] == "pmessage":
                                    logger.debug(f"Received update notification: {message['channel']}")

                                    # Re-fetch tool list
                                    query = GetAgentToolsQuery(claims=user, skip_cache=True)
                                    result = await self.mediator.execute_async(query)

                                    if result.status == 200:
                                        tools = result.data if result.data else []
                                        yield SSEEvent(
                                            event="tool_list",
                                            data=json.dumps(
                                                {
                                                    "tools": [self._tool_to_dict(t) for t in tools],
                                                    "count": len(tools),
                                                    "timestamp": time.time(),
                                                    "reason": "update",
                                                }
                                            ),
                                        ).format()
                            except TimeoutError:
                                pass  # No message, continue

                            # Send heartbeat
                            current_time = time.time()
                            if current_time - last_heartbeat >= heartbeat_interval:
                                yield SSEEvent(
                                    event="heartbeat",
                                    data=json.dumps({"timestamp": current_time}),
                                ).format()
                                last_heartbeat = current_time

                    except Exception as e:
                        logger.error(f"SSE pub/sub error: {e}")
                        yield SSEEvent(
                            event="error",
                            data=json.dumps({"message": "Connection error", "timestamp": time.time()}),
                        ).format()

                else:
                    # No Redis - fall back to polling-based updates
                    logger.warning("Redis not available, using heartbeat-only mode")

                    while True:
                        if await request.is_disconnected():
                            break

                        await asyncio.sleep(heartbeat_interval)
                        yield SSEEvent(
                            event="heartbeat",
                            data=json.dumps({"timestamp": time.time()}),
                        ).format()

            except asyncio.CancelledError:
                logger.info(f"Agent SSE connection cancelled for {username}")
            except Exception as e:
                logger.error(f"Agent SSE generator error for {username}: {e}")
                yield SSEEvent(
                    event="error",
                    data=json.dumps({"message": "Internal error", "timestamp": time.time()}),
                ).format()
            finally:
                # Cleanup pubsub connection
                if pubsub:
                    try:
                        await pubsub.unsubscribe()
                        await pubsub.close()
                    except Exception as e:
                        logger.debug(f"Ignoring pubsub cleanup error: {e}")

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            },
        )

    @post("/tools/call")
    async def execute_tool(
        self,
        request: ToolCallRequest,
        fastapi_request: Request,
        user: dict = Depends(get_current_user),
    ) -> ToolCallResponse:
        """Execute a tool on behalf of the authenticated end user.

        This endpoint provides secure tool execution with identity delegation:

        1. Validates the user has access to the tool (via access policies)
        2. Loads the tool definition and execution profile
        3. Validates arguments against JSON schema (if enabled)
        4. Exchanges the user's token for an upstream service token (RFC 8693)
        5. Executes the tool with the exchanged token
        6. Returns the result or error details

        **Usage:**
        ```
        POST /api/bff/tools/call
        Authorization: Bearer <user_jwt>
        Content-Type: application/json

        {
            "tool_id": "source123:get_users",
            "arguments": {"page": 1, "limit": 10}
        }
        ```

        **Identity Propagation:**
        The user's JWT is exchanged for an upstream service token via Keycloak
        token exchange (RFC 8693). This ensures the upstream service receives
        a token scoped to that service while preserving the user's identity.

        **Error Responses:**
        - 400: Invalid arguments (schema validation failed)
        - 401: Token exchange failed (unauthorized for upstream)
        - 403: Access denied (tool not available to this user)
        - 404: Tool not found or disabled
        - 503: Upstream service unavailable
        - 500: Internal server error
        """
        # Extract the raw bearer token for token exchange
        auth_header = fastapi_request.headers.get("Authorization", "")
        agent_token: str = ""  # nosec B105 - not a password, initializing token variable
        if auth_header.startswith("Bearer "):
            agent_token = auth_header[7:]

        if not agent_token:
            raise HTTPException(
                status_code=401,
                detail="Bearer token required for tool execution",
            )

        # Get the effective tool_id (supports both tool_id and name fields)
        effective_tool_id = request.get_tool_id()
        logger.debug(f"Tool call request: tool_id={request.tool_id}, name={request.name}, effective={effective_tool_id}")

        # Step 1: Verify agent has access to the tool
        # First, resolve which tools the agent can access
        tools_query = GetAgentToolsQuery(claims=user)
        tools_result = await self.mediator.execute_async(tools_query)

        if tools_result.status != 200:
            raise HTTPException(
                status_code=tools_result.status,
                detail="Failed to resolve agent tools",
            )

        # Check if requested tool is in the allowed list
        allowed_tools = tools_result.data or []
        tool_ids = [t.tool_id for t in allowed_tools]
        tool_names = [t.name for t in allowed_tools]

        # Match by tool_id first, then by name
        matched_tool_id = None
        if effective_tool_id in tool_ids:
            matched_tool_id = effective_tool_id
        elif effective_tool_id in tool_names:
            # Find the tool_id by name
            for t in allowed_tools:
                if t.name == effective_tool_id:
                    matched_tool_id = t.tool_id
                    break

        if not matched_tool_id:
            logger.warning(f"Agent attempted to execute unauthorized tool: {effective_tool_id}")
            raise HTTPException(
                status_code=403,
                detail=f"Access denied: Tool '{effective_tool_id}' is not available to this agent",
            )

        # Step 2: Execute the tool via command
        command = ExecuteToolCommand(
            tool_id=matched_tool_id,
            arguments=request.arguments,
            agent_token=agent_token,
            validate_schema=request.validate_schema,
            user_info=user,
        )

        result = await self.mediator.execute_async(command)

        # Step 3: Build response based on result
        if result.status == 200 and result.data:
            data = result.data
            return ToolCallResponse(
                tool_id=data.get("tool_id", matched_tool_id),
                status=data.get("status", "completed"),
                result=data.get("result"),
                error=data.get("error"),
                execution_time_ms=data.get("execution_time_ms"),
                upstream_status=data.get("upstream_status"),
            )
        else:
            # Error response - still return 200 with error details in body
            # This allows the Host App to see what went wrong
            error_data = result.data or {}
            errors = getattr(result, "errors", None) or []
            return ToolCallResponse(
                tool_id=matched_tool_id,
                status="failed",
                result=None,
                error=error_data.get("error") or {"message": errors[0] if errors else "Unknown error"},
                execution_time_ms=error_data.get("execution_time_ms", 0),
                upstream_status=error_data.get("upstream_status"),
            )

    def _tool_to_dict(self, tool: ToolManifestEntry) -> dict[str, Any]:
        """Convert ToolManifestEntry to dict for JSON serialization."""
        return {
            "tool_id": tool.tool_id,
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.input_schema,
            "source_id": tool.source_id,
            "source_path": tool.source_path,
            "tags": tool.tags,
            "version": tool.version,
        }

    def _get_redis_cache(self):
        """Get Redis cache service from DI container if available."""
        try:
            from infrastructure.cache import RedisCacheService

            return self.service_provider.get_service(RedisCacheService)
        except Exception:
            return None
