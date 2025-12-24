"""Domain repository interfaces for Knowledge Manager."""

from domain.repositories.namespace_repositories import (
    KnowledgeGraphRepository,
    KnowledgeNamespaceRepository,
    KnowledgeVectorRepository,
)

__all__ = [
    "KnowledgeNamespaceRepository",
    "KnowledgeGraphRepository",
    "KnowledgeVectorRepository",
]
