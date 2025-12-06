"""Tools Provider client for fetching tools and executing tool calls."""

import logging
from typing import Any, Optional

import httpx
from neuroglia.hosting.abstractions import ApplicationBuilderBase

from application.settings import Settings

logger = logging.getLogger(__name__)


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

        try:
            response = await client.get(
                "/api/bff/tools",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()

            data = response.json()
            tools = data.get("data", data) if isinstance(data, dict) else data

            logger.info(f"Fetched {len(tools)} tools from Tools Provider")
            return tools

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching tools: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
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

        try:
            response = await client.post(
                "/api/bff/tools/call",
                json={
                    "name": tool_name,
                    "arguments": arguments,
                },
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()

            result = response.json()
            logger.info(f"Executed tool '{tool_name}' successfully")
            return result

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error executing tool '{tool_name}': {e.response.status_code} - {e.response.text}")
            return {
                "success": False,
                "error": f"Tool execution failed: {e.response.status_code}",
                "details": e.response.text,
            }
        except httpx.RequestError as e:
            logger.error(f"Request error executing tool '{tool_name}': {e}")
            return {
                "success": False,
                "error": f"Request failed: {str(e)}",
            }

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
