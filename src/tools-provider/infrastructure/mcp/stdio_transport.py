"""StdioTransport - MCP transport using subprocess with stdin/stdout.

This transport spawns an MCP server as a subprocess and communicates
using JSON-RPC messages over stdin/stdout pipes.

This is the most common transport for local MCP plugins like uvx-based
or npx-based MCP servers.
"""

import asyncio
import json
import logging
import os
from typing import Any

from .models import (
    McpRequest,
    McpResponse,
    McpServerInfo,
    McpToolDefinition,
    McpToolResult,
)
from .transport import (
    IMcpTransport,
    McpConnectionError,
    McpProtocolError,
    McpTimeoutError,
)

logger = logging.getLogger(__name__)

# Default timeout for MCP operations
DEFAULT_TIMEOUT = 30.0  # seconds
DEFAULT_INIT_TIMEOUT = 10.0  # seconds for initialization

# MCP protocol version we support
PROTOCOL_VERSION = "2024-11-05"


class StdioTransport(IMcpTransport):
    """MCP transport using subprocess with stdin/stdout communication.

    Spawns an MCP server as a child process and communicates using
    JSON-RPC 2.0 messages over stdin (requests) and stdout (responses).

    The transport manages the subprocess lifecycle:
    - connect(): Spawns process and performs MCP initialization
    - disconnect(): Terminates process and cleans up

    Attributes:
        command: Command and arguments to spawn the MCP server
        environment: Environment variables to pass to the subprocess
        cwd: Working directory for the subprocess
        timeout: Default timeout for operations (seconds)
    """

    def __init__(
        self,
        command: list[str],
        environment: dict[str, str] | None = None,
        cwd: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        """Initialize the StdioTransport.

        Args:
            command: Command and arguments to spawn the MCP server
                     (e.g., ["uvx", "cml-mcp"])
            environment: Additional environment variables to set.
                        These are merged with the current process environment.
            cwd: Working directory for the subprocess.
                 Defaults to current directory.
            timeout: Default timeout for operations in seconds.
        """
        if not command:
            raise ValueError("Command cannot be empty")

        self._command = command
        self._environment = environment or {}
        self._cwd = cwd
        self._timeout = timeout

        # Runtime state
        self._process: asyncio.subprocess.Process | None = None
        self._request_id = 0
        self._server_info: McpServerInfo | None = None
        self._stderr_task: asyncio.Task[None] | None = None

    async def connect(self) -> McpServerInfo:
        """Spawn subprocess and perform MCP initialization handshake.

        Returns:
            McpServerInfo with server details

        Raises:
            McpConnectionError: If subprocess cannot be started
            McpProtocolError: If initialization handshake fails
            McpTimeoutError: If server does not respond in time
        """
        if self._process is not None:
            raise McpConnectionError("Transport already connected")

        # Build environment: current env + custom env
        env = {**os.environ, **self._environment}

        try:
            logger.debug(f"Spawning MCP server: {' '.join(self._command)}")
            self._process = await asyncio.create_subprocess_exec(
                *self._command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=self._cwd,
            )
        except FileNotFoundError as e:
            raise McpConnectionError(f"MCP server command not found: {self._command[0]}", e) from e
        except OSError as e:
            raise McpConnectionError(f"Failed to spawn MCP server: {e}", e) from e

        # Start stderr reader task (logs server errors)
        self._stderr_task = asyncio.create_task(self._read_stderr())

        # Perform MCP initialization handshake
        try:
            self._server_info = await self._initialize()
            logger.info(f"MCP transport connected to {self._server_info.name} v{self._server_info.version}")
            return self._server_info
        except Exception:
            # Clean up on initialization failure
            await self.disconnect()
            raise

    async def _initialize(self) -> McpServerInfo:
        """Perform MCP initialization handshake.

        1. Send 'initialize' request with client capabilities
        2. Receive server capabilities and info
        3. Send 'initialized' notification

        Returns:
            McpServerInfo from server response

        Raises:
            McpProtocolError: If handshake fails
            McpTimeoutError: If server does not respond
        """
        # Send initialize request
        init_response = await self._send_request(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {
                    "tools": {},  # We support tool calls
                },
                "clientInfo": {
                    "name": "tools-provider",
                    "version": "1.0.0",
                },
            },
            timeout=DEFAULT_INIT_TIMEOUT,
        )

        server_info = McpServerInfo.from_dict(init_response)

        # Send initialized notification (no response expected)
        await self._send_notification("notifications/initialized", {})

        return server_info

    async def disconnect(self) -> None:
        """Terminate subprocess and clean up resources.

        This method is idempotent - safe to call multiple times.
        """
        if self._stderr_task:
            self._stderr_task.cancel()
            try:
                await self._stderr_task
            except asyncio.CancelledError:
                pass
            self._stderr_task = None

        if self._process:
            try:
                # Try graceful shutdown first
                self._process.terminate()
                try:
                    await asyncio.wait_for(self._process.wait(), timeout=2.0)
                except TimeoutError:
                    # Force kill if graceful shutdown fails
                    self._process.kill()
                    await self._process.wait()
            except ProcessLookupError:
                # Process already exited
                pass
            finally:
                self._process = None
                self._server_info = None
                logger.debug("MCP transport disconnected")

    async def list_tools(self) -> list[McpToolDefinition]:
        """Get available tools from the MCP server.

        Returns:
            List of tool definitions

        Raises:
            McpConnectionError: If not connected
            McpProtocolError: If response cannot be parsed
        """
        self._ensure_connected()

        response = await self._send_request("tools/list", {})
        tools_data = response.get("tools", [])

        return [McpToolDefinition.from_dict(tool) for tool in tools_data]

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
            McpToolResult with content and status

        Raises:
            McpConnectionError: If not connected
            McpProtocolError: If tool execution fails
            McpTimeoutError: If tool does not respond in time
        """
        self._ensure_connected()

        response = await self._send_request(
            "tools/call",
            {
                "name": tool_name,
                "arguments": arguments,
            },
            timeout=timeout or self._timeout,
        )

        return McpToolResult.from_dict(response)

    @property
    def is_connected(self) -> bool:
        """Check if transport is connected and subprocess is running."""
        return self._process is not None and self._process.returncode is None

    @property
    def server_info(self) -> McpServerInfo | None:
        """Get server info from initialization."""
        return self._server_info

    def _ensure_connected(self) -> None:
        """Raise error if not connected."""
        if not self.is_connected:
            raise McpConnectionError("Transport not connected")

    async def _send_request(
        self,
        method: str,
        params: dict[str, Any],
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """Send a JSON-RPC request and wait for response.

        Args:
            method: RPC method name
            params: Method parameters
            timeout: Timeout in seconds

        Returns:
            Response result dictionary

        Raises:
            McpProtocolError: If response contains an error
            McpTimeoutError: If no response within timeout
        """
        if not self._process or not self._process.stdin or not self._process.stdout:
            raise McpConnectionError("Transport not connected")

        self._request_id += 1
        request = McpRequest(id=self._request_id, method=method, params=params)

        # Send request
        request_line = json.dumps(request.to_dict()) + "\n"
        logger.debug(f"MCP request: {method} (id={self._request_id})")

        try:
            self._process.stdin.write(request_line.encode("utf-8"))
            await self._process.stdin.drain()
        except (BrokenPipeError, ConnectionResetError) as e:
            raise McpConnectionError("MCP server connection lost", e) from e

        # Read response
        effective_timeout = timeout or self._timeout
        try:
            response_line = await asyncio.wait_for(
                self._process.stdout.readline(),
                timeout=effective_timeout,
            )
        except TimeoutError:
            raise McpTimeoutError(f"MCP server did not respond within {effective_timeout}s")

        if not response_line:
            # Check if process died
            if self._process.returncode is not None:
                raise McpConnectionError(f"MCP server exited with code {self._process.returncode}")
            raise McpConnectionError("MCP server closed connection unexpectedly")

        # Parse response
        try:
            response_data = json.loads(response_line.decode("utf-8"))
        except json.JSONDecodeError as e:
            raise McpProtocolError(f"Invalid JSON response: {response_line[:100]}", e) from e

        response = McpResponse.from_dict(response_data)

        # Check for error response
        if response.error:
            raise McpProtocolError(f"MCP error ({response.error.code}): {response.error.message}")

        logger.debug(f"MCP response received for id={response.id}")
        return response.result or {}

    async def _send_notification(self, method: str, params: dict[str, Any]) -> None:
        """Send a JSON-RPC notification (no response expected).

        Args:
            method: Notification method name
            params: Notification parameters
        """
        if not self._process or not self._process.stdin:
            raise McpConnectionError("Transport not connected")

        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }

        notification_line = json.dumps(notification) + "\n"
        logger.debug(f"MCP notification: {method}")

        try:
            self._process.stdin.write(notification_line.encode("utf-8"))
            await self._process.stdin.drain()
        except (BrokenPipeError, ConnectionResetError) as e:
            raise McpConnectionError("MCP server connection lost", e) from e

    async def _read_stderr(self) -> None:
        """Background task to read and log stderr from subprocess."""
        if not self._process or not self._process.stderr:
            return

        try:
            while True:
                line = await self._process.stderr.readline()
                if not line:
                    break
                logger.warning(f"MCP stderr: {line.decode('utf-8').rstrip()}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug(f"Error reading MCP stderr: {e}")

    def __repr__(self) -> str:
        """String representation."""
        status = "connected" if self.is_connected else "disconnected"
        cmd = " ".join(self._command)
        return f"<StdioTransport({cmd}) [{status}]>"
