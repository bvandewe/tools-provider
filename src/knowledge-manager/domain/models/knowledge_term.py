"""KnowledgeTerm value object.

Terms are the atomic units of knowledge in a namespace.
They have canonical definitions, aliases, examples, and context hints.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class KnowledgeTerm:
    """A domain-specific term with definition and metadata.

    Terms are the atomic units of knowledge. They have:
    - Canonical definition (Markdown-supported)
    - Aliases for matching variations
    - Examples for context
    - Context hint for when to inject

    This is a value object - immutable after creation.
    Use the aggregate methods to modify terms.
    """

    id: str
    """Unique identifier for the term (UUID)."""

    term: str
    """The canonical term name (e.g., 'ExamBlueprint')."""

    definition: str
    """The definition of the term (Markdown-supported)."""

    aliases: list[str] = field(default_factory=list)
    """Alternative names/spellings for matching."""

    examples: list[str] = field(default_factory=list)
    """Usage examples for context."""

    context_hint: str | None = None
    """Hint for when to inject this term (e.g., 'When discussing exam structure')."""

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    """When the term was created."""

    updated_at: datetime = field(default_factory=datetime.now)
    """When the term was last updated."""

    is_active: bool = True
    """Whether the term is active (soft delete support)."""

    def matches(self, text: str) -> bool:
        """Check if this term or its aliases appear in text.

        Case-insensitive matching against the term and all aliases.

        Args:
            text: The text to search in

        Returns:
            True if the term or any alias is found in the text
        """
        text_lower = text.lower()
        if self.term.lower() in text_lower:
            return True
        return any(alias.lower() in text_lower for alias in self.aliases)

    def to_context_block(self) -> str:
        """Format as a context injection block.

        Returns a formatted string suitable for injection into LLM prompts.

        Returns:
            Markdown-formatted context block
        """
        block = f"**{self.term}**: {self.definition}"
        if self.examples:
            # Include up to 2 examples
            examples_str = ", ".join(self.examples[:2])
            block += f"\n  Examples: {examples_str}"
        return block

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "term": self.term,
            "definition": self.definition,
            "aliases": self.aliases,
            "examples": self.examples,
            "context_hint": self.context_hint,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_active": self.is_active,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "KnowledgeTerm":
        """Create from dictionary."""
        from datetime import datetime as dt

        created_at = data.get("created_at")
        updated_at = data.get("updated_at")

        return cls(
            id=data["id"],
            term=data["term"],
            definition=data["definition"],
            aliases=data.get("aliases", []),
            examples=data.get("examples", []),
            context_hint=data.get("context_hint"),
            created_at=dt.fromisoformat(created_at) if isinstance(created_at, str) else created_at or dt.now(),
            updated_at=dt.fromisoformat(updated_at) if isinstance(updated_at, str) else updated_at or dt.now(),
            is_active=data.get("is_active", True),
        )
