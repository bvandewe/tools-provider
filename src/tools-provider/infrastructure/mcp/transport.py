"""MCP transport interface.

Defines the abstract base class for all MCP transport implementations.
Transports handle the low-level communication with MCP servers.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .models import McpServerInfo, McpToolDefinition, McpToolResult


class McpTransportError(Exception):
    """Base exception for MCP transport errors.

    Raised when transport-level operations fail (connection, send, receive).
    """

    def __init__(self, message: str, cause: Exception | None = None):
        super().__init__(message)
        self.cause = cause


class McpConnectionError(McpTransportError):
    """Error establishing or maintaining connection to MCP server."""

    pass


class McpProtocolError(McpTransportError):
    """Error in MCP protocol communication (invalid messages, etc.)."""

    pass


class McpTimeoutError(McpTransportError):
    """Timeout waiting for MCP server response."""

    pass


class IMcpTransport(ABC):
    """Abstract base class for MCP transport implementations.

    A transport handles the communication channel with an MCP server,
    managing connection lifecycle and message exchange.

    Implementations:
        - StdioTransport: Subprocess with stdin/stdout communication
        - SseTransport: Server-Sent Events over HTTP (future)

    Usage:
        transport = StdioTransport(command=["uvx", "my-mcp-server"], environment={})
        await transport.connect()
        try:
            tools = await transport.list_tools()
            result = await transport.call_tool("my_tool", {"arg": "value"})
        finally:
            await transport.disconnect()

    Thread Safety:
        Transport instances are NOT thread-safe. Use one transport per
        concurrent execution context.
    """

    @abstractmethod
    async def connect(self) -> "McpServerInfo":
        """Establish connection to the MCP server.

        Performs the MCP initialization handshake:
        1. Starts the transport channel (subprocess, HTTP connection, etc.)
        2. Sends the 'initialize' request with client capabilities
        3. Receives server info and capabilities
        4. Sends 'initialized' notification

        Returns:
            McpServerInfo with server name, version, and protocol version

        Raises:
            McpConnectionError: If connection cannot be established
            McpProtocolError: If initialization handshake fails
            McpTimeoutError: If server does not respond in time
        """
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Close the connection to the MCP server.

        Performs graceful shutdown:
        1. Sends any pending messages
        2. Closes the transport channel
        3. Cleans up resources (subprocess, connections)

        This method should be idempotent - safe to call multiple times.
        """
        ...

    @abstractmethod
    async def list_tools(self) -> list["McpToolDefinition"]:
        """Discover available tools from the MCP server.

        Sends 'tools/list' request and parses the response.

        Returns:
            List of tool definitions with name, description, and input schema

        Raises:
            McpConnectionError: If not connected
            McpProtocolError: If response cannot be parsed
            McpTimeoutError: If server does not respond in time
        """
        ...

    @abstractmethod
    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        timeout: float | None = None,
    ) -> "McpToolResult":
        """Execute a tool call on the MCP server.

        Sends 'tools/call' request and waits for the result.

        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool
            timeout: Optional timeout in seconds (overrides default)

        Returns:
            McpToolResult with content and error status

        Raises:
            McpConnectionError: If not connected
            McpProtocolError: If tool execution fails at protocol level
            McpTimeoutError: If tool does not respond in time
        """
        ...

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if the transport is currently connected.

        Returns:
            True if connected and ready to send/receive messages
        """
        ...

    @property
    @abstractmethod
    def server_info(self) -> "McpServerInfo | None":
        """Get information about the connected server.

        Returns:
            Server info if connected, None otherwise
        """
        ...

    async def __aenter__(self) -> "IMcpTransport":
        """Async context manager entry - connects to server."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit - disconnects from server."""
        await self.disconnect()
