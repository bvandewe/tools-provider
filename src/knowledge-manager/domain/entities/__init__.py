"""Domain entities (aggregate roots) for Knowledge Manager."""

from domain.entities.knowledge_namespace import KnowledgeNamespace, KnowledgeNamespaceState

__all__ = [
    "KnowledgeNamespace",
    "KnowledgeNamespaceState",
]
