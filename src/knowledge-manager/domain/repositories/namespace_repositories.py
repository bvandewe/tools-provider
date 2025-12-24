"""Repository interfaces for KnowledgeNamespace aggregate.

Following Neuroglia's repository pattern with support for multiple storage dimensions:
1. MongoDB (aggregate state persistence via MotorRepository)
2. Neo4j (graph relationships) - Phase 2
3. Vector Store (term embeddings) - Phase 3

Note: Query handlers use the aggregate repository directly and map to DTOs inline,
following the same simplified pattern as agent-host.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from neuroglia.data.infrastructure.abstractions import Repository

if TYPE_CHECKING:
    from domain.entities import KnowledgeNamespace


class KnowledgeNamespaceRepository(Repository["KnowledgeNamespace", str], ABC):
    """Repository interface for KnowledgeNamespace aggregate.

    Implementations use MongoDB via MotorRepository for state persistence.
    Query handlers use this repository directly and map aggregates to DTOs inline.

    Note: Standard CRUD operations (get_async, add_async, update_async, remove_async)
    are inherited from the base Repository interface and implemented by MotorRepository.
    Only domain-specific query methods are declared here.
    """

    @abstractmethod
    async def get_by_tenant_async(self, tenant_id: str) -> list["KnowledgeNamespace"]:
        """Get namespaces belonging to a tenant.

        Args:
            tenant_id: The tenant to filter by

        Returns:
            List of namespaces belonging to the tenant
        """
        ...

    @abstractmethod
    async def get_public_async(self) -> list["KnowledgeNamespace"]:
        """Get all public namespaces.

        Returns:
            List of public namespaces
        """
        ...


class KnowledgeGraphRepository(ABC):
    """Graph-specific operations for relationship traversal (Phase 2).

    Implementations use Neo4j for graph queries.
    """

    @abstractmethod
    async def traverse_relationships(
        self,
        term_id: str,
        relationship_types: list[str] | None = None,
        direction: str = "outgoing",  # "outgoing", "incoming", "both"
        max_depth: int = 2,
    ) -> list[dict]:
        """Traverse graph from a starting term.

        Args:
            term_id: The starting term ID
            relationship_types: Types of relationships to follow (None = all)
            direction: Direction of traversal
            max_depth: Maximum traversal depth

        Returns:
            List of nodes and edges in the traversal
        """
        ...

    @abstractmethod
    async def find_paths(
        self,
        source_term_id: str,
        target_term_id: str,
        max_length: int = 5,
    ) -> list[list[dict]]:
        """Find all paths between two terms.

        Args:
            source_term_id: Starting term ID
            target_term_id: Ending term ID
            max_length: Maximum path length

        Returns:
            List of paths, each path is a list of nodes/edges
        """
        ...

    @abstractmethod
    async def get_community(
        self,
        term_id: str,
        algorithm: str = "louvain",
    ) -> list[dict]:
        """Get the community/cluster a term belongs to.

        Args:
            term_id: The term ID
            algorithm: Community detection algorithm

        Returns:
            List of terms in the same community
        """
        ...

    @abstractmethod
    async def sync_namespace(self, namespace_id: str, terms: list[dict], relationships: list[dict]) -> None:
        """Sync namespace terms and relationships to the graph.

        Args:
            namespace_id: The namespace identifier
            terms: List of term dictionaries
            relationships: List of relationship dictionaries
        """
        ...


class KnowledgeVectorRepository(ABC):
    """Vector-specific operations for semantic search (Phase 3).

    Implementations use Qdrant for vector similarity search.
    """

    @abstractmethod
    async def search_similar(
        self,
        embedding: list[float],
        namespace_ids: list[str],
        limit: int = 10,
        min_score: float = 0.7,
    ) -> list[tuple[Any, float]]:
        """Search terms by embedding similarity.

        Args:
            embedding: Query embedding vector
            namespace_ids: Namespaces to search in
            limit: Maximum number of results
            min_score: Minimum similarity score

        Returns:
            List of (term, score) tuples ordered by similarity
        """
        ...

    @abstractmethod
    async def update_embedding(
        self,
        term_id: str,
        namespace_id: str,
        embedding: list[float],
        metadata: dict | None = None,
    ) -> None:
        """Update the embedding for a term.

        Args:
            term_id: The term ID
            namespace_id: The namespace ID
            embedding: The embedding vector
            metadata: Optional metadata to store
        """
        ...

    @abstractmethod
    async def delete_embedding(self, term_id: str) -> None:
        """Delete the embedding for a term.

        Args:
            term_id: The term ID
        """
        ...
