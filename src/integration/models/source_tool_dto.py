"""SourceTool DTO for the Read Model.

This DTO is persisted in MongoDB and projected from domain events.
It supports efficient queries for tool listing and filtering.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from neuroglia.data.abstractions import Identifiable, queryable


@queryable
@dataclass
class SourceToolDto(Identifiable[str]):
    """Read model representation of a SourceTool.

    Optimized for queries:
    - Filter by source_id to list tools for a source
    - Filter by is_enabled for admin management
    - Filter by status for active vs deprecated tools
    - Search by name/tags for tool discovery
    """

    id: str  # tool_id: "{source_id}:{operation_id}"
    source_id: str
    source_name: str  # Denormalized for display
    tool_name: str
    operation_id: str
    description: str
    method: str  # HTTP method from execution profile
    path: str  # source_path from definition
    execution_mode: str  # "sync_http" or "async_poll"
    input_schema: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    required_audience: str = ""
    timeout_seconds: int = 30

    # Admin control
    is_enabled: bool = True
    status: str = "active"  # "active" or "deprecated"

    # Audit trail
    discovered_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    enabled_by: Optional[str] = None
    disabled_by: Optional[str] = None
    disable_reason: Optional[str] = None

    # Full definition (for tool execution)
    definition: Optional[Dict[str, Any]] = None  # Serialized ToolDefinition


@queryable
@dataclass
class SourceToolSummaryDto(Identifiable[str]):
    """Lightweight DTO for tool listing (without full definition).

    Used in API responses where full definition is not needed.
    """

    id: str
    source_id: str
    source_name: str
    tool_name: str
    description: str
    method: str
    path: str
    tags: List[str] = field(default_factory=list)
    is_enabled: bool = True
    status: str = "active"
    updated_at: Optional[datetime] = None
