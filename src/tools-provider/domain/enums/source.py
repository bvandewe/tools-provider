"""Source and Tool related enumerations.

These enums support the MCP Tools Provider domain for managing
upstream sources, tool discovery, and access policies.
"""

from enum import Enum


class SourceType(str, Enum):
    """Type of upstream source providing tools."""

    OPENAPI = "openapi"  # OpenAPI 3.x specification
    WORKFLOW = "workflow"  # Workflow engine (Temporal, n8n, etc.)


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
