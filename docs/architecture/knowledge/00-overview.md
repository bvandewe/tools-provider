# Knowledge Manager Service - Architecture Overview

## Executive Summary

The **knowledge-manager** is a new microservice that provides **multi-dimensional context awareness** for AI agents. It goes far beyond static glossaries—implementing a **Reconciliation Loop** where agents continuously observe user telemetry, reference user knowledge graphs, and steer users toward their stated goals.

The service delivers four integrated aspects:

| Aspect | Metaphor | Function |
|--------|----------|----------|
| **Temporal** | "The Archive" | Event-Sourced History (immutable audit trail, time-travel queries) |
| **Semantic** | "The Map" | Knowledge & Social Graph (what user knows, who they're connected to) |
| **Intentional** | "The Compass" | Goals & Plans (desired state vs. actual progress) |
| **Observational** | "The Pulse" | Real-time Telemetry (cognitive load, sentiment, fatigue) |

## Problem Statement

Standard LLMs fail at personalized support because they lack structured context. Currently:

### Static Knowledge Gaps

- Users must explain terminology in every prompt
- Agents don't know what the user has already mastered
- No institutional knowledge accumulation

### Goal Blindness

- Agents can't enforce learning paths or deadlines
- No awareness of "Exam Mode" vs. "Exploration Mode"
- Users drift from plans without AI intervention

### Emotional Blindness

- Agents don't detect frustration, fatigue, or confusion
- No adaptive pacing based on cognitive load
- Users quit before asking for help

## Domain: Learning & Certification

The knowledge-manager targets a single domain with **role-based views** on shared entities:

### User Roles

| Role | Description | Key Views |
|------|-------------|------------|
| **ExamOwner** | Creates and manages exam blueprints | Blueprint editor, analytics dashboard |
| **Author** | Creates learning content (modules, assessments) | Content editor, prerequisite graphs |
| **Tester** | Reviews and validates content quality | Review queue, coverage reports |
| **Proctor** | Monitors exam sessions | Live session view, incident reports |
| **Candidate** | Takes assessments and learns | Learning path, progress tracker |
| **Analyst** | Reviews aggregate performance data | Anonymized analytics, trend reports |

### Shared Entities with Role-Specific Views

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        SHARED DOMAIN ENTITIES                            │
├─────────────────────────────────────────────────────────────────────────┤
│  ExamBlueprint    Skill    Concept    Resource    Cohort    User        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ExamOwner ──► Full access to ExamBlueprint CRUD                       │
│   Author    ──► Edit Concept, Resource; Read ExamBlueprint              │
│   Tester    ──► Read/Review all; Flag issues                            │
│   Proctor   ──► Read User session state; Record incidents               │
│   Candidate ──► Read own progress; Execute assessments                  │
│   Analyst   ──► Read anonymized aggregates only                         │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Solution: The AI-Augmented Conversation

A **Conversation** is not just a chat window—it is a **Reconciliation Loop** where the AI agent continuously:

1. **Observes** the user's real-time telemetry (The Pulse)
2. **References** their knowledge and social graph (The Map)
3. **Steers** them toward their stated intent (The Compass)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      THE CONVERSATION LOOP                               │
│                                                                          │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐         │
│  │  TEMPORAL  │  │  SEMANTIC  │  │ INTENTIONAL│  │OBSERVATIONAL│        │
│  │"The Archive"│ │ "The Map" │  │"The Compass"│ │ "The Pulse"│         │
│  │            │  │            │  │            │  │            │         │
│  │ - Events   │  │ - Mastery  │  │ - Goals    │  │ - Telemetry│         │
│  │ - History  │  │ - Relations│  │ - Progress │  │ - Sentiment│         │
│  │ - Replay   │  │ - Resources│  │ - Velocity │  │ - Fatigue  │         │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘         │
│        │               │               │               │                │
│        └───────────────┴───────────────┴───────────────┘                │
│                                │                                         │
│                                ▼                                         │
│                      ┌─────────────────┐                                 │
│                      │  CONTEXT VECTOR │                                 │
│                      │ [History, Graph,│                                 │
│                      │  Spec, Telemetry]│                                │
│                      └────────┬────────┘                                 │
│                               │                                          │
│                               ▼                                          │
│                      ┌─────────────────┐                                 │
│                      │   AI AGENT      │                                 │
│                      │ (Tutor/Coach/   │                                 │
│                      │  Facilitator)   │                                 │
│                      └─────────────────┘                                 │
└─────────────────────────────────────────────────────────────────────────┘
```

## The Four Aspects

### 1. Temporal Aspect: "The Archive" (History & Replay)

Provides **immutable, append-only event streams** for audit-critical entities:

- **Storage**: EventStoreDB—each aggregate's history is a sequence of `DomainEvent` instances
- **Guarantee**: Events are immutable; the stream is the source of truth
- **Capability**: Reconstruct entity state at **any point in time** (time-travel queries)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     EVENT STREAM (Append-Only)                           │
│                                                                          │
│  t₀          t₁           t₂           t₃           t₄      → now       │
│  ┌──────┐    ┌──────┐    ┌──────┐    ┌──────┐    ┌──────┐               │
│  │Event₁│───►│Event₂│───►│Event₃│───►│Event₄│───►│Event₅│               │
│  │Created│   │Updated│   │Progress│  │Mastered│  │Certified│            │
│  └──────┘    └──────┘    └──────┘    └──────┘    └──────┘               │
│       │           │           │           │           │                  │
│       ▼           ▼           ▼           ▼           ▼                  │
│   State@t₀    State@t₁    State@t₂    State@t₃    State@t₄              │
│   (replay)    (replay)    (replay)    (replay)    (current)             │
└─────────────────────────────────────────────────────────────────────────┘
```

**AI Benefit**: Complete audit trail. The AI can answer "What was the user's mastery level on December 1st?" or "Show me the progression leading to this certification."

**Use Cases**:

- Compliance audits for certifications
- Debugging "How did the user get into this state?"
- Trend analysis over time
- Undo/rollback scenarios

### 2. Semantic Aspect: "The Map" (Context & Connection)

Projects **all entities and their relationships** into a **Knowledge & Social Graph**:

- **Nodes**: `User`, `Skill`, `Concept`, `Resource`, `Cohort`, `Blueprint`, `Topic`, `Exam`
- **Edges**: `[:MASTERED]`, `[:STRUGGLING_WITH]`, `[:PREREQUISITE_FOR]`, `[:CORRELATES_WITH]`, `[:PREDICTS_SUCCESS_IN]`
- **Temporal Versioning**: Nodes and edges include revision tracking (like versioned DomainEvents)

**Scope Beyond Users**:

- Blueprint Topic interdependencies and prerequisite chains
- KPI correlations between Candidate performance patterns
- Similarity searches via vector embeddings with temporal history
- Statistical/probabilistic queries to external analytics engines

**AI Benefit**: Zero-shot context awareness. The AI doesn't ask "What do you know?"—it queries the graph and vectors.

### 3. Intentional Aspect: "The Compass" (Goals & Plans)

Acts as the **Kubernetes Manifest for Learning** with an **autonomous Reconciliation Loop**:

- **Spec**: `target_date`, `learning_style`, `weekly_commitment`, `mode`
- **Status**: `current_velocity`, `completion_percent`, `drift_detected`
- **Reconciliation Loop**: Autonomous per-aggregate reconcilers subscribe to DomainEvent streams, converging toward Goals

**Intent Expression via Supportive Agent**:

- Users express Intent through conversation with an agent equipped with specialized tools
- Agent guides through goal identification, constraint discovery, preference elicitation
- Tools: `list_available_goals`, `analyze_goal_requirements`, `estimate_realistic_timeline`, `create_learning_intent`

**AI Benefit**: Strategic alignment. The AI enforces the Spec, acting as the "Controller" in a K8s reconciliation loop.

### 4. Observational Aspect: "The Pulse" (Empathy & Adaptation)

Processes high-frequency telemetry streams:

- **Metrics**: `TimeOnTask`, `SeekRate`, `TypingErrorRate`, `SentimentScore`, `FocusLossEvents`
- **Storage**: Time-series (ephemeral), not event-sourced

**AI Benefit**: Emotional intelligence. The AI adapts tone and pacing based on real-time cognitive load.

## Key Capabilities

| Capability | Description |
|------------|-------------|
| **Reactive Support** | Respond to user queries with full context (Tutor, Coach, Facilitator roles) |
| **Proactive Support** | Intervene before problems occur (Connector, Planner, Wellness roles) |
| **Context Expansion** | Automatically inject relevant knowledge into prompts |
| **Goal Enforcement** | Prevent drift from learning plans |
| **Adaptive Pacing** | Adjust based on fatigue/confusion signals |

## Architecture Position

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND CLIENTS                                    │
│                   (Chat UI, Admin UI, External Consumers)                        │
└───────────────────────────────────┬─────────────────────────────────────────────┘
                                    │
                 ┌──────────────────┼──────────────────┐
                 │                  │                  │
                 ▼                  ▼                  ▼
        ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
        │   agent-host    │ │ tools-provider  │ │knowledge-manager│
        │                 │ │                 │ │                 │
        │ - Conversations │ │ - MCP Tools     │ │ - Namespaces    │
        │ - Agents        │ │ - Sources       │ │ - Terms         │
        │ - Templates     │ │ - Execution     │ │ - Relationships │
        │ - Orchestrator  │ │ - Access Ctrl   │ │ - Rules         │
        └────────┬────────┘ └────────┬────────┘ └────────┬────────┘
                 │                   │                   │
                 │         ┌─────────┴─────────┐         │
                 │         │                   │         │
                 ▼         ▼                   ▼         ▼
        ┌─────────────────────────────────────────────────────────┐
        │                 SHARED INFRASTRUCTURE                    │
        │  ┌─────────────┐ ┌─────────────┐ ┌───────────────────┐  │
        │  │ EventStoreDB│ │   MongoDB   │ │     Keycloak      │  │
        │  │  (Events)   │ │ (ReadModel) │ │ (Auth/OAuth2)     │  │
        │  └─────────────┘ └─────────────┘ └───────────────────┘  │
        │  ┌─────────────┐ ┌─────────────┐ ┌───────────────────┐  │
        │  │    Redis    │ │   Neo4j     │ │  Embedding Svc    │  │
        │  │  (Cache)    │ │  (Graph)    │ │  (Local/Remote)   │  │
        │  └─────────────┘ └─────────────┘ └───────────────────┘  │
        └─────────────────────────────────────────────────────────┘
```

## Service Boundaries

| Service | Responsibility | Data Ownership |
|---------|---------------|----------------|
| **agent-host** | Conversation orchestration, agent execution | Conversations, AgentDefinitions, Templates |
| **tools-provider** | Tool discovery, access control, execution | UpstreamSources, SourceTools, AccessPolicies |
| **knowledge-manager** | Domain knowledge, context expansion | Namespaces, Terms, Relationships, Rules, Revisions |

## Key Design Decisions

### 1. Separate Microservice (Not Embedded)

- **Rationale**: Knowledge is a cross-cutting concern that may be shared across multiple agent-host deployments
- **Benefit**: Independent scaling, specialized storage (graph + vector), reusable by other services

### 2. Local Embedding Models with Abstraction Layer

- **Rationale**: Minimize external dependencies (OpenAI), reduce latency, control costs; enable backend swapping
- **Implementation**: Abstraction layer with `VectorStore` and `EmbeddingProvider` protocols
- **Default Backend**: Qdrant (base implementation); alternatives: MongoDB Atlas, Neo4j native vectors
- **Embedding Provider**: Sentence Transformers (all-MiniLM-L6-v2) primary, OpenAI fallback
- **Temporal Versioning**: All vectors include revision tracking linked to source DomainEvents

### 3. Graph-Native Storage

- **Rationale**: Relationships are first-class citizens; graph traversal is core to context expansion
- **Implementation**: Neo4j for graph operations, with event-sourced aggregates for audit trail

### 4. Namespace Versioning

- **Rationale**: Knowledge evolves; teams need rollback capability and change tracking
- **Implementation**: Revision-based model with branching support

### 5. DDD/CQRS with Hybrid Persistence

- **Rationale**: Consistency with agent-host and tools-provider; Neuroglia framework
- **Implementation**: AggregateRoot pattern with state-based persistence (MongoDB via `MotorRepository`) and CloudEvent emission for external observability. EventStoreDB reserved for audit-critical aggregates only.

### 6. Unified Graph + Vector with Neo4j 5.x

- **Rationale**: Minimize database sprawl; Neo4j 5.11+ supports native vector indexes
- **Trade-off**: Acceptable for moderate scale (<10M vectors); revisit if vector search becomes bottleneck
- **Implementation**: Single Neo4j deployment for both graph traversal and semantic search

### 7. Bounded Graph Complexity via Semantic Groups

- **Rationale**: Unbounded graph traversal is expensive and noisy; limit by default
- **Implementation**: Edges scoped to semantic groups; cross-group/cross-namespace edges are explicit opt-in
- **Benefit**: Predictable query performance, clearer ownership, reduced accidental coupling

### 8. Hardcoded Rules → Learned Rules Evolution

- **Rationale**: Start with explicit business rules, evolve toward agent-maintained rules
- **Implementation**: Seed dataset bootstraps known rules; agents suggest refinements; humans approve promotion
- **Tool**: Neuroglia's `BusinessRule` validation system (`neuroglia.validation.business_rules`)

### 9. External Workflow Orchestration (Synapse)

- **Rationale**: Complex multi-step workflows have different scaling/isolation needs
- **Implementation**: [Synapse](https://github.com/serverlessworkflow/synapse) subscribes to CloudEvents, executes workflow instances
- **Benefit**: knowledge-manager stays focused on state; workflows are declarative and versioned

## Document Index

| Document | Description |
|----------|-------------|
| [01-domain-model.md](01-domain-model.md) | Aggregates, entities, value objects, domain events |
| [02-api-contracts.md](02-api-contracts.md) | REST API design and endpoints |
| [03-integration.md](03-integration.md) | agent-host integration patterns |
| [04-context-expander.md](04-context-expander.md) | Prompt augmentation interceptor |
| [05-graph-analytics.md](05-graph-analytics.md) | Community detection, summarization |
| [06-vector-embeddings.md](06-vector-embeddings.md) | Local embedding models, vector search |
| [07-versioning.md](07-versioning.md) | Namespace revision support |
| [08-multi-tenancy.md](08-multi-tenancy.md) | Sharing namespaces across deployments |
| [09-import-export.md](09-import-export.md) | Seed data and import/export |
| [10-implementation-plan.md](10-implementation-plan.md) | Phased implementation roadmap |
| **Runtime Aspects** | |
| [11-temporal-aspect.md](11-temporal-aspect.md) | "The Archive" - Event-Sourced History & Time-Travel |
| [12-semantic-aspect.md](12-semantic-aspect.md) | "The Map" - Knowledge & Social Graph |
| [13-intentional-aspect.md](13-intentional-aspect.md) | "The Compass" - Goals & Plans |
| [14-observational-aspect.md](14-observational-aspect.md) | "The Pulse" - Telemetry & Empathy |
| [15-conversation-loop.md](15-conversation-loop.md) | Integrated reconciliation loop |

## Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **API** | FastAPI | REST endpoints, WebSocket (future) |
| **Framework** | Neuroglia | DDD/CQRS with Hybrid persistence |
| **State Store** | MongoDB | State-based persistence (most aggregates) |
| **Event Store** | EventStoreDB | Audit-critical aggregates only |
| **Graph + Vector** | Neo4j 5.x | Unified graph traversal + vector search |
| **Telemetry** | InfluxDB | Ephemeral time-series (Observational Aspect) |
| **Embeddings** | Sentence Transformers | Local embedding generation |
| **Auth** | Keycloak | OAuth2/OIDC, shared with other services |
| **Cache** | Redis | Query caching, rate limiting |

### Persistence Strategy

The service uses Neuroglia's **Hybrid Pattern**: State-based persistence with CloudEvent emission for observability.

| Entity | Persistence | Rationale |
|--------|-------------|------------|
| `SemanticProfile` | **State-Based** (MongoDB) | Frequent updates, graph sync |
| `LearningIntent` | **State-Based** (MongoDB) | Drift detection in aggregate |
| `TelemetryWindow` | **Ephemeral** (InfluxDB) | Time-series, no audit need |
| `ExamBlueprint` | **Event-Sourced** (EventStoreDB) | Audit trail, compliance |
| `Certification` | **Event-Sourced** (EventStoreDB) | Legal record, immutable |

**Key Insight**: DomainEvents are still emitted as CloudEvents for external analytics, but NOT persisted to EventStoreDB for most aggregates. This provides observability without storage overhead.

## Success Metrics

### Phase 1: Efficiency (MVP)

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Prompt Reduction** | 50%+ shorter prompts | Compare baseline vs. context-augmented |
| **Response Accuracy** | >90% domain-specific | Expert review sampling |
| **Context Latency** | <100ms added | P95 latency instrumentation |
| **Adoption** | >80% agents configured | Knowledge binding coverage |

### Phase 2: Trust & Alignment (6-12 months)

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Intervention Acceptance** | >70% proactive suggestions accepted | User action tracking |
| **Autonomy Progression** | Users opt into higher autonomy tiers | Tier migration analytics |
| **Goal Drift Detection** | <24hr detection of behind/critical status | Drift event frequency |
| **Override Rate** | <15% of agent recommendations overridden | User correction tracking |

### Phase 3: Ecosystem Health (12-24 months)

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Agent Collaboration** | >30% of goals involve multi-agent coordination | Orchestration logs |
| **Mutual Benefit Index** | Positive-sum outcomes in peer interactions | Cohort outcome analysis |
| **Knowledge Network Effects** | 10x content reuse across users | Graph traversal analytics |
| **Opt-In Dependency Growth** | Organic growth in inter-agent subscriptions | Dependency graph metrics |

### Phase 4: Emergent Harmony (24+ months)

| Indicator | Description | Observability |
|-----------|-------------|---------------|
| **Virtuous Cycles** | Self-reinforcing improvement loops | Trend analysis on learning velocity |
| **Human-Agent Trust** | Users delegate increasingly complex goals | Autonomy tier distribution |
| **Agent-Agent Cooperation** | Agents negotiate resource sharing | Inter-agent communication logs |
| **Adaptive Equilibrium** | System self-corrects without human intervention | Anomaly detection + auto-recovery |

> **Design Principle**: Harmony is not a destination but an emergent property of aligned incentives, graduated autonomy, and opt-in interdependencies. The system creates conditions for virtuous cycles rather than mandating them.

## Evolution Path: From Tool to Ecosystem

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AUTONOMY PROGRESSION                                 │
│                                                                              │
│   PHASE 1              PHASE 2              PHASE 3              PHASE 4    │
│   ────────             ────────             ────────             ────────   │
│                                                                              │
│   ┌─────────┐         ┌─────────┐         ┌─────────┐         ┌─────────┐  │
│   │  TOOL   │   ───►  │ASSISTANT│   ───►  │COLLABOR-│   ───►  │ECOSYSTEM│  │
│   │         │         │         │         │  ATOR   │         │PARTICIPANT│ │
│   └─────────┘         └─────────┘         └─────────┘         └─────────┘  │
│                                                                              │
│   - Reactive only     - Proactive hints   - Negotiated goals  - Emergent    │
│   - Human initiates   - Opt-in autonomy   - Agent-agent comm  - Virtuous    │
│   - No memory         - Context-aware     - Shared learning     cycles      │
│                                                                              │
│   Confidence: 0.95    Confidence: 0.75    Confidence: 0.55    Confidence:   │
│   (Proven)            (Validated)         (Experimental)      0.35 (Vision) │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Enabling Conditions for Emergent Harmony

1. **Optional Autonomy**: Users control autonomy levels; trust is earned, not assumed
2. **Opt-In Inter-Communication**: Agents subscribe to each other's events voluntarily
3. **Opt-In Inter-Dependencies**: Services declare capabilities; consumers choose to depend
4. **Aligned Incentives**: Reward structures favor long-term outcomes over short-term engagement
5. **Transparency**: All agent actions are observable; users can audit and override

### Reinforcement Learning Considerations

| Aspect | Approach | Risk Mitigation |
|--------|----------|-----------------|
| **Reward Signal** | Goal progression + user satisfaction blend | Multi-objective optimization, not single metric |
| **Exploration** | Bounded by safety policies | Human-in-the-loop for novel actions |
| **Credit Assignment** | Causal attribution via event streams | Temporal aspect enables replay analysis |
| **Cold Start** | Pretrained on expert demonstrations | Transfer learning from similar domains |

> **Caution**: RL in production requires strong guardrails. Start with rule-based proactive agents, introduce learning gradually with A/B testing and human oversight.

## Bootstrap: Seed Data & Admin Use Cases

### Phase 1 Admin Capabilities

The `/admin` page provides initial use cases for knowledge bootstrapping:

| Use Case | Description | Output |
|----------|-------------|--------|
| **Document Processing** | Upload PDF syllabi, specs, regulations → extract entities | Terms, Concepts, Rules |
| **Knowledge Seed Import** | Load curated YAML/JSON datasets | Namespaces with pre-defined structure |
| **Namespace Designer** | Visual editor for semantic groups and relationships | Graph topology |
| **Rule Editor** | Define business rules with validation preview | BusinessRule instances |

### Seed Dataset Structure

```yaml
# seed/engineering-certification.yaml
namespace:
  id: engineering-certification
  name: Engineering Certification Program
  semantic_groups:
    - id: python-development
      skills: [Python, Testing, Packaging]
      concepts:
        - { id: decorators, prereqs: [functions, closures] }
        - { id: generators, prereqs: [iterators] }
      rules:
        - name: decorator_mastery_requires_closures
          type: constraint
          condition: "skill.target == 'Decorators'"
          predicate: "user.mastered('Closures')"
          message: "Master Closures before attempting Decorators"

  external_relationships:
    - target_namespace: compliance-requirements
      type: DEPENDS_ON
      imported_terms: [audit_trail, data_retention]
```

### Emergent Capabilities (Later Phases)

These capabilities **emerge from stable Namespaces** rather than being built upfront:

| Capability | Prerequisite | Emergence Mechanism |
|------------|--------------|---------------------|
| **Process Mining** | Stable event streams | Pattern detection on CloudEvents |
| **Anomaly Detection** | Baseline established | Statistical deviation from norm |
| **Automatic Baselines** | Sufficient historical data | Rolling averages, percentile bounds |
| **Cross-Namespace Insights** | Multiple stable namespaces | Graph analytics across topology |

---

_Next: [01-domain-model.md](01-domain-model.md) - Domain Model Design_
