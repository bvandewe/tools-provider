# Polyglot Entity Model Architecture

**Version:** 1.1.0
**Status:** `APPROVED`
**Date:** December 15, 2025

---

## 1. Executive Summary

This document defines the **Polyglot Entity Model** - a theoretical framework for extending Domain-Driven Design (DDD) to support **multi-dimensional entities** that exist simultaneously across multiple persistence paradigms.

### Related Documents

- **[Polyglot User/Agent Architecture](./polyglot-user-agent.md)** - Primary application of this model to User and Agent entities
- **[Event Sourcing Architecture](./event-sourcing.md)** - Base patterns for Temporal dimension

### Core Innovation

An Entity is redefined from a mono-dimensional state container to a **Stream Nexus**:

```
Entity = Σ Dimensions[(Stream_type, Projection_db)]
```

Each dimension evolves along its own axis of time and consistency, enabling:

- **Temporal persistence** (What happened?) → EventStoreDB → MongoDB
- **Intentional state** (What do we want?) → ResourceStream → Redis
- **Semantic relationships** (Where do I fit?) → RelationStream → Neo4j
- **Observational metrics** (How am I performing?) → TelemetryStream → InfluxDB

---

## 2. The Four Dimensions

### 2.1 Dimension Overview

| Dimension | Stream Type | Projection Target | Semantics | Versioning |
|-----------|-------------|-------------------|-----------|------------|
| **I. Temporal** | DomainStream | MongoDB | "What happened?" | `AggregateVersion` (v105) |
| **II. Intentional** | ResourceStream | Redis | "Spec vs Status?" | `SpecRevision` (gen-12) |
| **III. Semantic** | RelationStream | Neo4j | "Where do I fit?" | `GraphTopology` (rev-4) |
| **IV. Observational** | TelemetryStream | InfluxDB | "How am I doing?" | `Timestamp` |

### 2.2 Dimension I: Temporal (Standard DDD)

The immutable narrative of business events.

```python
# Existing pattern - unchanged
class UpstreamSource(AggregateRoot[UpstreamSourceState, str]):
    """Domain aggregate tracking business events."""

    def register(self, name: str, url: str, ...):
        self.state.on(
            self.register_event(
                SourceRegisteredDomainEvent(aggregate_id=self.id(), ...)
            )
        )
```

- **Stream**: `$domain-{EntityType}-{EntityId}` (via EventStoreDB)
- **Projection**: MongoDB collection (via `DomainEventHandler`)
- **Consistency**: Strong (aggregate boundary)

### 2.3 Dimension II: Intentional (Kubernetes Pattern)

Declarative intent with reconciliation loops.

```python
class ResourceSpec:
    """Desired state declaration."""
    target_state: str
    config: dict
    revision: int  # Incremented on spec change

class ResourceStatus:
    """Observed actual state."""
    current_state: str
    conditions: list[Condition]
    last_reconciled_at: datetime
    observed_revision: int  # Tracks which spec revision was reconciled
```

- **Stream**: `$resource-{EntityType}-{EntityId}` (via EventStoreDB)
- **Projection**: Redis hash (optimized for fast reads)
- **Reconciliation**: Hybrid (event-driven + optional polling)

### 2.4 Dimension III: Semantic (Graph Pattern)

Relationships and topology for traversal queries.

```python
class GraphNode:
    """Entity as a node in the knowledge graph."""
    entity_id: str
    entity_type: str
    labels: list[str]
    properties: dict

class GraphEdge:
    """Relationship between entities."""
    from_id: str
    to_id: str
    relation_type: str  # e.g., "BELONGS_TO", "ACCESSIBLE_BY"
    properties: dict
```

- **Stream**: `$relation-{EntityType}-{EntityId}` (via EventStoreDB)
- **Projection**: Neo4j nodes/edges (via `GraphProjectionHandler`)
- **Queries**: Cypher traversals (e.g., "Find all tools accessible by User X")

### 2.5 Dimension IV: Observational (Telemetry Pattern)

High-frequency metrics and indicators (future enhancement).

```python
class TelemetryEvent:
    """Performance observation."""
    entity_id: str
    metric_name: str
    value: float
    timestamp: datetime
    tags: dict
```

- **Stream**: `$telemetry-{EntityType}` (category stream)
- **Projection**: InfluxDB/Prometheus
- **Use Cases**: Session engagement, agent performance, tool latency

---

## 3. Multi-Axis Versioning

Each dimension maintains independent versioning:

```python
@dataclass
class EntityVersionVector:
    """Composite version across dimensions."""
    aggregate_version: int      # Sequence length of DomainStream
    spec_revision: int          # Revision count of ResourceSpec
    graph_topology_version: int # Version of edge relationships

    def to_dict(self) -> dict:
        return {
            "domain": f"v{self.aggregate_version}",
            "resource": f"gen-{self.spec_revision}",
            "graph": f"rev-{self.graph_topology_version}",
        }
```

**Key Principle**: Versions do not conflict across dimensions. A change in Intent (`SpecRevision`) does not invalidate History (`AggregateVersion`), though it may trigger a reconciliation command that results in a new Domain Event.

---

## 4. Aspect Composition Strategy

### 4.1 Delegation Pattern

Entities compose aspects via delegation, not inheritance:

```python
from dataclasses import dataclass, field
from typing import Generic, TypeVar, Optional

TState = TypeVar("TState")
TKey = TypeVar("TKey")


@dataclass
class ResourceAspect:
    """Intentional dimension aspect."""
    spec: dict = field(default_factory=dict)
    status: dict = field(default_factory=dict)
    spec_revision: int = 0

    def update_spec(self, new_spec: dict) -> "ResourceSpecUpdatedEvent":
        self.spec_revision += 1
        self.spec = new_spec
        return ResourceSpecUpdatedEvent(
            spec=new_spec,
            revision=self.spec_revision,
        )

    def update_status(self, new_status: dict) -> "ResourceStatusUpdatedEvent":
        self.status = new_status
        return ResourceStatusUpdatedEvent(
            status=new_status,
            observed_revision=self.spec_revision,
        )


@dataclass
class GraphNodeAspect:
    """Semantic dimension aspect."""
    labels: list[str] = field(default_factory=list)
    properties: dict = field(default_factory=dict)
    edges: list[dict] = field(default_factory=list)
    topology_version: int = 0

    def add_edge(self, target_id: str, relation_type: str, props: dict = None) -> "EdgeCreatedEvent":
        edge = {"target_id": target_id, "relation_type": relation_type, "properties": props or {}}
        self.edges.append(edge)
        self.topology_version += 1
        return EdgeCreatedEvent(edge=edge, topology_version=self.topology_version)


class MultiDimensionalAggregate(AggregateRoot[TState, TKey], Generic[TState, TKey]):
    """Base class for polyglot entities with optional aspects."""

    def __init__(self):
        super().__init__()
        self._resource: Optional[ResourceAspect] = None
        self._graph_node: Optional[GraphNodeAspect] = None

    @property
    def resource(self) -> Optional[ResourceAspect]:
        """Access Intentional dimension if enabled."""
        return self._resource

    @property
    def graph_node(self) -> Optional[GraphNodeAspect]:
        """Access Semantic dimension if enabled."""
        return self._graph_node

    def enable_resource_aspect(self, initial_spec: dict = None) -> None:
        """Opt-in to Intentional dimension."""
        self._resource = ResourceAspect(spec=initial_spec or {})

    def enable_graph_aspect(self, labels: list[str] = None) -> None:
        """Opt-in to Semantic dimension."""
        self._graph_node = GraphNodeAspect(labels=labels or [])

    def get_version_vector(self) -> EntityVersionVector:
        """Get composite version across all enabled dimensions."""
        return EntityVersionVector(
            aggregate_version=len(self._pending_events) if hasattr(self, '_pending_events') else 0,
            spec_revision=self._resource.spec_revision if self._resource else 0,
            graph_topology_version=self._graph_node.topology_version if self._graph_node else 0,
        )
```

### 4.2 Declarative Entity Definition

Developers define entities by composing aspects:

```python
class UpstreamSource(MultiDimensionalAggregate[UpstreamSourceState, str]):
    """Upstream source with Resource and Graph aspects."""

    def __init__(self, name: str, url: str, ...):
        super().__init__()

        # Enable Intentional dimension for reconciliation
        self.enable_resource_aspect(initial_spec={
            "target_health": "healthy",
            "sync_interval_minutes": 15,
        })

        # Enable Semantic dimension for relationship tracking
        self.enable_graph_aspect(labels=["Source", "OpenAPI"])

        # Standard domain event
        self.state.on(
            self.register_event(
                SourceRegisteredDomainEvent(...)
            )
        )
```

---

## 5. Event Stream Topology

### 5.1 Hybrid Stream Architecture

DomainEvents remain the **source of truth**. Other dimension streams are **derived** but maintained separately for query optimization:

```
EventStoreDB Streams:
├── $domain-UpstreamSource-{id}     # Primary (DomainEvents)
├── $resource-UpstreamSource-{id}   # Derived (ResourceEvents)
├── $relation-UpstreamSource-{id}   # Derived (RelationEvents)
└── $ce-domain                      # Category stream (all domain events)
```

### 5.2 Cross-Dimension Event Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                        DomainEvent                                │
│                    (Source of Truth)                              │
└──────────────────────┬───────────────────────────────────────────┘
                       │ Mediator.publish()
                       ▼
          ┌────────────┴────────────┐
          │                         │
          ▼                         ▼
┌─────────────────────┐   ┌─────────────────────┐
│ DomainEventHandler  │   │ ResourceAspectHandler│
│ (MongoDB Projection)│   │ (Redis Projection)   │
└─────────────────────┘   └──────────┬──────────┘
                                     │ Emits ResourceEvent
                                     ▼
                          ┌─────────────────────┐
                          │ ReconciliationHandler│
                          │ (Detects Drift)      │
                          └──────────┬──────────┘
                                     │ Issues Command
                                     ▼
                          ┌─────────────────────┐
                          │ New DomainEvent     │
                          │ (Closes Loop)       │
                          └─────────────────────┘
```

---

## 6. Reconciliation Architecture

### 6.1 Hybrid Trigger Model

Reconciliators support both event-driven and optional polling:

```python
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

TEntity = TypeVar("TEntity")


class Reconciliator(ABC, Generic[TEntity]):
    """Base class for aspect reconciliation controllers."""

    # Event-driven: Called when ResourceSpecUpdated is published
    @abstractmethod
    async def on_spec_updated(self, entity_id: str, new_spec: dict) -> None:
        """React to spec changes immediately."""
        pass

    # Polling (optional): Called periodically by background worker
    @abstractmethod
    async def reconcile(self, entity: TEntity) -> ReconciliationResult:
        """Compare spec vs status and issue corrective commands."""
        pass

    @property
    def polling_enabled(self) -> bool:
        """Override to enable periodic reconciliation."""
        return False

    @property
    def polling_interval_seconds(self) -> int:
        """Override to set polling frequency."""
        return 60


class UpstreamSourceReconciliator(Reconciliator[UpstreamSource]):
    """Reconciles upstream sources: health checks, inventory sync."""

    @property
    def polling_enabled(self) -> bool:
        return True  # Health checks require polling

    @property
    def polling_interval_seconds(self) -> int:
        return 300  # 5 minutes

    async def on_spec_updated(self, entity_id: str, new_spec: dict) -> None:
        # Immediate action: trigger inventory sync if URL changed
        if "url" in new_spec:
            await self._mediator.send(RefreshInventoryCommand(source_id=entity_id))

    async def reconcile(self, entity: UpstreamSource) -> ReconciliationResult:
        spec = entity.resource.spec
        status = entity.resource.status

        # Check health drift
        if spec.get("target_health") == "healthy" and status.get("current_health") != "healthy":
            # Issue corrective command
            await self._mediator.send(CheckSourceHealthCommand(source_id=entity.id()))

        return ReconciliationResult(reconciled=True)
```

### 6.2 Reconciliator Registry

```python
class ReconciliatorRegistry:
    """Manages reconciliators for all entity types."""

    def __init__(self):
        self._reconciliators: dict[type, Reconciliator] = {}

    def register(self, entity_type: type, reconciliator: Reconciliator) -> None:
        self._reconciliators[entity_type] = reconciliator

    def get_polling_reconciliators(self) -> list[Reconciliator]:
        return [r for r in self._reconciliators.values() if r.polling_enabled]
```

---

## 7. Graph Projection Architecture

### 7.1 Neo4j Integration

```python
from neo4j import AsyncGraphDatabase


class GraphProjectionHandler(DomainEventHandler[SourceRegisteredDomainEvent]):
    """Projects domain events to Neo4j graph."""

    def __init__(self, neo4j_driver: AsyncGraphDatabase.driver):
        self._driver = neo4j_driver

    async def handle_async(self, event: SourceRegisteredDomainEvent) -> None:
        async with self._driver.session() as session:
            await session.run(
                """
                MERGE (s:Source {id: $id})
                SET s.name = $name, s.url = $url, s.source_type = $source_type
                """,
                id=event.aggregate_id,
                name=event.name,
                url=event.url,
                source_type=event.source_type.value,
            )


class ToolGroupMembershipHandler(DomainEventHandler[ExplicitToolAddedDomainEvent]):
    """Projects tool-group relationships to Neo4j."""

    async def handle_async(self, event: ExplicitToolAddedDomainEvent) -> None:
        async with self._driver.session() as session:
            await session.run(
                """
                MATCH (g:ToolGroup {id: $group_id})
                MATCH (t:Tool {id: $tool_id})
                MERGE (t)-[:BELONGS_TO]->(g)
                """,
                group_id=event.aggregate_id,
                tool_id=event.tool_id,
            )
```

### 7.2 Graph Query Service

```python
class GraphQueryService:
    """Semantic queries across the knowledge graph."""

    async def get_accessible_tools_for_user(self, user_claims: dict) -> list[str]:
        """Traverse: User claims → Policies → Groups → Tools."""
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (p:Policy)-[:ALLOWS]->(g:ToolGroup)<-[:BELONGS_TO]-(t:Tool)
                WHERE p.claim_path IN $claim_paths
                RETURN DISTINCT t.id as tool_id
                """,
                claim_paths=list(user_claims.keys()),
            )
            return [record["tool_id"] async for record in result]
```

---

## 8. Entity Mapping to Dimensions

### 8.1 Primary Use Case: User and Agent Entities

The **User** and **Agent** entities are the primary candidates for Polyglot extension, enabling stateful, context-aware AI interactions. See [Polyglot User/Agent Architecture](./polyglot-user-agent.md) for detailed design.

| Entity | Temporal | Intentional | Semantic | Observational |
|--------|----------|-------------|----------|---------------|
| **User** | ✅ Profile history | ✅ Goals/Plans (primary) | ✅ Skills/Relationships | ✅ Session telemetry |
| **Agent** | ✅ Interaction history | ✅ Operational targets | ✅ User assignments | ✅ Performance metrics |
| **Session** | ✅ Already | ✅ Mode/Goals | ✅ User→Agent graph | ✅ Engagement |

### 8.2 Future Extension: Tools Provider Entities

These entities may benefit from Polyglot extension in future iterations:

| Entity | Temporal | Intentional | Semantic | Observational |
|--------|----------|-------------|----------|---------------|
| **UpstreamSource** | ✅ Already | 🔮 Health spec | 🔮 Source node | 🔮 Latency |
| **SourceTool** | ✅ Already | 🔮 Enable spec | 🔮 Tool edges | 🔮 Call count |
| **ToolGroup** | ✅ Already | 🔮 Selector spec | 🔮 Group node | ❌ N/A |
| **AccessPolicy** | ✅ Already | 🔮 Active spec | 🔮 Policy edges | ❌ N/A |

---

## 9. Confidence Assessment

| Aspect | Score | Notes |
|--------|-------|-------|
| **Feasibility** | 0.88 | Individual components are mature; integration complexity is manageable |
| **Backward Compatibility** | 0.95 | Existing aggregates can be extended without breaking changes |
| **Developer Experience** | 0.85 | Aspect composition simplifies boilerplate; requires learning curve |
| **Neuroglia Extension** | 0.75 | Mediator adaptation for cross-dimension routing requires framework changes |

---

## 10. References

- [Polyglot User/Agent Architecture](./polyglot-user-agent.md) - Primary application
- [Polyglot Entity Model Specification](https://gist.github.com/bvandewe/95db93a4c4cb307d6b16e841e7df5877)
- [AI-Augmented Learning Session](https://gist.github.com/bvandewe/7011d1a183f85d9064d1a44316cc0cc8)
- [Event Sourcing Architecture](./event-sourcing.md)
- [CQRS Pattern](./cqrs-pattern.md)
