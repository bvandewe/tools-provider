"""Tests for KnowledgeNamespace aggregate."""

import pytest

from domain.entities import KnowledgeNamespace
from domain.enums import AccessLevel, RelationshipType, RuleType
from domain.events import (
    KnowledgeNamespaceCreatedDomainEvent,
    KnowledgeTermAddedDomainEvent,
    KnowledgeTermRemovedDomainEvent,
    KnowledgeTermUpdatedDomainEvent,
)


@pytest.mark.unit
@pytest.mark.domain
class TestKnowledgeNamespaceCreation:
    """Tests for namespace creation."""

    def test_create_namespace_with_required_fields(self):
        """Test creating namespace with minimum required fields."""
        namespace = KnowledgeNamespace.create(
            namespace_id="test-ns",
            name="Test Namespace",
            description="Test description",
            owner_id="user-123",
        )

        assert namespace.id() == "test-ns"
        assert namespace.state.name == "Test Namespace"
        assert namespace.state.description == "Test description"
        assert namespace.state.owner_id == "user-123"
        assert namespace.state.is_public is False
        assert namespace.state.access_level == AccessLevel.PRIVATE

    def test_create_namespace_with_all_fields(self):
        """Test creating namespace with all fields."""
        namespace = KnowledgeNamespace.create(
            namespace_id="full-ns",
            name="Full Namespace",
            description="Full description",
            owner_id="user-123",
            tenant_id="tenant-abc",
            is_public=True,
        )

        assert namespace.state.tenant_id == "tenant-abc"
        assert namespace.state.is_public is True

    def test_create_namespace_emits_event(self):
        """Test that creation emits domain event."""
        namespace = KnowledgeNamespace.create(
            namespace_id="event-ns",
            name="Event Namespace",
            description="Description",
            owner_id="user-123",
        )

        events = namespace.pending_events
        assert len(events) == 1
        assert isinstance(events[0], KnowledgeNamespaceCreatedDomainEvent)
        assert events[0].aggregate_id == "event-ns"
        assert events[0].name == "Event Namespace"


@pytest.mark.unit
@pytest.mark.domain
class TestKnowledgeNamespaceTerms:
    """Tests for term management within namespace."""

    def test_add_term(self, sample_namespace):
        """Test adding a term to namespace."""
        sample_namespace.add_term(
            term="API",
            definition="Application Programming Interface",
            aliases=["interface"],
            examples=["REST API"],
            context_hint="Software interfaces",
            user_id="user-123",
        )

        terms = sample_namespace.get_active_terms()
        assert len(terms) == 1
        assert terms[0].term == "API"
        assert terms[0].definition == "Application Programming Interface"

    def test_add_term_emits_event(self, sample_namespace):
        """Test that adding term emits event."""
        sample_namespace.clear_pending_events()

        sample_namespace.add_term(
            term="Test Term",
            definition="Test Definition",
            user_id="user-123",
        )

        events = sample_namespace.pending_events
        # Should have term added event
        term_events = [e for e in events if isinstance(e, KnowledgeTermAddedDomainEvent)]
        assert len(term_events) == 1
        assert term_events[0].term == "Test Term"

    def test_update_term(self, sample_namespace):
        """Test updating an existing term."""
        sample_namespace.add_term(
            term="Original",
            definition="Original definition",
            user_id="user-123",
        )

        term_id = sample_namespace.get_active_terms()[0].id
        sample_namespace.clear_pending_events()

        sample_namespace.update_term(
            term_id=term_id,
            definition="Updated definition",
            user_id="user-123",
        )

        term = sample_namespace.get_term(term_id)
        assert term.definition == "Updated definition"

        events = sample_namespace.pending_events
        update_events = [e for e in events if isinstance(e, KnowledgeTermUpdatedDomainEvent)]
        assert len(update_events) == 1

    def test_remove_term(self, sample_namespace):
        """Test removing a term (soft delete)."""
        sample_namespace.add_term(
            term="ToRemove",
            definition="Will be removed",
            user_id="user-123",
        )

        term_id = sample_namespace.get_active_terms()[0].id
        sample_namespace.clear_pending_events()

        sample_namespace.remove_term(term_id=term_id, user_id="user-123")

        # Term should no longer be in active terms
        active_terms = sample_namespace.get_active_terms()
        assert len(active_terms) == 0

        # But should still exist (soft deleted)
        term = sample_namespace.get_term(term_id)
        assert term is not None
        assert term.is_active is False

        events = sample_namespace.pending_events
        remove_events = [e for e in events if isinstance(e, KnowledgeTermRemovedDomainEvent)]
        assert len(remove_events) == 1

    def test_term_matching(self, sample_namespace):
        """Test term matching functionality."""
        sample_namespace.add_term(
            term="API",
            definition="Application Programming Interface",
            aliases=["Application Programming Interface", "interface"],
            user_id="user-123",
        )

        term = sample_namespace.get_active_terms()[0]

        # Should match term text
        assert term.matches("api")
        assert term.matches("API")

        # Should match aliases
        assert term.matches("interface")
        assert term.matches("application programming")

        # Should not match unrelated text
        assert not term.matches("database")


@pytest.mark.unit
@pytest.mark.domain
class TestKnowledgeNamespaceRelationships:
    """Tests for relationship management."""

    def test_add_relationship(self, sample_namespace):
        """Test adding a relationship between terms."""
        sample_namespace.add_term(
            term="REST",
            definition="Representational State Transfer",
            user_id="user-123",
        )
        sample_namespace.add_term(
            term="API",
            definition="Application Programming Interface",
            user_id="user-123",
        )

        terms = sample_namespace.get_active_terms()
        rest_id = next(t.id for t in terms if t.term == "REST")
        api_id = next(t.id for t in terms if t.term == "API")

        sample_namespace.add_relationship(
            source_term_id=rest_id,
            target_term_id=api_id,
            relationship_type=RelationshipType.RELATED_TO,
            weight=0.9,
            bidirectional=False,
            user_id="user-123",
        )

        relationships = list(sample_namespace.state.relationships.values())
        assert len(relationships) == 1
        assert relationships[0].source_term_id == rest_id
        assert relationships[0].target_term_id == api_id
        assert relationships[0].relationship_type == RelationshipType.RELATED_TO


@pytest.mark.unit
@pytest.mark.domain
class TestKnowledgeNamespaceRules:
    """Tests for rule management."""

    def test_add_rule(self, sample_namespace):
        """Test adding a rule."""
        sample_namespace.add_rule(
            name="Always uppercase API",
            condition="term.matches('api')",
            rule_text="API should always be written in uppercase",
            applies_to_term_ids=[],
            rule_type=RuleType.CONSTRAINT,
            priority=10,
            user_id="user-123",
        )

        rules = list(sample_namespace.state.rules.values())
        assert len(rules) == 1
        assert rules[0].name == "Always uppercase API"
        assert rules[0].rule_type == RuleType.CONSTRAINT
        assert rules[0].priority == 10


@pytest.mark.unit
@pytest.mark.domain
class TestKnowledgeNamespaceRevisions:
    """Tests for revision management."""

    def test_create_revision(self, sample_namespace):
        """Test creating a revision snapshot."""
        sample_namespace.add_term(
            term="Initial Term",
            definition="Initial definition",
            user_id="user-123",
        )

        sample_namespace.create_revision(
            message="Initial snapshot",
            user_id="user-123",
        )

        assert sample_namespace.state.current_revision == 1
        assert len(sample_namespace.state.revisions) == 1
        assert sample_namespace.state.revisions[0].message == "Initial snapshot"
