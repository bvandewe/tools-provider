"""Label DTO for the Read Model.

This DTO is persisted in MongoDB and projected from domain events.
It provides efficient queries for label listing and management.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from neuroglia.data.abstractions import Identifiable, queryable


@queryable
@dataclass
class LabelDto(Identifiable[str]):
    """Read model representation of a Label.

    Optimized for queries:
    - List all labels for dropdown selections
    - Filter by color for visual grouping
    - Search by name
    """

    id: str  # Unique label identifier
    name: str  # Display name
    description: str  # Optional description
    color: str  # CSS color (hex or named)

    # Usage statistics (updated by projectors)
    tool_count: int = 0  # Number of tools with this label

    # Lifecycle
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    is_deleted: bool = False


@queryable
@dataclass
class LabelSummaryDto(Identifiable[str]):
    """Lightweight DTO for label selection dropdowns.

    Used in API responses where full details are not needed.
    """

    id: str
    name: str
    color: str
    tool_count: int = 0
