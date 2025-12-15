"""MCP (Model Context Protocol) infrastructure layer.

This package provides the transport layer for communicating with MCP
plugin servers. It includes:

- Transport abstractions and implementations (stdio, HTTP, SSE)
- MCP protocol message models
- Environment variable resolution for plugins
- Transport lifecycle management
"""

from .env_resolver import McpEnvironmentResolver
from .http_transport import HttpTransport
from .models import (
    McpContent,
    McpError,
    McpNotification,
    McpRequest,
    McpResponse,
    McpToolCall,
    McpToolResult,
)
from .stdio_transport import StdioTransport
from .transport import IMcpTransport, McpConnectionError, McpProtocolError, McpTimeoutError, McpTransportError
from .transport_factory import TransportFactory

__all__ = [
    # Transport interface
    "IMcpTransport",
    "McpTransportError",
    "McpConnectionError",
    "McpProtocolError",
    "McpTimeoutError",
    # Transport implementations
    "StdioTransport",
    "HttpTransport",
    # Factory
    "TransportFactory",
    # Protocol models
    "McpRequest",
    "McpResponse",
    "McpNotification",
    "McpError",
    "McpToolCall",
    "McpToolResult",
    "McpContent",
    # Environment
    "McpEnvironmentResolver",
]
