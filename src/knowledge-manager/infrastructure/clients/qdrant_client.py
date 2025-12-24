"""Qdrant vector database client for semantic search (Phase 3 scaffold)."""

import logging
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

log = logging.getLogger(__name__)


class QdrantVectorClient:
    """Qdrant client for vector similarity search.

    This is a Phase 3 scaffold - full implementation will include:
    - Term embedding generation and storage
    - Semantic similarity search
    - Multi-namespace vector queries
    - Embedding model abstraction (swappable backends)
    """

    def __init__(
        self,
        url: str,
        api_key: str | None = None,
        embedding_dimension: int = 384,
    ):
        """Initialize Qdrant client.

        Args:
            url: Qdrant server URL
            api_key: Optional API key
            embedding_dimension: Vector dimension size
        """
        self._client: AsyncQdrantClient | None = None
        self._url = url
        self._api_key = api_key
        self._embedding_dimension = embedding_dimension

    async def connect(self) -> None:
        """Establish connection to Qdrant."""
        log.info(f"Connecting to Qdrant at {self._url}")
        self._client = AsyncQdrantClient(
            url=self._url,
            api_key=self._api_key,
        )
        log.info("Qdrant connection established")

    async def close(self) -> None:
        """Close Qdrant connection."""
        if self._client:
            await self._client.close()
            self._client = None
            log.info("Qdrant connection closed")

    async def health_check(self) -> bool:
        """Check Qdrant connectivity.

        Returns:
            True if healthy
        """
        if not self._client:
            return False
        try:
            # Just check if we can list collections
            await self._client.get_collections()
            return True
        except Exception as e:
            log.error(f"Qdrant health check failed: {e}")
            return False

    async def ensure_collection(self, collection_name: str) -> bool:
        """Ensure a collection exists.

        Args:
            collection_name: Name of collection

        Returns:
            True if collection exists or was created
        """
        if not self._client:
            raise RuntimeError("Qdrant not connected")

        try:
            collections = await self._client.get_collections()
            existing = [c.name for c in collections.collections]

            if collection_name not in existing:
                await self._client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=self._embedding_dimension,
                        distance=Distance.COSINE,
                    ),
                )
                log.info(f"Created Qdrant collection: {collection_name}")

            return True
        except Exception as e:
            log.error(f"Failed to ensure collection {collection_name}: {e}")
            return False

    # =========================================================================
    # Phase 3: Vector Operations (Scaffold)
    # =========================================================================

    async def upsert_term_embedding(
        self,
        collection_name: str,
        term_id: str,
        namespace_id: str,
        embedding: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Upsert a term embedding.

        Args:
            collection_name: Target collection
            term_id: Term identifier
            namespace_id: Namespace identifier
            embedding: Vector embedding
            metadata: Additional metadata

        Returns:
            True if successful
        """
        if not self._client:
            raise RuntimeError("Qdrant not connected")

        try:
            payload = {
                "term_id": term_id,
                "namespace_id": namespace_id,
                **(metadata or {}),
            }

            await self._client.upsert(
                collection_name=collection_name,
                points=[
                    PointStruct(
                        id=term_id,
                        vector=embedding,
                        payload=payload,
                    )
                ],
            )
            return True
        except Exception as e:
            log.error(f"Failed to upsert embedding for {term_id}: {e}")
            return False

    async def search_similar_terms(
        self,
        collection_name: str,
        query_embedding: list[float],
        namespace_id: str | None = None,
        limit: int = 10,
        score_threshold: float = 0.7,
    ) -> list[dict[str, Any]]:
        """Search for similar terms by vector.

        Args:
            collection_name: Collection to search
            query_embedding: Query vector
            namespace_id: Optional namespace filter
            limit: Maximum results
            score_threshold: Minimum similarity score

        Returns:
            List of matching terms with scores
        """
        if not self._client:
            raise RuntimeError("Qdrant not connected")

        try:
            # Build filter if namespace specified
            query_filter = None
            if namespace_id:
                query_filter = Filter(
                    must=[
                        FieldCondition(
                            key="namespace_id",
                            match=MatchValue(value=namespace_id),
                        )
                    ]
                )

            results = await self._client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                query_filter=query_filter,
                limit=limit,
                score_threshold=score_threshold,
            )

            return [
                {
                    "term_id": hit.id,
                    "score": hit.score,
                    **hit.payload,
                }
                for hit in results
            ]
        except Exception as e:
            log.error(f"Vector search failed: {e}")
            return []

    async def delete_term_embedding(
        self,
        collection_name: str,
        term_id: str,
    ) -> bool:
        """Delete a term embedding.

        Args:
            collection_name: Collection name
            term_id: Term identifier

        Returns:
            True if successful
        """
        if not self._client:
            raise RuntimeError("Qdrant not connected")

        try:
            await self._client.delete(
                collection_name=collection_name,
                points_selector=[term_id],
            )
            return True
        except Exception as e:
            log.error(f"Failed to delete embedding for {term_id}: {e}")
            return False

    async def get_namespace_embeddings_count(
        self,
        collection_name: str,
        namespace_id: str,
    ) -> int:
        """Get count of embeddings in a namespace.

        Args:
            collection_name: Collection name
            namespace_id: Namespace identifier

        Returns:
            Count of embeddings
        """
        if not self._client:
            raise RuntimeError("Qdrant not connected")

        try:
            result = await self._client.count(
                collection_name=collection_name,
                count_filter=Filter(
                    must=[
                        FieldCondition(
                            key="namespace_id",
                            match=MatchValue(value=namespace_id),
                        )
                    ]
                ),
            )
            return result.count
        except Exception as e:
            log.error(f"Failed to count embeddings: {e}")
            return 0
