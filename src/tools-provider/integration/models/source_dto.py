"""Source DTO for read model queries.

This is the queryable representation of an UpstreamSource,
optimized for read operations from MongoDB.
"""

import datetime
from dataclasses import dataclass
from typing import Any

from neuroglia.data.abstractions import Identifiable, queryable

from domain.enums import AuthMode, HealthStatus, SourceType


@queryable
@dataclass
class SourceDto(Identifiable[str]):
    """Read model DTO for UpstreamSource aggregate.

    Contains denormalized fields for efficient querying.
    Note: auth_config credentials are NOT stored here - they are loaded
    from a separate secrets file (infrastructure/secrets/source_secrets_store.py).
    """

    id: str
    name: str
    url: str  # Service base URL
    source_type: SourceType
    health_status: HealthStatus
    is_enabled: bool
    inventory_count: int = 0
    inventory_hash: str = ""
    last_sync_at: datetime.datetime | None = None
    last_sync_error: str | None = None
    consecutive_failures: int = 0
    created_at: datetime.datetime | None = None
    updated_at: datetime.datetime | None = None
    created_by: str | None = None
    default_audience: str | None = None  # Target audience for token exchange
    openapi_url: str | None = None  # URL to the OpenAPI specification (separate from base URL)
    description: str | None = None  # Human-readable description of the source
    auth_mode: AuthMode = AuthMode.TOKEN_EXCHANGE  # Authentication mode for tool execution
    required_scopes: list[str] | None = None  # Scopes required for all tools from this source
    mcp_config: dict[str, Any] | None = None  # MCP configuration (for MCP sources only)
