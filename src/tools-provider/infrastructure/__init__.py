"""Infrastructure layer for cross-cutting concerns."""

from .adapters import KeycloakTokenExchanger, TokenExchangeError, TokenExchangeResult
from .cache import RedisCacheService
from .mcp import (
    IMcpTransport,
    McpContent,
    McpEnvironmentResolver,
    McpError,
    McpNotification,
    McpRequest,
    McpResponse,
    McpToolCall,
    McpToolResult,
    McpTransportError,
    StdioTransport,
    TransportFactory,
)
from .secrets import SourceSecretsStore
from .services import CircuitBreakerEventPublisher
from .session_store import InMemorySessionStore, RedisSessionStore, SessionStore

__all__ = [
    # Session management
    "SessionStore",
    "InMemorySessionStore",
    "RedisSessionStore",
    # Caching
    "RedisCacheService",
    # Authentication
    "KeycloakTokenExchanger",
    "TokenExchangeResult",
    "TokenExchangeError",
    # Event publishing
    "CircuitBreakerEventPublisher",
    # Secrets
    "SourceSecretsStore",
    # MCP Transport Layer
    "IMcpTransport",
    "McpTransportError",
    "StdioTransport",
    "TransportFactory",
    "McpEnvironmentResolver",
    # MCP Protocol Models
    "McpRequest",
    "McpResponse",
    "McpNotification",
    "McpError",
    "McpToolCall",
    "McpToolResult",
    "McpContent",
]
