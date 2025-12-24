"""Domain events for Knowledge Manager."""

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

__all__ = [
    # Namespace events
    "KnowledgeNamespaceCreatedDomainEvent",
    "KnowledgeNamespaceUpdatedDomainEvent",
    "KnowledgeNamespaceDeletedDomainEvent",
    # Term events
    "KnowledgeTermAddedDomainEvent",
    "KnowledgeTermUpdatedDomainEvent",
    "KnowledgeTermRemovedDomainEvent",
    # Relationship events
    "KnowledgeRelationshipAddedDomainEvent",
    "KnowledgeRelationshipRemovedDomainEvent",
    # Rule events
    "KnowledgeRuleAddedDomainEvent",
    "KnowledgeRuleUpdatedDomainEvent",
    "KnowledgeRuleRemovedDomainEvent",
    # Revision events
    "KnowledgeRevisionCreatedDomainEvent",
    "KnowledgeRevisionRolledBackDomainEvent",
]
