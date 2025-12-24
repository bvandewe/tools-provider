# Knowledge Manager - Implementation Plan

## Phase Overview

| Phase | Duration | Focus |
|-------|----------|-------|
| **Foundation** | | |
| 1 | 2 weeks | Core service scaffold + domain model |
| 2 | 2 weeks | Graph storage + basic API |
| 3 | 2 weeks | Vector embeddings + context expansion |
| 4 | 1 week | Agent-host integration |
| 5 | 1 week | Admin UI + import/export |
| 6 | 1 week | Versioning + multi-tenancy |
| **Runtime Aspects** | | |
| 7 | 2 weeks | Semantic Aspect - Knowledge & Social Graph |
| 8 | 2 weeks | Intentional Aspect - Goals & Plans |
| 9 | 2 weeks | Observational Aspect - Telemetry |
| 10 | 1 week | Conversation Loop Integration |

**Total**: ~16 weeks for full implementation

---

## Phase 1: Core Service (Weeks 1-2)

**Goal:** Standalone knowledge-manager microservice with Neuroglia patterns.

### Tasks

- [ ] Project scaffold (pyproject.toml, Makefile, Docker)
- [ ] Domain model: `KnowledgeNamespace` aggregate
- [ ] Domain events with `@cloudevent` decorators
- [ ] EventStoreDB integration (write model)
- [ ] MongoDB projection (read model)
- [ ] Basic CRUD endpoints for namespaces/terms

### Deliverables

- Running service on port 8002
- Create/read namespace with terms
- Events persisted to EventStoreDB

---

## Phase 2: Graph Storage (Weeks 3-4)

**Goal:** Neo4j integration with relationship management.

### Tasks

- [ ] Neo4j Docker service + connection pool
- [ ] Graph repository implementation
- [ ] Relationship CRUD endpoints
- [ ] Event handlers to sync MongoDB → Neo4j
- [ ] Basic traversal queries

### Deliverables

- Relationships stored in Neo4j
- `GET /graph/traverse` endpoint working

---

## Phase 3: Vector Embeddings (Weeks 5-6)

**Goal:** Semantic search with local embeddings.

### Tasks

- [ ] Sentence Transformers integration
- [ ] Qdrant Docker service
- [ ] Embedding pipeline (on term create/update)
- [ ] Vector search endpoint
- [ ] Context expansion endpoint

### Deliverables

- `POST /search/semantic` working
- `POST /context/expand` returning context blocks

---

## Phase 4: Agent-Host Integration (Week 7)

**Goal:** Connect agent-host to knowledge-manager.

### Tasks

- [ ] Add `knowledge_namespace_ids` to AgentDefinition
- [ ] KnowledgeManagerClient in agent-host
- [ ] ContextExpanderService interceptor
- [ ] Inject context into agent system message
- [ ] AgentDefinition admin UI update

### Deliverables

- Agents automatically receive domain context
- Admin can assign namespaces to agents

---

## Phase 5: Admin UI + Import/Export (Week 8)

**Goal:** Admin interface for knowledge management.

### Tasks

- [ ] Namespace list/create/edit UI
- [ ] Term editor with relationship builder
- [ ] Rule editor
- [ ] Export to JSON/YAML
- [ ] Import with validation
- [ ] Seed data loader

### Deliverables

- Full admin UI for knowledge curation
- Seed files for common domains

---

## Phase 6: Versioning + Multi-Tenancy (Week 9)

**Goal:** Production-ready with revision support.

### Tasks

- [ ] Revision creation and history
- [ ] Rollback functionality
- [ ] Tenant-based access control
- [ ] Namespace sharing settings
- [ ] Audit logging

### Deliverables

- Version history with rollback
- Multi-tenant namespace isolation

---

## Runtime Aspects (Weeks 10-16)

## Phase 7: Semantic Aspect (Weeks 10-11)

**Goal:** Knowledge & Social Graph for user mastery tracking.

### Tasks

- [ ] Extend Neo4j schema for User, Skill, Concept nodes
- [ ] Implement mastery relationship tracking (`:MASTERED`, `:STRUGGLING_WITH`)
- [ ] Social graph edges (`:MENTORED_BY`, `:MEMBER_OF`)
- [ ] API endpoints for mastery queries
- [ ] Event handlers for assessment/activity events
- [ ] Prerequisite chain queries

### Deliverables

- `GET /semantic/users/{id}/mastery` returns user knowledge state
- Graph queries for prerequisites and peer connections
- Events update graph from external sources (assessments, activities)

---

## Phase 8: Intentional Aspect (Weeks 12-13)

**Goal:** Goals & Plans tracking with drift detection.

### Tasks

- [ ] `LearningIntent` aggregate with spec/status pattern
- [ ] Milestone tracking within intents
- [ ] Drift detection logic (velocity vs commitment)
- [ ] Mode-based action constraints (learning/exam/exploration)
- [ ] Schedule optimization endpoint
- [ ] Progress recording from external events

### Deliverables

- `GET /intent/users/{id}/current` returns goal and drift status
- `POST /intent/{id}/progress` updates progress
- Drift alerts when velocity drops below threshold

---

## Phase 9: Observational Aspect (Weeks 14-15)

**Goal:** Real-time telemetry processing for cognitive state inference.

### Tasks

- [ ] Telemetry ingestion (WebSocket or batch POST)
- [ ] InfluxDB/TimescaleDB integration (time-series)
- [ ] User state inference engine (confusion, fatigue, frustration)
- [ ] Alert threshold configuration
- [ ] Conversation summary projection to EventStoreDB
- [ ] Privacy controls (retention, opt-in)

### Deliverables

- `GET /telemetry/users/{id}/state` returns inferred cognitive state
- Real-time alerts for fatigue/confusion thresholds
- Conversation summaries event-sourced for analytics

---

## Phase 10: Conversation Loop Integration (Week 16)

**Goal:** Unified context assembly and proactive intervention.

### Tasks

- [ ] `ConversationContextService` assembling all three aspects
- [ ] Parallel fetching from Semantic, Intentional, Observational
- [ ] Context block formatting for LLM injection
- [ ] Proactive intervention trigger framework
- [ ] AI role mapping based on context
- [ ] agent-host integration for conversation loop

### Deliverables

- Full context vector injected into every agent invocation
- Proactive interventions fire on telemetry/intent triggers
- AI adopts appropriate role (Tutor/Coach/Facilitator/etc.)

---

## Infrastructure Requirements

### Docker Services

```yaml
services:
  knowledge-manager:
    ports: ["8002:8002"]

  neo4j:
    image: neo4j:5
    ports: ["7474:7474", "7687:7687"]

  qdrant:
    image: qdrant/qdrant:latest
    ports: ["6333:6333"]

  # For Observational Aspect
  influxdb:
    image: influxdb:2
    ports: ["8086:8086"]
```

### Dependencies

```toml
[dependencies]
neuroglia = "^x.x.x"
sentence-transformers = "^2.2"
neo4j = "^5.0"
qdrant-client = "^1.7"
influxdb-client = "^1.36"  # For telemetry
```

---

## Success Metrics

### Foundation Metrics

- Context expansion latency < 100ms (p95)
- 90% term detection accuracy
- Zero cross-tenant data leakage
- Admin can build namespace in < 30 min

### Runtime Aspect Metrics

- Conversation context assembly < 150ms (p95)
- User state inference accuracy > 80%
- Drift detection within 24 hours of velocity drop
- Proactive interventions prevent 30% of conversation abandonments
- User engagement increase of 20% with personalized context

### User Experience Metrics

- 50% reduction in prompt verbosity (users write shorter queries)
- 25% improvement in first-response accuracy
- 40% reduction in "I don't understand" follow-ups
- Positive sentiment on AI interventions > 85%

---

_End of architecture documentation._
