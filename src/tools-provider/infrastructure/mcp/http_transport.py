"""MCP HTTP Transport for remote MCP servers.

Implements the Streamable HTTP transport for connecting to remote MCP servers
that expose their API over HTTP (e.g., MCP servers running in containers).
"""

import logging
from typing import Any

import httpx

from .models import McpContent, McpServerInfo, McpToolDefinition, McpToolResult
from .transport import IMcpTransport, McpConnectionError, McpProtocolError, McpTimeoutError

logger = logging.getLogger(__name__)


class HttpTransport(IMcpTransport):
    """HTTP transport for remote MCP servers.

    Connects to MCP servers that expose their API over HTTP, typically
    running in containers or as standalone services.

    The transport uses JSON-RPC over HTTP POST requests for communication.
    Server-Sent Events (SSE) can optionally be used for streaming responses.

    Example server URL: http://cml-mcp:9000

    Endpoints used:
        - POST /mcp (or /): JSON-RPC endpoint for all MCP operations
        - GET /health: Health check endpoint (optional)

    Usage:
        transport = HttpTransport(
            server_url="http://cml-mcp:9000",
            timeout=30.0,
        )
        await transport.connect()
        tools = await transport.list_tools()
        result = await transport.call_tool("my_tool", {"arg": "value"})
        await transport.disconnect()
    """

    MCP_PROTOCOL_VERSION = "2024-11-05"  # MCP protocol version

    def __init__(
        self,
        server_url: str,
        timeout: float = 30.0,
        headers: dict[str, str] | None = None,
    ):
        """Initialize HTTP transport.

        Args:
            server_url: Base URL of the MCP server (e.g., http://localhost:9000)
            timeout: Request timeout in seconds
            headers: Optional additional HTTP headers (e.g., for authentication)
        """
        self._server_url = server_url.rstrip("/")
        self._timeout = timeout
        self._headers = headers or {}
        self._client: httpx.AsyncClient | None = None
        self._server_info: McpServerInfo | None = None
        self._is_connected = False
        self._request_id = 0

    def _next_request_id(self) -> int:
        """Generate the next JSON-RPC request ID."""
        self._request_id += 1
        return self._request_id

    def _build_jsonrpc_request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Build a JSON-RPC 2.0 request object."""
        request = {
            "jsonrpc": "2.0",
            "id": self._next_request_id(),
            "method": method,
        }
        if params is not None:
            request["params"] = params
        return request

    async def _send_request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Send a JSON-RPC request and return the result.

        Args:
            method: JSON-RPC method name
            params: Optional method parameters

        Returns:
            The 'result' field from the JSON-RPC response

        Raises:
            McpConnectionError: If not connected or connection fails
            McpProtocolError: If response contains an error
            McpTimeoutError: If request times out
        """
        if not self._client or not self._is_connected:
            raise McpConnectionError("Not connected to MCP server")

        request = self._build_jsonrpc_request(method, params)
        logger.debug(f"Sending MCP request: {method}")

        try:
            response = await self._client.post(
                f"{self._server_url}/mcp",
                json=request,
                timeout=self._timeout,
            )
            response.raise_for_status()

            # Handle both plain JSON and SSE-formatted responses
            content_type = response.headers.get("content-type", "")
            response_text = response.text

            if "text/event-stream" in content_type or response_text.startswith("event:"):
                # Parse SSE format: extract JSON from "data: {...}" lines
                data = self._parse_sse_response(response_text)
            else:
                # Plain JSON response
                data = response.json()

            if "error" in data:
                error = data["error"]
                raise McpProtocolError(f"MCP error {error.get('code', 'unknown')}: {error.get('message', 'Unknown error')}")

            return data.get("result", {})

        except httpx.TimeoutException as e:
            raise McpTimeoutError(f"Request timed out after {self._timeout}s", e) from e
        except httpx.HTTPStatusError as e:
            raise McpProtocolError(f"HTTP error {e.response.status_code}: {e.response.text}", e) from e
        except httpx.RequestError as e:
            raise McpConnectionError(f"Connection error: {e}", e) from e

    def _parse_sse_response(self, text: str) -> dict[str, Any]:
        """Parse Server-Sent Events format to extract JSON data.

        SSE format:
            event: message
            data: {"jsonrpc": "2.0", ...}

        Args:
            text: Raw SSE response text

        Returns:
            Parsed JSON data from the SSE response

        Raises:
            McpProtocolError: If SSE format is invalid or JSON parsing fails
        """
        import json

        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("data:"):
                json_str = line[5:].strip()
                if json_str:
                    try:
                        return json.loads(json_str)
                    except json.JSONDecodeError as e:
                        raise McpProtocolError(f"Failed to parse SSE JSON data: {e}") from e

        raise McpProtocolError(f"No data found in SSE response: {text[:200]}")

    async def connect(self) -> McpServerInfo:
        """Establish connection to the MCP server.

        Performs HTTP-based MCP initialization:
        1. Creates HTTP client
        2. Sends 'initialize' request
        3. Sends 'initialized' notification
        4. Optionally checks /health endpoint

        Returns:
            McpServerInfo with server details

        Raises:
            McpConnectionError: If connection fails
            McpProtocolError: If initialization fails
        """
        if self._is_connected and self._server_info is not None:
            return self._server_info

        logger.info(f"Connecting to remote MCP server: {self._server_url}")

        # Create HTTP client
        self._client = httpx.AsyncClient(
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                **self._headers,
            },
            timeout=self._timeout,
        )

        try:
            # Check health endpoint first (optional)
            try:
                health_response = await self._client.get(
                    f"{self._server_url}/health",
                    timeout=5.0,
                )
                if health_response.status_code != 200:
                    logger.warning(f"Health check returned {health_response.status_code}")
            except Exception as e:
                logger.debug(f"Health endpoint not available: {e}")

            # Mark as connected to allow _send_request
            self._is_connected = True

            # Send initialize request
            init_result = await self._send_request(
                "initialize",
                {
                    "protocolVersion": self.MCP_PROTOCOL_VERSION,
                    "capabilities": {
                        "tools": {},
                    },
                    "clientInfo": {
                        "name": "tools-provider",
                        "version": "1.0.0",
                    },
                },
            )

            # Parse server info
            server_info_data = init_result.get("serverInfo", {})
            self._server_info = McpServerInfo(
                name=server_info_data.get("name", "Unknown"),
                version=server_info_data.get("version", "0.0.0"),
                protocol_version=init_result.get("protocolVersion", self.MCP_PROTOCOL_VERSION),
            )

            # Send initialized notification (no response expected)
            try:
                await self._client.post(
                    f"{self._server_url}/mcp",
                    json={
                        "jsonrpc": "2.0",
                        "method": "notifications/initialized",
                    },
                    timeout=5.0,
                )
            except Exception as e:
                logger.debug(f"Initialized notification failed (may be expected): {e}")

            logger.info(f"Connected to MCP server: {self._server_info.name} v{self._server_info.version}")
            return self._server_info

        except Exception as e:
            self._is_connected = False
            await self.disconnect()
            if isinstance(e, McpConnectionError | McpProtocolError | McpTimeoutError):
                raise
            raise McpConnectionError(f"Failed to connect to MCP server: {e}", e) from e

    async def disconnect(self) -> None:
        """Close the HTTP connection."""
        self._is_connected = False
        self._server_info = None
        if self._client:
            await self._client.aclose()
            self._client = None
        logger.debug(f"Disconnected from MCP server: {self._server_url}")

    async def list_tools(self) -> list[McpToolDefinition]:
        """Discover available tools from the MCP server.

        Returns:
            List of tool definitions

        Raises:
            McpConnectionError: If not connected
            McpProtocolError: If request fails
        """
        result = await self._send_request("tools/list")
        tools = result.get("tools", [])

        return [
            McpToolDefinition(
                name=tool.get("name", ""),
                description=tool.get("description", ""),
                input_schema=tool.get("inputSchema", {}),
            )
            for tool in tools
        ]

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        timeout: float | None = None,
    ) -> McpToolResult:
        """Execute a tool call on the MCP server.

        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool
            timeout: Optional timeout override

        Returns:
            McpToolResult with content

        Raises:
            McpConnectionError: If not connected
            McpProtocolError: If tool execution fails
            McpTimeoutError: If tool times out
        """
        if not self._client or not self._is_connected:
            raise McpConnectionError("Not connected to MCP server")

        request = self._build_jsonrpc_request(
            "tools/call",
            {
                "name": tool_name,
                "arguments": arguments,
            },
        )

        effective_timeout = timeout or self._timeout
        logger.debug(f"Calling remote tool '{tool_name}' with timeout {effective_timeout}s")

        try:
            response = await self._client.post(
                f"{self._server_url}/mcp",
                json=request,
                timeout=effective_timeout,
            )
            response.raise_for_status()

            # Handle both plain JSON and SSE-formatted responses
            content_type = response.headers.get("content-type", "")
            response_text = response.text

            if "text/event-stream" in content_type or response_text.startswith("event:"):
                # Parse SSE format: extract JSON from "data: {...}" lines
                data = self._parse_sse_response(response_text)
            else:
                # Plain JSON response
                data = response.json()

            if "error" in data:
                error = data["error"]
                # Tool errors are returned as content, not as JSON-RPC errors
                # unless it's a protocol-level error
                if error.get("code", 0) < -32000:  # JSON-RPC reserved error codes
                    raise McpProtocolError(f"MCP error {error.get('code')}: {error.get('message', 'Unknown error')}")

            result = data.get("result", {})
            content_items = result.get("content", [])
            is_error = result.get("isError", False)

            content = [
                McpContent(
                    type=item.get("type", "text"),
                    text=item.get("text"),
                    data=item.get("data"),
                    mime_type=item.get("mimeType"),
                )
                for item in content_items
            ]

            return McpToolResult(
                content=content,
                is_error=is_error,
            )

        except httpx.TimeoutException as e:
            raise McpTimeoutError(f"Tool execution timed out after {effective_timeout}s", e) from e
        except httpx.HTTPStatusError as e:
            raise McpProtocolError(f"HTTP error {e.response.status_code}: {e.response.text}", e) from e
        except httpx.RequestError as e:
            raise McpConnectionError(f"Connection error during tool call: {e}", e) from e

    @property
    def is_connected(self) -> bool:
        """Check if connected to the MCP server."""
        return self._is_connected and self._client is not None

    @property
    def server_info(self) -> McpServerInfo | None:
        """Get server information."""
        return self._server_info

    @property
    def server_url(self) -> str:
        """Get the server URL."""
        return self._server_url
