"""Domain events for KnowledgeNamespace aggregate.

These events represent state changes in the KnowledgeNamespace lifecycle,
following the @cloudevent decorator pattern from tools-provider.
"""

from dataclasses import dataclass
from datetime import datetime

from neuroglia.data.abstractions import DomainEvent
from neuroglia.eventing.cloud_events.decorators import cloudevent

# =============================================================================
# Namespace Events
# =============================================================================


@cloudevent("knowledge.namespace.created.v1")
@dataclass
class KnowledgeNamespaceCreatedDomainEvent(DomainEvent):
    """Event raised when a new knowledge namespace is created."""

    aggregate_id: str
    name: str
    description: str
    owner_user_id: str | None
    owner_tenant_id: str | None
    icon: str | None
    access_level: str
    created_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        name: str,
        description: str,
        created_at: datetime,
        owner_user_id: str | None = None,
        owner_tenant_id: str | None = None,
        icon: str | None = None,
        access_level: str = "private",
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.name = name
        self.description = description
        self.owner_user_id = owner_user_id
        self.owner_tenant_id = owner_tenant_id
        self.icon = icon
        self.access_level = access_level
        self.created_at = created_at


@cloudevent("knowledge.namespace.updated.v1")
@dataclass
class KnowledgeNamespaceUpdatedDomainEvent(DomainEvent):
    """Event raised when a namespace's properties are updated."""

    aggregate_id: str
    name: str | None
    description: str | None
    icon: str | None
    access_level: str | None
    allowed_tenant_ids: list[str] | None
    updated_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        updated_at: datetime,
        name: str | None = None,
        description: str | None = None,
        icon: str | None = None,
        access_level: str | None = None,
        allowed_tenant_ids: list[str] | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.name = name
        self.description = description
        self.icon = icon
        self.access_level = access_level
        self.allowed_tenant_ids = allowed_tenant_ids
        self.updated_at = updated_at


@cloudevent("knowledge.namespace.deleted.v1")
@dataclass
class KnowledgeNamespaceDeletedDomainEvent(DomainEvent):
    """Event raised when a namespace is soft deleted."""

    aggregate_id: str
    deleted_by: str
    deleted_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        deleted_by: str,
        deleted_at: datetime,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.deleted_by = deleted_by
        self.deleted_at = deleted_at


# =============================================================================
# Term Events
# =============================================================================


@cloudevent("knowledge.term.added.v1")
@dataclass
class KnowledgeTermAddedDomainEvent(DomainEvent):
    """Event raised when a term is added to a namespace."""

    aggregate_id: str  # namespace_id
    term_id: str
    term: str
    definition: str
    aliases: list[str]
    examples: list[str]
    context_hint: str | None
    created_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        term_id: str,
        term: str,
        definition: str,
        created_at: datetime,
        aliases: list[str] | None = None,
        examples: list[str] | None = None,
        context_hint: str | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.term_id = term_id
        self.term = term
        self.definition = definition
        self.aliases = aliases or []
        self.examples = examples or []
        self.context_hint = context_hint
        self.created_at = created_at


@cloudevent("knowledge.term.updated.v1")
@dataclass
class KnowledgeTermUpdatedDomainEvent(DomainEvent):
    """Event raised when a term is updated."""

    aggregate_id: str
    term_id: str
    term: str | None
    definition: str | None
    aliases: list[str] | None
    examples: list[str] | None
    context_hint: str | None
    updated_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        term_id: str,
        updated_at: datetime,
        term: str | None = None,
        definition: str | None = None,
        aliases: list[str] | None = None,
        examples: list[str] | None = None,
        context_hint: str | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.term_id = term_id
        self.term = term
        self.definition = definition
        self.aliases = aliases
        self.examples = examples
        self.context_hint = context_hint
        self.updated_at = updated_at


@cloudevent("knowledge.term.removed.v1")
@dataclass
class KnowledgeTermRemovedDomainEvent(DomainEvent):
    """Event raised when a term is removed (soft deleted)."""

    aggregate_id: str
    term_id: str
    removed_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        term_id: str,
        removed_at: datetime,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.term_id = term_id
        self.removed_at = removed_at


# =============================================================================
# Relationship Events
# =============================================================================


@cloudevent("knowledge.relationship.added.v1")
@dataclass
class KnowledgeRelationshipAddedDomainEvent(DomainEvent):
    """Event raised when a relationship is added between terms."""

    aggregate_id: str
    relationship_id: str
    source_term_id: str
    target_term_id: str
    relationship_type: str
    description: str | None
    bidirectional: bool
    weight: float
    created_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        relationship_id: str,
        source_term_id: str,
        target_term_id: str,
        relationship_type: str,
        created_at: datetime,
        description: str | None = None,
        bidirectional: bool = False,
        weight: float = 1.0,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.relationship_id = relationship_id
        self.source_term_id = source_term_id
        self.target_term_id = target_term_id
        self.relationship_type = relationship_type
        self.description = description
        self.bidirectional = bidirectional
        self.weight = weight
        self.created_at = created_at


@cloudevent("knowledge.relationship.removed.v1")
@dataclass
class KnowledgeRelationshipRemovedDomainEvent(DomainEvent):
    """Event raised when a relationship is removed."""

    aggregate_id: str
    relationship_id: str
    removed_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        relationship_id: str,
        removed_at: datetime,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.relationship_id = relationship_id
        self.removed_at = removed_at


# =============================================================================
# Rule Events
# =============================================================================


@cloudevent("knowledge.rule.added.v1")
@dataclass
class KnowledgeRuleAddedDomainEvent(DomainEvent):
    """Event raised when a business rule is added."""

    aggregate_id: str
    rule_id: str
    name: str
    condition: str
    rule_text: str
    applies_to_term_ids: list[str]
    rule_type: str
    priority: int
    created_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        rule_id: str,
        name: str,
        condition: str,
        rule_text: str,
        created_at: datetime,
        applies_to_term_ids: list[str] | None = None,
        rule_type: str = "constraint",
        priority: int = 0,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.rule_id = rule_id
        self.name = name
        self.condition = condition
        self.rule_text = rule_text
        self.applies_to_term_ids = applies_to_term_ids or []
        self.rule_type = rule_type
        self.priority = priority
        self.created_at = created_at


@cloudevent("knowledge.rule.updated.v1")
@dataclass
class KnowledgeRuleUpdatedDomainEvent(DomainEvent):
    """Event raised when a rule is updated."""

    aggregate_id: str
    rule_id: str
    name: str | None
    condition: str | None
    rule_text: str | None
    priority: int | None
    updated_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        rule_id: str,
        updated_at: datetime,
        name: str | None = None,
        condition: str | None = None,
        rule_text: str | None = None,
        priority: int | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.rule_id = rule_id
        self.name = name
        self.condition = condition
        self.rule_text = rule_text
        self.priority = priority
        self.updated_at = updated_at


@cloudevent("knowledge.rule.removed.v1")
@dataclass
class KnowledgeRuleRemovedDomainEvent(DomainEvent):
    """Event raised when a rule is removed."""

    aggregate_id: str
    rule_id: str
    removed_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        rule_id: str,
        removed_at: datetime,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.rule_id = rule_id
        self.removed_at = removed_at


# =============================================================================
# Revision Events
# =============================================================================


@cloudevent("knowledge.revision.created.v1")
@dataclass
class KnowledgeRevisionCreatedDomainEvent(DomainEvent):
    """Event raised when a revision snapshot is created."""

    aggregate_id: str
    revision_number: int
    message: str
    created_by: str
    created_at: datetime
    term_count: int
    relationship_count: int
    rule_count: int

    def __init__(
        self,
        aggregate_id: str,
        revision_number: int,
        message: str,
        created_by: str,
        created_at: datetime,
        term_count: int = 0,
        relationship_count: int = 0,
        rule_count: int = 0,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.revision_number = revision_number
        self.message = message
        self.created_by = created_by
        self.created_at = created_at
        self.term_count = term_count
        self.relationship_count = relationship_count
        self.rule_count = rule_count


@cloudevent("knowledge.revision.rolledback.v1")
@dataclass
class KnowledgeRevisionRolledBackDomainEvent(DomainEvent):
    """Event raised when a namespace is rolled back to a previous revision."""

    aggregate_id: str
    from_revision: int
    to_revision: int
    rolled_back_by: str
    rolled_back_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        from_revision: int,
        to_revision: int,
        rolled_back_by: str,
        rolled_back_at: datetime,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.from_revision = from_revision
        self.to_revision = to_revision
        self.rolled_back_by = rolled_back_by
        self.rolled_back_at = rolled_back_at
