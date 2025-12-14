"""Source and Tool related enumerations.

These enums support the MCP Tools Provider domain for managing
upstream sources, tool discovery, and access policies.
"""

from enum import Enum


class SourceType(str, Enum):
    """Type of upstream source providing tools."""

    OPENAPI = "openapi"  # OpenAPI 3.x specification
    WORKFLOW = "workflow"  # Workflow engine (Temporal, n8n, etc.)
    BUILTIN = "builtin"  # Built-in utility tools (fetch_url, etc.)


class HealthStatus(str, Enum):
    """Health status of an upstream source.

    Tracks the connectivity and sync status of external sources.
    """

    UNKNOWN = "unknown"  # Initial state, never synced
    HEALTHY = "healthy"  # Last sync successful
    DEGRADED = "degraded"  # Partial failures or slow responses
    UNHEALTHY = "unhealthy"  # Multiple consecutive failures


class ToolStatus(str, Enum):
    """Lifecycle status of a SourceTool.

    Tracks whether a discovered tool is still present in the upstream spec.
    """

    ACTIVE = "active"  # Tool exists in upstream spec
    DEPRECATED = "deprecated"  # Tool removed from upstream spec


class ExecutionMode(str, Enum):
    """How a tool is executed against the upstream service."""

    SYNC_HTTP = "sync_http"  # Synchronous HTTP request/response
    ASYNC_POLL = "async_poll"  # Async trigger with polling for result


class ClaimOperator(str, Enum):
    """Operators for JWT claim matching in access policies.

    Used by ClaimMatcher to evaluate access rules against JWT claims.
    """

    EQUALS = "equals"  # Exact string match
    CONTAINS = "contains"  # Array contains value
    MATCHES = "matches"  # Regex pattern match
    NOT_EQUALS = "not_equals"  # Negated exact match
    NOT_CONTAINS = "not_contains"  # Array does not contain value
    IN = "in"  # Value is in a list
    NOT_IN = "not_in"  # Value is not in a list
    EXISTS = "exists"  # Claim path exists (value ignored)


class AuthMode(str, Enum):
    """Authentication mode for upstream sources.

    Determines how the Tools Provider authenticates requests
    to upstream services when executing tools.

    - NONE: No authentication (public endpoints)
    - API_KEY: Static API key in header or query param
    - HTTP_BASIC: HTTP Basic authentication (RFC 7617)
    - CLIENT_CREDENTIALS: OAuth2 client credentials grant (service-to-service)
    - TOKEN_EXCHANGE: RFC 8693 token exchange for user identity delegation
    """

    NONE = "none"  # No authentication required
    API_KEY = "api_key"  # Static API key authentication  # pragma: allowlist secret
    HTTP_BASIC = "http_basic"  # HTTP Basic authentication (RFC 7617)  # pragma: allowlist secret
    CLIENT_CREDENTIALS = "client_credentials"  # OAuth2 client_credentials grant  # pragma: allowlist secret
    TOKEN_EXCHANGE = "token_exchange"  # RFC 8693 token exchange (default)  # nosec B105  # pragma: allowlist secret
