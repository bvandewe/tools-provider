"""Source DTO for read model queries.

This is the queryable representation of an UpstreamSource,
optimized for read operations from MongoDB.
"""

import datetime
from dataclasses import dataclass
from typing import Optional

from neuroglia.data.abstractions import Identifiable, queryable

from domain.enums import HealthStatus, SourceType


@queryable
@dataclass
class SourceDto(Identifiable[str]):
    """Read model DTO for UpstreamSource aggregate.

    Contains denormalized fields for efficient querying.
    """

    id: str
    name: str
    url: str  # Service base URL
    source_type: SourceType
    health_status: HealthStatus
    is_enabled: bool
    inventory_count: int = 0
    inventory_hash: str = ""
    last_sync_at: Optional[datetime.datetime] = None
    last_sync_error: Optional[str] = None
    consecutive_failures: int = 0
    created_at: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None
    created_by: Optional[str] = None
    default_audience: Optional[str] = None  # Target audience for token exchange
    openapi_url: Optional[str] = None  # URL to the OpenAPI specification (separate from base URL)
    description: Optional[str] = None  # Human-readable description of the source
