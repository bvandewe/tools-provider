# Knowledge Manager - Vector Embeddings

## Architecture: Abstraction Layer for Swappable Backends

The embedding system uses an **abstraction layer** enabling easy swap of implementations via dependency injection. All implementations conform to `VectorStore` and `EmbeddingProvider` protocols.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EMBEDDING ABSTRACTION LAYER                          │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                      VectorStore Protocol                                ││
│  │  - store(id, embedding, metadata, revision)                              ││
│  │  - search(embedding, filters, limit)                                     ││
│  │  - get_revisions(entity_id) → temporal history                          ││
│  │  - search_at_revision(embedding, revision_timestamp)                     ││
│  └───────────────────────────────┬─────────────────────────────────────────┘│
│                                  │                                           │
│           ┌──────────────────────┼──────────────────────┐                   │
│           │                      │                      │                   │
│           ▼                      ▼                      ▼                   │
│  ┌────────────────┐   ┌────────────────┐   ┌────────────────┐              │
│  │  QdrantStore   │   │ MongoAtlasStore│   │   Neo4jStore   │              │
│  │  (Base Impl)   │   │  (Alternative) │   │  (Graph+Vector)│              │
│  └────────────────┘   └────────────────┘   └────────────────┘              │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                   EmbeddingProvider Protocol                             ││
│  │  - embed(text) → list[float]                                             ││
│  │  - embed_batch(texts) → list[list[float]]                               ││
│  │  - dimensions: int                                                       ││
│  └───────────────────────────────┬─────────────────────────────────────────┘│
│                                  │                                           │
│           ┌──────────────────────┼──────────────────────┐                   │
│           │                      │                      │                   │
│           ▼                      ▼                      ▼                   │
│  ┌────────────────┐   ┌────────────────┐   ┌────────────────┐              │
│  │LocalTransformers│   │ OpenAI API    │   │  Custom Model  │              │
│  │  (Primary)      │   │ (Cloud backup)│   │  (Future)      │              │
│  └────────────────┘   └────────────────┘   └────────────────┘              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Protocols (Interfaces)

```python
# domain/protocols/embedding_protocols.py

from typing import Protocol, TypedDict
from datetime import datetime

class VectorMetadata(TypedDict, total=False):
    """Metadata stored alongside vectors."""
    entity_type: str          # "Concept", "Skill", "Blueprint", "User"
    entity_id: str
    namespace_id: str
    tenant_id: str
    revision: int             # Version number for temporal tracking
    revision_timestamp: datetime
    source_event_id: str      # DomainEvent that triggered this embedding
    labels: dict[str, str]    # Arbitrary key-value labels


class VectorSearchResult(TypedDict):
    """Result from vector similarity search."""
    id: str
    score: float
    metadata: VectorMetadata
    revision: int


class EmbeddingProvider(Protocol):
    """Protocol for embedding text into vectors."""

    @property
    def dimensions(self) -> int:
        """Return the dimensionality of embeddings."""
        ...

    async def embed(self, text: str) -> list[float]:
        """Embed a single text."""
        ...

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts efficiently."""
        ...


class VectorStore(Protocol):
    """Protocol for vector storage backends."""

    async def store(
        self,
        entity_id: str,
        embedding: list[float],
        metadata: VectorMetadata,
    ) -> str:
        """Store embedding with automatic revision increment."""
        ...

    async def search(
        self,
        embedding: list[float],
        filters: dict | None = None,
        limit: int = 10,
        min_score: float = 0.7,
    ) -> list[VectorSearchResult]:
        """Search for similar vectors."""
        ...

    async def get_revisions(
        self,
        entity_id: str,
    ) -> list[VectorSearchResult]:
        """Get all revisions of an entity's embedding (temporal history)."""
        ...

    async def search_at_revision(
        self,
        embedding: list[float],
        as_of: datetime,
        filters: dict | None = None,
        limit: int = 10,
    ) -> list[VectorSearchResult]:
        """Time-travel search: find similar vectors as they existed at a point in time."""
        ...

    async def delete_entity(self, entity_id: str, keep_history: bool = True) -> int:
        """Delete entity embeddings. If keep_history=True, mark as deleted but preserve revisions."""
        ...
```

## Embedding Strategy

### Local Model (Primary)

Using Sentence Transformers for local inference:

```python
# infrastructure/services/local_embedding_provider.py

import asyncio
from sentence_transformers import SentenceTransformer
from domain.protocols.embedding_protocols import EmbeddingProvider

class LocalEmbeddingProvider(EmbeddingProvider):
    """Local embedding using Sentence Transformers."""

    MODEL_NAME = "all-MiniLM-L6-v2"  # 384 dimensions, fast

    def __init__(self):
        self._model = SentenceTransformer(self.MODEL_NAME)

    @property
    def dimensions(self) -> int:
        return 384

    async def embed(self, text: str) -> list[float]:
        # Run in thread pool to avoid blocking
        result = await asyncio.to_thread(
            self._model.encode, text, convert_to_numpy=True
        )
        return result.tolist()

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        results = await asyncio.to_thread(
            self._model.encode, texts, convert_to_numpy=True
        )
        return [r.tolist() for r in results]
```

### Model Selection

| Model | Dimensions | Speed | Quality |
|-------|------------|-------|---------|
| all-MiniLM-L6-v2 | 384 | Fast | Good |
| all-mpnet-base-v2 | 768 | Medium | Better |
| instructor-large | 768 | Slow | Best |

## Vector Storage

### Qdrant (Base Implementation)

Qdrant is the **primary implementation** with full support for temporal revisions:

```python
# infrastructure/repositories/qdrant_vector_store.py

from datetime import datetime, timezone
from uuid import uuid4
from qdrant_client import QdrantClient, AsyncQdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, Filter, FieldCondition,
    MatchValue, Range, PayloadSchemaType
)
from domain.protocols.embedding_protocols import VectorStore, VectorMetadata, VectorSearchResult


class QdrantVectorStore(VectorStore):
    """Qdrant implementation of VectorStore with temporal versioning.

    Each entity can have multiple points (one per revision).
    Point IDs are UUIDs; entity_id is stored in payload for grouping.
    """

    def __init__(self, url: str, collection_name: str = "knowledge_vectors", dimensions: int = 384):
        self._client = AsyncQdrantClient(url=url)
        self._collection_name = collection_name
        self._dimensions = dimensions

    async def initialize(self) -> None:
        """Ensure collection exists with proper schema."""
        await self._client.recreate_collection(
            collection_name=self._collection_name,
            vectors_config=VectorParams(
                size=self._dimensions,
                distance=Distance.COSINE,
            ),
        )
        # Create payload indexes for efficient filtering
        await self._client.create_payload_index(
            collection_name=self._collection_name,
            field_name="entity_id",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        await self._client.create_payload_index(
            collection_name=self._collection_name,
            field_name="namespace_id",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        await self._client.create_payload_index(
            collection_name=self._collection_name,
            field_name="revision",
            field_schema=PayloadSchemaType.INTEGER,
        )
        await self._client.create_payload_index(
            collection_name=self._collection_name,
            field_name="revision_timestamp",
            field_schema=PayloadSchemaType.DATETIME,
        )
        await self._client.create_payload_index(
            collection_name=self._collection_name,
            field_name="is_current",
            field_schema=PayloadSchemaType.BOOL,
        )

    async def store(
        self,
        entity_id: str,
        embedding: list[float],
        metadata: VectorMetadata,
    ) -> str:
        """Store embedding with automatic revision increment."""
        # Get current max revision for this entity
        existing = await self._client.scroll(
            collection_name=self._collection_name,
            scroll_filter=Filter(
                must=[FieldCondition(key="entity_id", match=MatchValue(value=entity_id))]
            ),
            limit=1000,
            with_payload=True,
        )

        # Calculate next revision
        current_revisions = [p.payload.get("revision", 0) for p in existing[0]]
        next_revision = max(current_revisions, default=0) + 1

        # Mark all existing as not current
        if existing[0]:
            await self._client.set_payload(
                collection_name=self._collection_name,
                payload={"is_current": False},
                points=[p.id for p in existing[0]],
            )

        # Create new point with revision
        point_id = str(uuid4())
        now = datetime.now(timezone.utc)

        payload = {
            **metadata,
            "entity_id": entity_id,
            "revision": next_revision,
            "revision_timestamp": now.isoformat(),
            "is_current": True,
        }

        await self._client.upsert(
            collection_name=self._collection_name,
            points=[PointStruct(
                id=point_id,
                vector=embedding,
                payload=payload,
            )],
        )
        return point_id

    async def search(
        self,
        embedding: list[float],
        filters: dict | None = None,
        limit: int = 10,
        min_score: float = 0.7,
    ) -> list[VectorSearchResult]:
        """Search current (latest) vectors only."""
        filter_conditions = [
            FieldCondition(key="is_current", match=MatchValue(value=True))
        ]

        if filters:
            if "namespace_ids" in filters:
                filter_conditions.append(
                    FieldCondition(key="namespace_id", match=MatchValue(value=filters["namespace_ids"]))
                )
            if "entity_type" in filters:
                filter_conditions.append(
                    FieldCondition(key="entity_type", match=MatchValue(value=filters["entity_type"]))
                )

        results = await self._client.search(
            collection_name=self._collection_name,
            query_vector=embedding,
            query_filter=Filter(must=filter_conditions),
            limit=limit,
            score_threshold=min_score,
        )

        return [
            VectorSearchResult(
                id=str(r.id),
                score=r.score,
                metadata=r.payload,
                revision=r.payload.get("revision", 1),
            )
            for r in results
        ]

    async def get_revisions(self, entity_id: str) -> list[VectorSearchResult]:
        """Get all revisions of an entity's embedding (temporal history)."""
        results, _ = await self._client.scroll(
            collection_name=self._collection_name,
            scroll_filter=Filter(
                must=[FieldCondition(key="entity_id", match=MatchValue(value=entity_id))]
            ),
            limit=1000,
            with_payload=True,
            with_vectors=False,
        )

        return sorted(
            [
                VectorSearchResult(
                    id=str(p.id),
                    score=1.0,  # Not a similarity search
                    metadata=p.payload,
                    revision=p.payload.get("revision", 1),
                )
                for p in results
            ],
            key=lambda x: x["revision"],
        )

    async def search_at_revision(
        self,
        embedding: list[float],
        as_of: datetime,
        filters: dict | None = None,
        limit: int = 10,
    ) -> list[VectorSearchResult]:
        """Time-travel search: find the latest revision of each entity as of a timestamp."""
        # First, get all entities that existed at this time
        filter_conditions = [
            FieldCondition(
                key="revision_timestamp",
                range=Range(lte=as_of.isoformat()),
            )
        ]
        if filters:
            if "namespace_ids" in filters:
                filter_conditions.append(
                    FieldCondition(key="namespace_id", match=MatchValue(value=filters["namespace_ids"]))
                )

        results = await self._client.search(
            collection_name=self._collection_name,
            query_vector=embedding,
            query_filter=Filter(must=filter_conditions),
            limit=limit * 5,  # Over-fetch to filter by max revision per entity
        )

        # Group by entity_id and keep only max revision per entity
        entity_max_revision: dict[str, VectorSearchResult] = {}
        for r in results:
            entity_id = r.payload.get("entity_id")
            revision = r.payload.get("revision", 1)

            if entity_id not in entity_max_revision or revision > entity_max_revision[entity_id]["revision"]:
                entity_max_revision[entity_id] = VectorSearchResult(
                    id=str(r.id),
                    score=r.score,
                    metadata=r.payload,
                    revision=revision,
                )

        return sorted(
            list(entity_max_revision.values()),
            key=lambda x: x["score"],
            reverse=True,
        )[:limit]

    async def delete_entity(self, entity_id: str, keep_history: bool = True) -> int:
        """Delete entity embeddings."""
        if keep_history:
            # Soft delete: mark as deleted but preserve revisions
            results, _ = await self._client.scroll(
                collection_name=self._collection_name,
                scroll_filter=Filter(
                    must=[FieldCondition(key="entity_id", match=MatchValue(value=entity_id))]
                ),
                limit=1000,
            )
            if results:
                await self._client.set_payload(
                    collection_name=self._collection_name,
                    payload={"is_deleted": True, "is_current": False},
                    points=[p.id for p in results],
                )
            return len(results)
        else:
            # Hard delete
            result = await self._client.delete(
                collection_name=self._collection_name,
                points_selector=Filter(
                    must=[FieldCondition(key="entity_id", match=MatchValue(value=entity_id))]
                ),
            )
            return result.status
```

### MongoDB Atlas Alternative

```python
# infrastructure/repositories/mongo_atlas_vector_store.py

from motor.motor_asyncio import AsyncIOMotorClient
from domain.protocols.embedding_protocols import VectorStore, VectorMetadata, VectorSearchResult

class MongoAtlasVectorStore(VectorStore):
    """MongoDB Atlas Vector Search implementation with temporal versioning."""

    def __init__(self, connection_string: str, database: str, collection: str = "knowledge_vectors"):
        self._client = AsyncIOMotorClient(connection_string)
        self._db = self._client[database]
        self._collection = self._db[collection]

    async def search(
        self,
        embedding: list[float],
        filters: dict | None = None,
        limit: int = 10,
        min_score: float = 0.7,
    ) -> list[VectorSearchResult]:
        """Search using $vectorSearch aggregation."""
        pre_filter = {"is_current": True}
        if filters:
            if "namespace_ids" in filters:
                pre_filter["namespace_id"] = {"$in": filters["namespace_ids"]}
            if "entity_type" in filters:
                pre_filter["entity_type"] = filters["entity_type"]

        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index",
                    "path": "embedding",
                    "queryVector": embedding,
                    "numCandidates": limit * 10,
                    "limit": limit,
                    "filter": pre_filter,
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "entity_id": 1,
                    "metadata": 1,
                    "revision": 1,
                    "score": {"$meta": "vectorSearchScore"},
                }
            },
        ]

        results = await self._collection.aggregate(pipeline).to_list(limit)
        return [
            VectorSearchResult(
                id=str(r["_id"]),
                score=r["score"],
                metadata=r.get("metadata", {}),
                revision=r.get("revision", 1),
            )
            for r in results
            if r["score"] >= min_score
        ]

    async def search_at_revision(
        self,
        embedding: list[float],
        as_of: datetime,
        filters: dict | None = None,
        limit: int = 10,
    ) -> list[VectorSearchResult]:
        """Time-travel: aggregate to find max revision per entity before timestamp."""
        pipeline = [
            # Filter by timestamp
            {"$match": {"revision_timestamp": {"$lte": as_of}}},
            # Group by entity, keep max revision
            {"$sort": {"revision": -1}},
            {"$group": {
                "_id": "$entity_id",
                "doc": {"$first": "$$ROOT"},
            }},
            {"$replaceRoot": {"newRoot": "$doc"}},
            # Vector search on the subset
            {
                "$vectorSearch": {
                    "index": "vector_index",
                    "path": "embedding",
                    "queryVector": embedding,
                    "numCandidates": limit * 5,
                    "limit": limit,
                }
            },
        ]
        results = await self._collection.aggregate(pipeline).to_list(limit)
        return [self._to_result(r) for r in results]
```

### Neo4j Vector Store (Graph + Vector Unified)

```python
# infrastructure/repositories/neo4j_vector_store.py

from neo4j import AsyncGraphDatabase
from domain.protocols.embedding_protocols import VectorStore, VectorMetadata, VectorSearchResult

class Neo4jVectorStore(VectorStore):
    """Neo4j 5.x native vector search with graph relationships.

    Best for queries that combine semantic similarity with graph traversal.
    """

    def __init__(self, uri: str, auth: tuple[str, str], database: str = "neo4j"):
        self._driver = AsyncGraphDatabase.driver(uri, auth=auth)
        self._database = database

    async def store(
        self,
        entity_id: str,
        embedding: list[float],
        metadata: VectorMetadata,
    ) -> str:
        """Store embedding as node property with revision tracking."""
        query = """
        MATCH (e {id: $entity_id})
        SET e.embedding = $embedding,
            e.embedding_revision = COALESCE(e.embedding_revision, 0) + 1,
            e.embedding_timestamp = datetime()

        // Create revision history node
        CREATE (h:EmbeddingRevision {
            entity_id: $entity_id,
            revision: e.embedding_revision,
            embedding: $embedding,
            timestamp: datetime(),
            source_event_id: $source_event_id
        })
        CREATE (e)-[:HAS_EMBEDDING_REVISION]->(h)

        RETURN e.id as id, e.embedding_revision as revision
        """
        async with self._driver.session(database=self._database) as session:
            result = await session.run(
                query,
                entity_id=entity_id,
                embedding=embedding,
                source_event_id=metadata.get("source_event_id", ""),
            )
            record = await result.single()
            return record["id"]

    async def search(
        self,
        embedding: list[float],
        filters: dict | None = None,
        limit: int = 10,
        min_score: float = 0.7,
    ) -> list[VectorSearchResult]:
        """Hybrid search: vector similarity + graph filters."""
        query = """
        CALL db.index.vector.queryNodes('entity_embedding_idx', $limit, $embedding)
        YIELD node, score
        WHERE score >= $min_score
        RETURN node.id as id, score,
               node.entity_type as entity_type,
               node.namespace_id as namespace_id,
               node.embedding_revision as revision
        ORDER BY score DESC
        """
        async with self._driver.session(database=self._database) as session:
            result = await session.run(
                query, embedding=embedding, limit=limit, min_score=min_score
            )
            records = await result.data()
            return [self._to_result(r) for r in records]

    async def search_with_graph_context(
        self,
        embedding: list[float],
        user_id: str,
        limit: int = 10,
    ) -> list[VectorSearchResult]:
        """Vector search enriched with user's mastery context."""
        query = """
        CALL db.index.vector.queryNodes('concept_embedding_idx', $limit * 2, $embedding)
        YIELD node AS concept, score

        // Enrich with user context
        OPTIONAL MATCH (u:User {id: $user_id})-[mastery:MASTERED]->(concept)
        OPTIONAL MATCH (u)-[struggle:STRUGGLING_WITH]->(concept)
        OPTIONAL MATCH (prereq:Concept)-[:PREREQUISITE_FOR]->(concept)
        OPTIONAL MATCH (u)-[prereq_mastery:MASTERED]->(prereq)

        RETURN concept.id as id,
               score,
               concept.name as name,
               CASE WHEN mastery IS NOT NULL THEN 'mastered'
                    WHEN struggle IS NOT NULL THEN 'struggling'
                    ELSE 'unknown' END as user_status,
               collect(DISTINCT prereq.name) as prerequisites,
               count(DISTINCT prereq_mastery) as prereqs_mastered
        ORDER BY score DESC
        LIMIT $limit
        """
        async with self._driver.session(database=self._database) as session:
            result = await session.run(
                query, embedding=embedding, user_id=user_id, limit=limit
            )
            return await result.data()
```

## Dependency Injection Registration

```python
# main.py - Registering implementations

from infrastructure.repositories.qdrant_vector_store import QdrantVectorStore
from infrastructure.services.local_embedding_provider import LocalEmbeddingProvider
from domain.protocols.embedding_protocols import VectorStore, EmbeddingProvider

def configure_embeddings(builder: ServiceBuilder):
    """Register embedding services with the DI container."""

    # Register embedding provider (swappable)
    builder.services.add_singleton(
        EmbeddingProvider,
        lambda sp: LocalEmbeddingProvider()
    )

    # Register vector store (swappable - Qdrant is default)
    builder.services.add_singleton(
        VectorStore,
        lambda sp: QdrantVectorStore(
            url=sp.get_required_service(Settings).qdrant_url,
            collection_name="knowledge_vectors",
            dimensions=384,
        )
    )

    # Alternative: Swap to MongoDB Atlas
    # builder.services.add_singleton(
    #     VectorStore,
    #     lambda sp: MongoAtlasVectorStore(
    #         connection_string=sp.get_required_service(Settings).mongo_uri,
    #         database="knowledge",
    #     )
    # )
```

## Temporal Embedding Pipeline

```
DomainEvent (Entity Created/Updated)
        │
        ▼
┌────────────────────────────────────┐
│  Event Handler (CloudEvent)         │
│  - Extracts entity text content     │
│  - Includes event metadata          │
└─────────────┬──────────────────────┘
              │
              ▼
┌────────────────────────────────────┐
│  EmbeddingProvider.embed()          │
│  - LocalTransformers (primary)      │
│  - Generates 384-dim vector         │
└─────────────┬──────────────────────┘
              │
              ▼
┌────────────────────────────────────┐
│  VectorStore.store()                │
│  - Auto-increments revision         │
│  - Preserves revision history       │
│  - Links to source DomainEvent      │
└─────────────┬──────────────────────┘
              │
              ▼
┌────────────────────────────────────┐
│  Entity now searchable with:        │
│  - Current state similarity         │
│  - Historical state time-travel     │
│  - Revision audit trail             │
└────────────────────────────────────┘
```

## Temporal Query Examples

```python
# Query: Find similar concepts as they existed 3 months ago
results = await vector_store.search_at_revision(
    embedding=await embedding_provider.embed("machine learning"),
    as_of=datetime.now() - timedelta(days=90),
    filters={"entity_type": "Concept", "namespace_ids": ["ai-fundamentals"]},
    limit=10,
)

# Query: Get the evolution of a concept's embedding over time
revisions = await vector_store.get_revisions(entity_id="concept-ml-101")
for rev in revisions:
    print(f"Revision {rev['revision']} at {rev['metadata']['revision_timestamp']}")

# Query: Compare semantic drift - how much has "DevOps" changed meaning?
old_embedding = revisions[0].embedding  # First version
current_embedding = revisions[-1].embedding  # Latest
semantic_drift = 1 - cosine_similarity(old_embedding, current_embedding)
```

---

_Next: [07-versioning.md](07-versioning.md) - Namespace Versioning_
