"""KnowledgeRevision value object.

Represents a snapshot of namespace state at a point in time for versioning.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class KnowledgeRevision:
    """Snapshot of namespace state at a point in time.

    Revisions enable:
    - Audit trail of changes
    - Rollback to previous state
    - Branching (future capability)

    This is a value object - immutable after creation.
    """

    revision_number: int
    """Sequential revision number."""

    message: str
    """Commit message describing the changes."""

    created_by: str
    """User ID who created this revision."""

    created_at: datetime = field(default_factory=datetime.now)
    """When the revision was created."""

    # Snapshot data (stored as dictionaries for flexibility)
    term_snapshot: dict[str, dict] = field(default_factory=dict)
    """term_id -> term data at time of revision."""

    relationship_snapshot: dict[str, dict] = field(default_factory=dict)
    """relationship_id -> relationship data at time of revision."""

    rule_snapshot: dict[str, dict] = field(default_factory=dict)
    """rule_id -> rule data at time of revision."""

    # Statistics at time of revision
    term_count: int = 0
    """Number of terms at time of revision."""

    relationship_count: int = 0
    """Number of relationships at time of revision."""

    rule_count: int = 0
    """Number of rules at time of revision."""

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "revision_number": self.revision_number,
            "message": self.message,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "term_snapshot": self.term_snapshot,
            "relationship_snapshot": self.relationship_snapshot,
            "rule_snapshot": self.rule_snapshot,
            "term_count": self.term_count,
            "relationship_count": self.relationship_count,
            "rule_count": self.rule_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "KnowledgeRevision":
        """Create from dictionary."""
        from datetime import datetime as dt

        created_at = data.get("created_at")

        return cls(
            revision_number=data["revision_number"],
            message=data["message"],
            created_by=data["created_by"],
            created_at=dt.fromisoformat(created_at) if isinstance(created_at, str) else created_at or dt.now(),
            term_snapshot=data.get("term_snapshot", {}),
            relationship_snapshot=data.get("relationship_snapshot", {}),
            rule_snapshot=data.get("rule_snapshot", {}),
            term_count=data.get("term_count", 0),
            relationship_count=data.get("relationship_count", 0),
            rule_count=data.get("rule_count", 0),
        )
