"""Knowledge namespace DTOs with queryable decorator."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from neuroglia.data.abstractions import queryable

from domain.enums import AccessLevel, RelationshipType, RuleType


@queryable
@dataclass
class KnowledgeTermDto:
    """DTO for knowledge term read model."""

    id: str
    """Unique term identifier."""

    namespace_id: str
    """Parent namespace identifier."""

    term: str
    """The term or phrase."""

    definition: str
    """Definition or explanation."""

    aliases: list[str] = field(default_factory=list)
    """Alternative names or spellings."""

    examples: list[str] = field(default_factory=list)
    """Usage examples."""

    context_hint: str | None = None
    """Optional context hint for AI agents."""

    created_at: datetime | None = None
    """When the term was created."""

    updated_at: datetime | None = None
    """When the term was last updated."""

    is_active: bool = True
    """Whether the term is active."""


@queryable
@dataclass
class KnowledgeRelationshipDto:
    """DTO for knowledge relationship read model."""

    id: str
    """Unique relationship identifier."""

    namespace_id: str
    """Parent namespace identifier."""

    source_term_id: str
    """Source term in the relationship."""

    target_term_id: str
    """Target term in the relationship."""

    relationship_type: RelationshipType
    """Type of relationship."""

    weight: float = 1.0
    """Relationship strength/weight."""

    bidirectional: bool = False
    """Whether relationship applies in both directions."""

    created_at: datetime | None = None
    """When the relationship was created."""


@queryable
@dataclass
class KnowledgeRuleDto:
    """DTO for knowledge rule read model."""

    id: str
    """Unique rule identifier."""

    namespace_id: str
    """Parent namespace identifier."""

    name: str
    """Rule name."""

    condition: str
    """Condition expression."""

    rule_text: str
    """Rule content."""

    applies_to_term_ids: list[str] = field(default_factory=list)
    """Terms this rule applies to."""

    rule_type: RuleType = RuleType.CONSTRAINT
    """Type of rule."""

    priority: int = 0
    """Rule priority (higher = more important)."""

    created_at: datetime | None = None
    """When the rule was created."""


@queryable
@dataclass
class KnowledgeNamespaceDto:
    """DTO for knowledge namespace read model."""

    id: str
    """Unique namespace identifier (slug)."""

    name: str
    """Human-readable name."""

    description: str
    """Namespace description."""

    tenant_id: str | None = None
    """Owning tenant ID."""

    is_public: bool = False
    """Whether namespace is publicly accessible."""

    access_level: AccessLevel = AccessLevel.PRIVATE
    """Default access level."""

    owner_id: str | None = None
    """User ID of owner."""

    allowed_users: list[str] = field(default_factory=list)
    """Users with access."""

    allowed_roles: list[str] = field(default_factory=list)
    """Roles with access."""

    term_count: int = 0
    """Number of active terms."""

    relationship_count: int = 0
    """Number of relationships."""

    rule_count: int = 0
    """Number of rules."""

    revision_count: int = 0
    """Number of revisions."""

    current_revision: int = 0
    """Current revision number."""

    created_at: datetime | None = None
    """When the namespace was created."""

    updated_at: datetime | None = None
    """When the namespace was last updated."""

    last_modified_by: str | None = None
    """User who last modified."""

    is_deleted: bool = False
    """Soft delete flag."""

    # Embedded terms (for full namespace queries)
    terms: list[KnowledgeTermDto] = field(default_factory=list)
    """Terms in this namespace (optional embed)."""

    relationships: list[KnowledgeRelationshipDto] = field(default_factory=list)
    """Relationships in this namespace (optional embed)."""

    rules: list[KnowledgeRuleDto] = field(default_factory=list)
    """Rules in this namespace (optional embed)."""

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional metadata."""

    @property
    def is_active(self) -> bool:
        """Whether namespace is active (not deleted)."""
        return not self.is_deleted
