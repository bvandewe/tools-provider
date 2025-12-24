"""KnowledgeNamespace aggregate root.

The primary aggregate for managing domain knowledge including terms,
relationships, and business rules. Supports versioning via revisions.

Following the AggregateRoot + AggregateState pattern from tools-provider.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from multipledispatch import dispatch
from neuroglia.data.abstractions import AggregateRoot, AggregateState

from domain.enums import AccessLevel, RelationshipType, RuleType
from domain.events.knowledge_namespace import (
    KnowledgeNamespaceCreatedDomainEvent,
    KnowledgeNamespaceDeletedDomainEvent,
    KnowledgeNamespaceUpdatedDomainEvent,
    KnowledgeRelationshipAddedDomainEvent,
    KnowledgeRelationshipRemovedDomainEvent,
    KnowledgeRevisionCreatedDomainEvent,
    KnowledgeRevisionRolledBackDomainEvent,
    KnowledgeRuleAddedDomainEvent,
    KnowledgeRuleRemovedDomainEvent,
    KnowledgeRuleUpdatedDomainEvent,
    KnowledgeTermAddedDomainEvent,
    KnowledgeTermRemovedDomainEvent,
    KnowledgeTermUpdatedDomainEvent,
)
from domain.models import KnowledgeTerm


class KnowledgeNamespaceState(AggregateState[str]):
    """Encapsulates the persisted state for the KnowledgeNamespace aggregate.

    This state is persisted via EventStoreDB (event-sourced) for audit-critical
    scenarios with full history and time-travel capability.
    """

    # Identity
    id: str
    """Namespace identifier (slug format, e.g., 'assessments', 'networking')."""

    # Ownership
    owner_tenant_id: str | None
    """Tenant that owns this namespace (None = global/shared)."""

    owner_user_id: str | None
    """User who created this namespace."""

    # Display
    name: str
    """Human-readable name (e.g., 'Assessment Domain')."""

    description: str
    """Description of the namespace (Markdown-supported)."""

    icon: str | None
    """Bootstrap icon class (e.g., 'bi-book')."""

    # Access Control
    access_level: str
    """Visibility level: private, tenant, public. Stored as string for serialization."""

    allowed_tenant_ids: list[str]
    """Explicit tenant allow list (for tenant/public access)."""

    # Versioning
    current_revision: int
    """Current active revision number."""

    revisions: list[dict]
    """Revision metadata (stored as dicts for flexibility)."""

    # Content (stored as dictionaries keyed by ID)
    terms: dict[str, dict]
    """term_id -> KnowledgeTerm.to_dict()"""

    relationships: dict[str, dict]
    """relationship_id -> KnowledgeRelationship.to_dict()"""

    rules: dict[str, dict]
    """rule_id -> KnowledgeRule.to_dict()"""

    # Statistics (denormalized for performance)
    term_count: int
    relationship_count: int
    rule_count: int

    # Audit
    created_by: str | None
    created_at: datetime
    updated_at: datetime

    # Optimistic concurrency
    state_version: int

    def __init__(self) -> None:
        super().__init__()
        # Initialize ALL fields with defaults (required by Neuroglia)
        self.id = ""
        self.owner_tenant_id = None
        self.owner_user_id = None
        self.name = ""
        self.description = ""
        self.icon = None
        self.access_level = AccessLevel.PRIVATE.value  # Store as string for serialization
        self.allowed_tenant_ids = []
        self.current_revision = 0
        self.revisions = []
        self.terms = {}
        self.relationships = {}
        self.rules = {}
        self.term_count = 0
        self.relationship_count = 0
        self.rule_count = 0
        self.created_by = None
        now = datetime.now(UTC)
        self.created_at = now
        self.updated_at = now
        self.state_version = 0

    # =========================================================================
    # Event Handlers - Apply events to state
    # =========================================================================

    @dispatch(KnowledgeNamespaceCreatedDomainEvent)
    def on(self, event: KnowledgeNamespaceCreatedDomainEvent) -> None:  # type: ignore[override]
        """Apply the namespace created event to the state."""
        self.id = event.aggregate_id
        self.name = event.name
        self.description = event.description
        self.owner_user_id = event.owner_user_id
        self.owner_tenant_id = event.owner_tenant_id
        self.icon = event.icon
        self.access_level = event.access_level
        self.created_at = event.created_at
        self.updated_at = event.created_at
        self.created_by = event.owner_user_id

    @dispatch(KnowledgeNamespaceUpdatedDomainEvent)
    def on(self, event: KnowledgeNamespaceUpdatedDomainEvent) -> None:  # type: ignore[override]
        """Apply the namespace updated event to the state."""
        if event.name is not None:
            self.name = event.name
        if event.description is not None:
            self.description = event.description
        if event.icon is not None:
            self.icon = event.icon
        if event.access_level is not None:
            self.access_level = event.access_level
        if event.allowed_tenant_ids is not None:
            self.allowed_tenant_ids = event.allowed_tenant_ids
        self.updated_at = event.updated_at

    @dispatch(KnowledgeNamespaceDeletedDomainEvent)
    def on(self, event: KnowledgeNamespaceDeletedDomainEvent) -> None:  # type: ignore[override]
        """Apply the namespace deleted event to the state."""
        # Mark all content as inactive (soft delete)
        for term_id in self.terms:
            self.terms[term_id]["is_active"] = False
        for rel_id in self.relationships:
            self.relationships[rel_id]["is_active"] = False
        for rule_id in self.rules:
            self.rules[rule_id]["is_active"] = False
        self.updated_at = event.deleted_at

    # === Term Event Handlers ===

    @dispatch(KnowledgeTermAddedDomainEvent)
    def on(self, event: KnowledgeTermAddedDomainEvent) -> None:  # type: ignore[override]
        """Apply the term added event to the state."""
        self.terms[event.term_id] = {
            "id": event.term_id,
            "term": event.term,
            "definition": event.definition,
            "aliases": event.aliases,
            "examples": event.examples,
            "context_hint": event.context_hint,
            "created_at": event.created_at.isoformat(),
            "updated_at": event.created_at.isoformat(),
            "is_active": True,
        }
        self.term_count = len([t for t in self.terms.values() if t.get("is_active", True)])
        self.updated_at = event.created_at

    @dispatch(KnowledgeTermUpdatedDomainEvent)
    def on(self, event: KnowledgeTermUpdatedDomainEvent) -> None:  # type: ignore[override]
        """Apply the term updated event to the state."""
        if event.term_id in self.terms:
            term = self.terms[event.term_id]
            if event.term is not None:
                term["term"] = event.term
            if event.definition is not None:
                term["definition"] = event.definition
            if event.aliases is not None:
                term["aliases"] = event.aliases
            if event.examples is not None:
                term["examples"] = event.examples
            if event.context_hint is not None:
                term["context_hint"] = event.context_hint
            term["updated_at"] = event.updated_at.isoformat()
        self.updated_at = event.updated_at

    @dispatch(KnowledgeTermRemovedDomainEvent)
    def on(self, event: KnowledgeTermRemovedDomainEvent) -> None:  # type: ignore[override]
        """Apply the term removed event to the state."""
        if event.term_id in self.terms:
            self.terms[event.term_id]["is_active"] = False
            self.terms[event.term_id]["updated_at"] = event.removed_at.isoformat()
        self.term_count = len([t for t in self.terms.values() if t.get("is_active", True)])
        self.updated_at = event.removed_at

    # === Relationship Event Handlers ===

    @dispatch(KnowledgeRelationshipAddedDomainEvent)
    def on(self, event: KnowledgeRelationshipAddedDomainEvent) -> None:  # type: ignore[override]
        """Apply the relationship added event to the state."""
        self.relationships[event.relationship_id] = {
            "id": event.relationship_id,
            "source_term_id": event.source_term_id,
            "target_term_id": event.target_term_id,
            "relationship_type": event.relationship_type,
            "description": event.description,
            "bidirectional": event.bidirectional,
            "weight": event.weight,
            "created_at": event.created_at.isoformat(),
            "is_active": True,
        }
        self.relationship_count = len([r for r in self.relationships.values() if r.get("is_active", True)])
        self.updated_at = event.created_at

    @dispatch(KnowledgeRelationshipRemovedDomainEvent)
    def on(self, event: KnowledgeRelationshipRemovedDomainEvent) -> None:  # type: ignore[override]
        """Apply the relationship removed event to the state."""
        if event.relationship_id in self.relationships:
            self.relationships[event.relationship_id]["is_active"] = False
        self.relationship_count = len([r for r in self.relationships.values() if r.get("is_active", True)])
        self.updated_at = event.removed_at

    # === Rule Event Handlers ===

    @dispatch(KnowledgeRuleAddedDomainEvent)
    def on(self, event: KnowledgeRuleAddedDomainEvent) -> None:  # type: ignore[override]
        """Apply the rule added event to the state."""
        self.rules[event.rule_id] = {
            "id": event.rule_id,
            "name": event.name,
            "condition": event.condition,
            "rule_text": event.rule_text,
            "applies_to_term_ids": event.applies_to_term_ids,
            "rule_type": event.rule_type,
            "priority": event.priority,
            "created_at": event.created_at.isoformat(),
            "updated_at": event.created_at.isoformat(),
            "is_active": True,
        }
        self.rule_count = len([r for r in self.rules.values() if r.get("is_active", True)])
        self.updated_at = event.created_at

    @dispatch(KnowledgeRuleUpdatedDomainEvent)
    def on(self, event: KnowledgeRuleUpdatedDomainEvent) -> None:  # type: ignore[override]
        """Apply the rule updated event to the state."""
        if event.rule_id in self.rules:
            rule = self.rules[event.rule_id]
            if event.name is not None:
                rule["name"] = event.name
            if event.condition is not None:
                rule["condition"] = event.condition
            if event.rule_text is not None:
                rule["rule_text"] = event.rule_text
            if event.priority is not None:
                rule["priority"] = event.priority
            rule["updated_at"] = event.updated_at.isoformat()
        self.updated_at = event.updated_at

    @dispatch(KnowledgeRuleRemovedDomainEvent)
    def on(self, event: KnowledgeRuleRemovedDomainEvent) -> None:  # type: ignore[override]
        """Apply the rule removed event to the state."""
        if event.rule_id in self.rules:
            self.rules[event.rule_id]["is_active"] = False
        self.rule_count = len([r for r in self.rules.values() if r.get("is_active", True)])
        self.updated_at = event.removed_at

    # === Revision Event Handlers ===

    @dispatch(KnowledgeRevisionCreatedDomainEvent)
    def on(self, event: KnowledgeRevisionCreatedDomainEvent) -> None:  # type: ignore[override]
        """Apply the revision created event to the state."""
        self.current_revision = event.revision_number
        self.revisions.append(
            {
                "revision_number": event.revision_number,
                "message": event.message,
                "created_by": event.created_by,
                "created_at": event.created_at.isoformat(),
                "term_count": event.term_count,
                "relationship_count": event.relationship_count,
                "rule_count": event.rule_count,
            }
        )
        self.updated_at = event.created_at

    @dispatch(KnowledgeRevisionRolledBackDomainEvent)
    def on(self, event: KnowledgeRevisionRolledBackDomainEvent) -> None:  # type: ignore[override]
        """Apply the revision rolled back event to the state."""
        self.current_revision = event.to_revision
        self.updated_at = event.rolled_back_at


class KnowledgeNamespace(AggregateRoot[KnowledgeNamespaceState, str]):
    """Aggregate root for knowledge namespaces.

    A namespace groups related domain terms, their relationships,
    and business rules. Namespaces support versioning for
    revision history and rollback.

    Persistence: Event-Sourced (EventStoreDB) for full audit trail.
    """

    def __init__(
        self,
        namespace_id: str,
        name: str,
        description: str = "",
        owner_user_id: str | None = None,
        owner_tenant_id: str | None = None,
        icon: str | None = None,
        access_level: AccessLevel | str = AccessLevel.PRIVATE,
        **kwargs: Any,
    ) -> None:
        """Create a new KnowledgeNamespace.

        Args:
            namespace_id: Unique identifier (slug format recommended)
            name: Human-readable name
            description: Description (Markdown-supported)
            owner_user_id: User who created this namespace
            owner_tenant_id: Tenant that owns this namespace
            icon: Bootstrap icon class
            access_level: Visibility level
        """
        super().__init__()
        now = datetime.now(UTC)

        # Convert enum to string if needed
        access_level_str = access_level.value if isinstance(access_level, AccessLevel) else access_level

        event = KnowledgeNamespaceCreatedDomainEvent(
            aggregate_id=namespace_id,
            name=name,
            description=description,
            owner_user_id=owner_user_id,
            owner_tenant_id=owner_tenant_id,
            icon=icon,
            access_level=access_level_str,
            created_at=now,
        )
        self.state.on(self.register_event(event))  # type: ignore

    # =========================================================================
    # Namespace Management
    # =========================================================================

    def update(
        self,
        name: str | None = None,
        description: str | None = None,
        icon: str | None = None,
        access_level: AccessLevel | str | None = None,
        allowed_tenant_ids: list[str] | None = None,
    ) -> bool:
        """Update namespace properties.

        Args:
            name: New name (optional)
            description: New description (optional)
            icon: New icon class (optional)
            access_level: New access level (optional)
            allowed_tenant_ids: New tenant allow list (optional)

        Returns:
            True if update was applied
        """
        now = datetime.now(UTC)

        # Convert enum to string if needed
        access_level_str = None
        if access_level is not None:
            access_level_str = access_level.value if isinstance(access_level, AccessLevel) else access_level

        event = KnowledgeNamespaceUpdatedDomainEvent(
            aggregate_id=self.id(),
            name=name,
            description=description,
            icon=icon,
            access_level=access_level_str,
            allowed_tenant_ids=allowed_tenant_ids,
            updated_at=now,
        )
        self.state.on(self.register_event(event))  # type: ignore
        return True

    def delete(self, deleted_by: str) -> bool:
        """Soft delete the namespace.

        Args:
            deleted_by: User ID who deleted this namespace

        Returns:
            True if deletion was applied
        """
        now = datetime.now(UTC)
        event = KnowledgeNamespaceDeletedDomainEvent(
            aggregate_id=self.id(),
            deleted_by=deleted_by,
            deleted_at=now,
        )
        self.state.on(self.register_event(event))  # type: ignore
        return True

    # =========================================================================
    # Term Management
    # =========================================================================

    def add_term(
        self,
        term: str,
        definition: str,
        aliases: list[str] | None = None,
        examples: list[str] | None = None,
        context_hint: str | None = None,
    ) -> str:
        """Add a term to this namespace.

        Args:
            term: The canonical term name
            definition: The definition (Markdown-supported)
            aliases: Alternative names for matching
            examples: Usage examples
            context_hint: When to inject this term

        Returns:
            The generated term_id
        """
        term_id = str(uuid4())
        now = datetime.now(UTC)

        event = KnowledgeTermAddedDomainEvent(
            aggregate_id=self.id(),
            term_id=term_id,
            term=term,
            definition=definition,
            aliases=aliases or [],
            examples=examples or [],
            context_hint=context_hint,
            created_at=now,
        )
        self.state.on(self.register_event(event))  # type: ignore
        return term_id

    def update_term(
        self,
        term_id: str,
        term: str | None = None,
        definition: str | None = None,
        aliases: list[str] | None = None,
        examples: list[str] | None = None,
        context_hint: str | None = None,
    ) -> bool:
        """Update an existing term.

        Args:
            term_id: ID of the term to update
            term: New term name (optional)
            definition: New definition (optional)
            aliases: New aliases (optional)
            examples: New examples (optional)
            context_hint: New context hint (optional)

        Returns:
            True if term exists and was updated
        """
        if term_id not in self.state.terms:
            return False

        now = datetime.now(UTC)
        event = KnowledgeTermUpdatedDomainEvent(
            aggregate_id=self.id(),
            term_id=term_id,
            term=term,
            definition=definition,
            aliases=aliases,
            examples=examples,
            context_hint=context_hint,
            updated_at=now,
        )
        self.state.on(self.register_event(event))  # type: ignore
        return True

    def remove_term(self, term_id: str) -> bool:
        """Remove a term (soft delete).

        Args:
            term_id: ID of the term to remove

        Returns:
            True if term exists and was removed
        """
        if term_id not in self.state.terms:
            return False

        now = datetime.now(UTC)
        event = KnowledgeTermRemovedDomainEvent(
            aggregate_id=self.id(),
            term_id=term_id,
            removed_at=now,
        )
        self.state.on(self.register_event(event))  # type: ignore
        return True

    def get_term(self, term_id: str) -> KnowledgeTerm | None:
        """Get a term by ID.

        Args:
            term_id: ID of the term

        Returns:
            KnowledgeTerm if found and active, None otherwise
        """
        term_data = self.state.terms.get(term_id)
        if term_data and term_data.get("is_active", True):
            return KnowledgeTerm.from_dict(term_data)
        return None

    def get_active_terms(self) -> list[KnowledgeTerm]:
        """Get all active terms.

        Returns:
            List of active KnowledgeTerm objects
        """
        return [KnowledgeTerm.from_dict(t) for t in self.state.terms.values() if t.get("is_active", True)]

    # =========================================================================
    # Relationship Management
    # =========================================================================

    def add_relationship(
        self,
        source_term_id: str,
        target_term_id: str,
        relationship_type: RelationshipType | str,
        description: str | None = None,
        bidirectional: bool = False,
        weight: float = 1.0,
    ) -> str:
        """Add a relationship between terms.

        Args:
            source_term_id: ID of the source term
            target_term_id: ID of the target term
            relationship_type: Type of relationship
            description: Description of the relationship
            bidirectional: Whether the relationship applies both ways
            weight: Weight for graph algorithms

        Returns:
            The generated relationship_id
        """
        relationship_id = str(uuid4())
        now = datetime.now(UTC)

        # Convert enum to string if needed
        rel_type_str = relationship_type.value if isinstance(relationship_type, RelationshipType) else relationship_type

        event = KnowledgeRelationshipAddedDomainEvent(
            aggregate_id=self.id(),
            relationship_id=relationship_id,
            source_term_id=source_term_id,
            target_term_id=target_term_id,
            relationship_type=rel_type_str,
            description=description,
            bidirectional=bidirectional,
            weight=weight,
            created_at=now,
        )
        self.state.on(self.register_event(event))  # type: ignore
        return relationship_id

    def remove_relationship(self, relationship_id: str) -> bool:
        """Remove a relationship (soft delete).

        Args:
            relationship_id: ID of the relationship to remove

        Returns:
            True if relationship exists and was removed
        """
        if relationship_id not in self.state.relationships:
            return False

        now = datetime.now(UTC)
        event = KnowledgeRelationshipRemovedDomainEvent(
            aggregate_id=self.id(),
            relationship_id=relationship_id,
            removed_at=now,
        )
        self.state.on(self.register_event(event))  # type: ignore
        return True

    # =========================================================================
    # Rule Management
    # =========================================================================

    def add_rule(
        self,
        name: str,
        condition: str,
        rule_text: str,
        applies_to_term_ids: list[str] | None = None,
        rule_type: RuleType | str = RuleType.CONSTRAINT,
        priority: int = 0,
    ) -> str:
        """Add a business rule.

        Args:
            name: Human-readable rule name
            condition: When to apply the rule
            rule_text: The actual rule content
            applies_to_term_ids: Term IDs this rule applies to
            rule_type: Type of rule
            priority: Priority for ordering

        Returns:
            The generated rule_id
        """
        rule_id = str(uuid4())
        now = datetime.now(UTC)

        # Convert enum to string if needed
        rule_type_str = rule_type.value if isinstance(rule_type, RuleType) else rule_type

        event = KnowledgeRuleAddedDomainEvent(
            aggregate_id=self.id(),
            rule_id=rule_id,
            name=name,
            condition=condition,
            rule_text=rule_text,
            applies_to_term_ids=applies_to_term_ids or [],
            rule_type=rule_type_str,
            priority=priority,
            created_at=now,
        )
        self.state.on(self.register_event(event))  # type: ignore
        return rule_id

    def update_rule(
        self,
        rule_id: str,
        name: str | None = None,
        condition: str | None = None,
        rule_text: str | None = None,
        priority: int | None = None,
    ) -> bool:
        """Update an existing rule.

        Args:
            rule_id: ID of the rule to update
            name: New name (optional)
            condition: New condition (optional)
            rule_text: New rule text (optional)
            priority: New priority (optional)

        Returns:
            True if rule exists and was updated
        """
        if rule_id not in self.state.rules:
            return False

        now = datetime.now(UTC)
        event = KnowledgeRuleUpdatedDomainEvent(
            aggregate_id=self.id(),
            rule_id=rule_id,
            name=name,
            condition=condition,
            rule_text=rule_text,
            priority=priority,
            updated_at=now,
        )
        self.state.on(self.register_event(event))  # type: ignore
        return True

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule (soft delete).

        Args:
            rule_id: ID of the rule to remove

        Returns:
            True if rule exists and was removed
        """
        if rule_id not in self.state.rules:
            return False

        now = datetime.now(UTC)
        event = KnowledgeRuleRemovedDomainEvent(
            aggregate_id=self.id(),
            rule_id=rule_id,
            removed_at=now,
        )
        self.state.on(self.register_event(event))  # type: ignore
        return True

    # =========================================================================
    # Versioning
    # =========================================================================

    def create_revision(self, message: str, created_by: str) -> int:
        """Create a new revision snapshot.

        Args:
            message: Commit message describing the changes
            created_by: User ID who created this revision

        Returns:
            The new revision number
        """
        now = datetime.now(UTC)
        revision_number = self.state.current_revision + 1

        event = KnowledgeRevisionCreatedDomainEvent(
            aggregate_id=self.id(),
            revision_number=revision_number,
            message=message,
            created_by=created_by,
            created_at=now,
            term_count=self.state.term_count,
            relationship_count=self.state.relationship_count,
            rule_count=self.state.rule_count,
        )
        self.state.on(self.register_event(event))  # type: ignore
        return revision_number

    def rollback_to_revision(self, revision: int, rolled_back_by: str) -> bool:
        """Rollback to a previous revision.

        Note: This is a simplified implementation. Full rollback would
        require restoring the term/relationship/rule snapshots from
        the target revision.

        Args:
            revision: Target revision number
            rolled_back_by: User ID who triggered the rollback

        Returns:
            True if rollback was applied
        """
        # Validate revision exists
        if revision < 0 or revision > self.state.current_revision:
            return False

        now = datetime.now(UTC)
        event = KnowledgeRevisionRolledBackDomainEvent(
            aggregate_id=self.id(),
            from_revision=self.state.current_revision,
            to_revision=revision,
            rolled_back_by=rolled_back_by,
            rolled_back_at=now,
        )
        self.state.on(self.register_event(event))  # type: ignore
        return True
