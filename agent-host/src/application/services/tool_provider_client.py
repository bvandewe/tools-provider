"""Tools Provider client for fetching tools and executing tool calls."""

import logging
import time
from typing import Any, Optional

import httpx
from neuroglia.hosting.abstractions import ApplicationBuilderBase
from opentelemetry import trace

from application.settings import Settings
from observability import tool_execution_count, tool_execution_errors, tool_execution_time, tools_fetched

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class ToolProviderClient:
    """
    HTTP client for communicating with the Tools Provider BFF API.

    Handles:
    - Fetching available tools
    - Executing tool calls with user tokens
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
    ) -> None:
        """
        Initialize the Tools Provider client.

        Args:
            base_url: Base URL of the Tools Provider (e.g., http://app:8080)
            timeout: HTTP timeout in seconds
        """
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def get_tools(self, access_token: str) -> list[dict[str, Any]]:
        """
        Fetch available tools from the Tools Provider.

        Args:
            access_token: User's access token for authentication

        Returns:
            List of tool definitions from the BFF API
        """
        client = await self._get_client()

        with tracer.start_as_current_span("tools_provider.get_tools") as span:
            try:
                response = await client.get(
                    "/api/agent/tools",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                response.raise_for_status()

                data = response.json()
                tools = data.get("data", data) if isinstance(data, dict) else data

                # Record metrics
                tools_fetched.add(1, {"tool_count": str(len(tools))})
                span.set_attribute("tools.count", len(tools))

                logger.debug(f"Fetched {len(tools)} tools from Tools Provider")

                # Debug: log first tool's structure to verify input_schema
                if tools and len(tools) > 0:
                    first_tool = tools[0]
                    logger.debug(f"First tool structure: name={first_tool.get('name')}")
                    logger.debug(f"First tool keys: {list(first_tool.keys())}")
                    input_schema = first_tool.get("input_schema") or first_tool.get("inputSchema")
                    logger.debug(f"First tool input_schema: {input_schema}")

                return tools
            except httpx.HTTPStatusError as e:
                span.set_attribute("error", True)
                span.set_attribute("error.message", str(e))
                logger.error(f"HTTP error fetching tools: {e.response.status_code} - {e.response.text}")
                raise
            except httpx.RequestError as e:
                span.set_attribute("error", True)
                span.set_attribute("error.message", str(e))
                logger.error(f"Request error fetching tools: {e}")
                raise

    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        access_token: str,
    ) -> dict[str, Any]:
        """
        Execute a tool via the Tools Provider BFF API.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments
            access_token: User's access token for authentication

        Returns:
            Tool execution result
        """
        client = await self._get_client()
        start_time = time.time()

        with tracer.start_as_current_span("tools_provider.execute_tool") as span:
            span.set_attribute("tool.name", tool_name)
            span.set_attribute("tool.argument_count", len(arguments))

            try:
                response = await client.post(
                    "/api/agent/tools/call",
                    json={
                        "name": tool_name,
                        "arguments": arguments,
                    },
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                response.raise_for_status()

                result = response.json()

                # Record metrics
                duration_ms = (time.time() - start_time) * 1000
                tool_execution_count.add(1, {"tool_name": tool_name, "success": "true"})
                tool_execution_time.record(duration_ms, {"tool_name": tool_name})
                span.set_attribute("tool.duration_ms", duration_ms)
                span.set_attribute("tool.success", True)

                logger.info(f"Executed tool '{tool_name}' successfully in {duration_ms:.2f}ms")
                return result

            except httpx.HTTPStatusError as e:
                duration_ms = (time.time() - start_time) * 1000
                tool_execution_count.add(1, {"tool_name": tool_name, "success": "false"})
                tool_execution_errors.add(1, {"tool_name": tool_name, "error_type": "http"})
                span.set_attribute("error", True)
                span.set_attribute("error.message", str(e))

                logger.error(f"HTTP error executing tool '{tool_name}': {e.response.status_code} - {e.response.text}")
                return {
                    "success": False,
                    "error": f"Tool execution failed: {e.response.status_code}",
                    "details": e.response.text,
                }
            except httpx.RequestError as e:
                duration_ms = (time.time() - start_time) * 1000
                tool_execution_count.add(1, {"tool_name": tool_name, "success": "false"})
                tool_execution_errors.add(1, {"tool_name": tool_name, "error_type": "request"})
                span.set_attribute("error", True)
                span.set_attribute("error.message", str(e))

                logger.error(f"Request error executing tool '{tool_name}': {e}")
                return {
                    "success": False,
                    "error": f"Request failed: {str(e)}",
                }

    async def get_tool_source_info(
        self,
        tool_name: str,
        access_token: str,
    ) -> dict[str, Any]:
        """
        Get source information for a tool from the Tools Provider.

        Args:
            tool_name: Name of the tool (format: source_id:operation_id)
            access_token: User's access token for authentication

        Returns:
            Source information for the tool
        """
        client = await self._get_client()

        with tracer.start_as_current_span("tools_provider.get_tool_source_info") as span:
            span.set_attribute("tool.name", tool_name)

            try:
                # URL-encode the tool name since it contains colons
                encoded_tool_name = tool_name.replace(":", "%3A")
                response = await client.get(
                    f"/api/tools/{encoded_tool_name}/source",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                response.raise_for_status()

                result = response.json()
                span.set_attribute("source.name", result.get("source_name", ""))
                logger.debug(f"Fetched source info for tool '{tool_name}': {result.get('source_name')}")
                return result

            except httpx.HTTPStatusError as e:
                span.set_attribute("error", True)
                span.set_attribute("error.message", str(e))
                logger.error(f"HTTP error fetching tool source info: {e.response.status_code} - {e.response.text}")
                raise
            except httpx.RequestError as e:
                span.set_attribute("error", True)
                span.set_attribute("error.message", str(e))
                logger.error(f"Request error fetching tool source info: {e}")
                raise

    @staticmethod
    def configure(builder: ApplicationBuilderBase) -> None:
        """
        Configure ToolProviderClient in the service collection.

        Follows Neuroglia framework pattern for service registration.

        Args:
            builder: The application builder
        """
        # Get settings from builder
        settings: Settings = next(
            (d.singleton for d in builder.services if d.service_type is Settings),
            None,
        )

        if settings is None:
            logger.warning("Settings not found in services, using defaults")
            settings = Settings()

        # Create and register singleton instance
        client = ToolProviderClient(
            base_url=settings.tools_provider_url,
            timeout=settings.tools_provider_timeout,
        )

        builder.services.add_singleton(ToolProviderClient, singleton=client)
        logger.info(f"Configured ToolProviderClient with base_url={settings.tools_provider_url}")
