"""AccessPolicy DTO for the Read Model.

This DTO is persisted in MongoDB and projected from domain events.
It supports efficient queries for access policy listing and evaluation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from neuroglia.data.abstractions import Identifiable, queryable


@queryable
@dataclass
class AccessPolicyDto(Identifiable[str]):
    """Read model DTO for AccessPolicy aggregate.

    Optimized for queries:
    - Filter by is_active for active policies
    - Sort by priority for evaluation order
    - Full claim_matchers for access resolution

    Note: This DTO stores the serialized forms of ClaimMatchers
    for MongoDB compatibility. The AccessResolver service handles
    the actual claim evaluation.
    """

    id: str
    name: str
    description: Optional[str] = None

    # Serialized claim matchers for evaluation
    claim_matchers: List[Dict[str, Any]] = field(default_factory=list)

    # Allowed group IDs this policy grants access to
    allowed_group_ids: List[str] = field(default_factory=list)

    # Evaluation control
    priority: int = 0
    is_active: bool = True

    # Audit trail
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None

    # Derived counts for display
    matcher_count: int = 0
    group_count: int = 0


@queryable
@dataclass
class AccessPolicySummaryDto(Identifiable[str]):
    """Lightweight DTO for access policy listing (without full details).

    Used in API responses where full matchers/groups are not needed.
    """

    id: str
    name: str
    description: Optional[str] = None
    priority: int = 0
    is_active: bool = True
    matcher_count: int = 0
    group_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
