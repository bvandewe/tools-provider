"""KnowledgeRule value object.

Represents a business rule or constraint within a namespace.
"""

from dataclasses import dataclass, field
from datetime import datetime

from domain.enums import RuleType


@dataclass
class KnowledgeRule:
    """Business rule or constraint in the domain.

    Rules are injected into context when their associated terms
    are detected in the user's query.

    Rule types:
    - constraint: Must be satisfied (validation)
    - incentive: Encourages behavior (soft rule)
    - procedure: Defines a process
    - definition: Definitional rule (always true by construction)

    This is a value object - immutable after creation.
    """

    id: str
    """Unique identifier for the rule (UUID)."""

    name: str
    """Human-readable rule name (e.g., 'Blueprint Domain Requirement')."""

    condition: str
    """When to apply the rule (e.g., 'When discussing ExamBlueprint structure')."""

    rule_text: str
    """The actual rule content (Markdown-supported)."""

    applies_to_term_ids: list[str] = field(default_factory=list)
    """Term IDs this rule applies to."""

    rule_type: RuleType | str = RuleType.CONSTRAINT
    """Type of rule."""

    priority: int = 0
    """Priority for ordering (higher = inject first)."""

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    """When the rule was created."""

    updated_at: datetime = field(default_factory=datetime.now)
    """When the rule was last updated."""

    is_active: bool = True
    """Whether the rule is active (soft delete support)."""

    def to_context_block(self) -> str:
        """Format as a rule injection block.

        Returns a formatted string suitable for injection into LLM prompts.

        Returns:
            Markdown-formatted rule block
        """
        return f"**Rule - {self.name}**: {self.rule_text}"

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        rule_type = self.rule_type
        if isinstance(rule_type, RuleType):
            rule_type = rule_type.value

        return {
            "id": self.id,
            "name": self.name,
            "condition": self.condition,
            "rule_text": self.rule_text,
            "applies_to_term_ids": self.applies_to_term_ids,
            "rule_type": rule_type,
            "priority": self.priority,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_active": self.is_active,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "KnowledgeRule":
        """Create from dictionary."""
        from datetime import datetime as dt

        created_at = data.get("created_at")
        updated_at = data.get("updated_at")
        rule_type = data.get("rule_type", "constraint")

        # Try to convert to enum, fallback to string
        try:
            rule_type = RuleType(rule_type)
        except ValueError:
            pass  # Keep as string

        return cls(
            id=data["id"],
            name=data["name"],
            condition=data["condition"],
            rule_text=data["rule_text"],
            applies_to_term_ids=data.get("applies_to_term_ids", []),
            rule_type=rule_type,
            priority=data.get("priority", 0),
            created_at=dt.fromisoformat(created_at) if isinstance(created_at, str) else created_at or dt.now(),
            updated_at=dt.fromisoformat(updated_at) if isinstance(updated_at, str) else updated_at or dt.now(),
            is_active=data.get("is_active", True),
        )
