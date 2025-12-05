"""ToolGroup DTO for the Read Model.

This DTO is persisted in MongoDB and projected from domain events.
It supports efficient queries for tool group listing and filtering.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from neuroglia.data.abstractions import Identifiable, queryable


@queryable
@dataclass
class ToolGroupDto(Identifiable[str]):
    """Read model representation of a ToolGroup.

    Optimized for queries:
    - Filter by is_active for active groups
    - Get selector_count and tool_count for display
    - Full selectors and memberships for resolution

    Note: This DTO stores the serialized forms of value objects
    for MongoDB compatibility. The CatalogProjector handles the
    actual tool resolution using selectors and explicit memberships.
    """

    id: str
    name: str
    description: str

    # Aggregated counts for display
    selector_count: int = 0
    explicit_tool_count: int = 0
    excluded_tool_count: int = 0

    # Serialized selectors and memberships
    selectors: List[Dict[str, Any]] = field(default_factory=list)
    explicit_tool_ids: List[Dict[str, Any]] = field(default_factory=list)
    excluded_tool_ids: List[Dict[str, Any]] = field(default_factory=list)

    # Lifecycle
    is_active: bool = True

    # Audit trail
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None


@queryable
@dataclass
class ToolGroupSummaryDto(Identifiable[str]):
    """Lightweight DTO for tool group listing (without full details).

    Used in API responses where full selectors/memberships are not needed.
    """

    id: str
    name: str
    description: str
    selector_count: int = 0
    explicit_tool_count: int = 0
    excluded_tool_count: int = 0
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@queryable
@dataclass
class ResolvedToolGroupDto(Identifiable[str]):
    """DTO with resolved tool list for a group.

    This is computed by the CatalogProjector and cached.
    Contains the final list of tool IDs after applying:
    1. Selector matching
    2. Explicit additions
    3. Exclusion removals

    Note: This may be cached in Redis for fast agent tool discovery.
    """

    id: str
    name: str
    description: str

    # Resolved tool IDs (final computed list)
    tool_ids: List[str] = field(default_factory=list)
    tool_count: int = 0

    # When this resolution was computed
    resolved_at: Optional[datetime] = None

    # Cache management
    is_stale: bool = False  # True if group changed since resolution
