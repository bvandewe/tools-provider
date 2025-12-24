"""KnowledgeRelationship value object.

Represents a directed relationship between two terms in a namespace.
"""

from dataclasses import dataclass, field
from datetime import datetime

from domain.enums import RelationshipType


@dataclass
class KnowledgeRelationship:
    """Directed relationship between two terms.

    Relationship types:
    - contains: Parent contains child (ExamBlueprint contains ExamDomain)
    - references: Entity references another (ExamDomain references Skill)
    - is_instance_of: Concrete instance of abstract (Item is_instance_of Skill)
    - parent_of: Hierarchical parent
    - depends_on: Dependency relationship
    - prerequisite_for: Learning prerequisite
    - related_to: General association
    - correlates_with: Statistical correlation
    - predicts_success_in: Predictive relationship

    This is a value object - immutable after creation.
    """

    id: str
    """Unique identifier for the relationship (UUID)."""

    source_term_id: str
    """ID of the source term (from)."""

    target_term_id: str
    """ID of the target term (to)."""

    relationship_type: RelationshipType | str
    """Type of relationship."""

    description: str | None = None
    """Optional description of the relationship."""

    bidirectional: bool = False
    """Whether the relationship applies in both directions."""

    weight: float = 1.0
    """Weight for graph algorithms (0.0 - 1.0)."""

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    """When the relationship was created."""

    is_active: bool = True
    """Whether the relationship is active (soft delete support)."""

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        rel_type = self.relationship_type
        if isinstance(rel_type, RelationshipType):
            rel_type = rel_type.value

        return {
            "id": self.id,
            "source_term_id": self.source_term_id,
            "target_term_id": self.target_term_id,
            "relationship_type": rel_type,
            "description": self.description,
            "bidirectional": self.bidirectional,
            "weight": self.weight,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_active": self.is_active,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "KnowledgeRelationship":
        """Create from dictionary."""
        from datetime import datetime as dt

        created_at = data.get("created_at")
        rel_type = data.get("relationship_type", "related_to")

        # Try to convert to enum, fallback to string
        try:
            rel_type = RelationshipType(rel_type)
        except ValueError:
            pass  # Keep as string

        return cls(
            id=data["id"],
            source_term_id=data["source_term_id"],
            target_term_id=data["target_term_id"],
            relationship_type=rel_type,
            description=data.get("description"),
            bidirectional=data.get("bidirectional", False),
            weight=data.get("weight", 1.0),
            created_at=dt.fromisoformat(created_at) if isinstance(created_at, str) else created_at or dt.now(),
            is_active=data.get("is_active", True),
        )
