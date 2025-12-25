# Certification Program - Service Topology

> **Purpose:** Define service boundaries, responsibilities, and integration patterns.

## Design Principle: Generic Core + Domain-Specific Services

The architecture strictly separates:

1. **Generic Core**: Reusable across any domain (agent-host, knowledge-manager, tools-provider)
2. **Domain Services**: Certification-specific logic (blueprint-manager, external systems)

This enables the core services to be applied to other domains (healthcare, finance, education) without modification.

---

## Service Inventory

### Generic Core Services

| Service | Port | Responsibility | Persistence |
|---------|------|----------------|-------------|
| `agent-host` | 8001 | Conversation orchestration, agent execution | MongoDB (state-based) |
| `knowledge-manager` | 8002 | Context expansion, graph/vector storage | MongoDB + Neo4j |
| `tools-provider` | 8000 | MCP tool discovery and execution | MongoDB (state-based) |

### Domain-Specific Services

| Service | Status | Responsibility | Persistence |
|---------|--------|----------------|-------------|
| `blueprint-manager` | **NEW** | ExamBlueprint, SkillTemplate, FormSpec | MongoDB + EventStoreDB |
| ExamContentAuthoring | External | Forms, Items, Grading Rules | Vendor-managed |
| track-manager | External | Certification tracks, prerequisites | TBD |
| pod-manager | External | Pod lifecycle, device allocation | TBD |
| session-manager | External | Exam sessions, timing | TBD |
| exam-delivery-system | External | Candidate UI, proctoring | TBD |
| grading-system | External | Rule evaluation, scoring | TBD |

---

## Detailed Service Specifications

### agent-host

**Purpose:** Generic conversation orchestration with specialized agent configurations for each actor role.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              agent-host                                      │
│                                                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐           │
│  │  Conversation    │  │  AgentDefinition │  │ Conversation     │           │
│  │  Aggregate       │  │  Aggregate       │  │ Template         │           │
│  │                  │  │                  │  │                  │           │
│  │ • Messages       │  │ • System prompt  │  │ • Item flow      │           │
│  │ • Tool calls     │  │ • Tools list     │  │ • Widget specs   │           │
│  │ • Widget state   │  │ • Model config   │  │ • Scoring rules  │           │
│  │ • Template prog  │  │ • Namespace refs │  │                  │           │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘           │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                         Orchestrator                                  │   │
│  │                                                                       │   │
│  │  WebSocket Handler → Message Handler → Agent Runner → Stream Handler │   │
│  │                              ↓                                        │   │
│  │                    Context Expander (calls knowledge-manager)         │   │
│  │                              ↓                                        │   │
│  │                    Tool Executor (calls tools-provider)               │   │
│  │                              ↓                                        │   │
│  │                    Item Generator (for templated items)               │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  Certification Instantiation:                                               │
│  • AgentDefinitions for each actor role                                     │
│  • ConversationTemplates mapped to FormSpecs                                │
│  • Item generation from SkillTemplates                                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key Extension Point:** `knowledge_namespace_ids` in AgentDefinition links to certification namespaces.

### knowledge-manager

**Purpose:** Generic knowledge graph and context expansion, populated with certification domain data.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           knowledge-manager                                  │
│                                                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐           │
│  │ KnowledgeNamespace│  │ Terms/Relations │  │  Context API     │           │
│  │ Aggregate        │  │                  │  │                  │           │
│  │                  │  │ • Definitions    │  │ POST /expand     │           │
│  │ • certification- │  │ • Relationships  │  │ • Match terms    │           │
│  │   core           │  │ • BusinessRules  │  │ • Traverse graph │           │
│  │ • exam-analytics │  │                  │  │ • Vector search  │           │
│  │ • proctor-guide  │  │                  │  │ • Format context │           │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘           │
│                                                                              │
│  ┌───────────────────────────────────────┐                                  │
│  │            Storage Layer              │                                  │
│  │                                       │                                  │
│  │  MongoDB (state) ←→ Neo4j (graph) ←→ Vector (embeddings)                │
│  └───────────────────────────────────────┘                                  │
│                                                                              │
│  Data Sources (Certification Domain):                                       │
│  • blueprint-manager: Blueprints, Skills, KSA (static, versioned)          │
│  • analytics: Score data, trends (dynamic, aggregated)                      │
│  • session-manager: Active sessions (dynamic, real-time)                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Data Flow:**

1. `blueprint-manager` publishes CloudEvents on Blueprint/Template changes
2. `knowledge-manager` consumes events and updates namespaces
3. `agent-host` queries context API for prompt augmentation

### tools-provider

**Purpose:** Generic MCP tool registry wrapping certification domain APIs.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            tools-provider                                    │
│                                                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐           │
│  │  UpstreamSource  │  │   SourceTool     │  │  AccessPolicy    │           │
│  │  Aggregate       │  │                  │  │                  │           │
│  │                  │  │ • Tool schema    │  │ • Role-based     │           │
│  │ • ExamContent    │  │ • Execution      │  │ • User-based     │           │
│  │   Authoring API  │  │   endpoint       │  │ • Scope-based    │           │
│  │ • pod-manager    │  │ • Auth config    │  │                  │           │
│  │ • grading-system │  │                  │  │                  │           │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘           │
│                                                                              │
│  MCP Endpoints:                                                              │
│  • GET /mcp/tools - List available tools (filtered by access)               │
│  • POST /mcp/execute/{tool_name} - Execute tool with identity propagation   │
│                                                                              │
│  Certification Tools (examples):                                             │
│  • get_blueprint, update_topic, analyze_coverage                            │
│  • generate_item, submit_for_review, approve_item                           │
│  • get_candidate_context, check_pod_status                                  │
│  • query_scores, generate_report                                            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### blueprint-manager (NEW)

**Purpose:** Certification domain-specific service for Blueprint authoring and template management.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           blueprint-manager                                  │
│                                                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐           │
│  │  ExamBlueprint   │  │  SkillTemplate   │  │    FormSpec      │           │
│  │  Aggregate       │  │                  │  │                  │           │
│  │                  │  │ • stem_templates │  │ • item_slots     │           │
│  │ • Topics         │  │ • difficulty_    │  │ • time_limits    │           │
│  │ • Skills         │  │   levels         │  │ • ordering       │           │
│  │ • KSA Statements │  │ • distractor_    │  │ • scoring        │           │
│  │ • Weights        │  │   strategies     │  │                  │           │
│  │ • MQC Definition │  │ • parameters     │  │                  │           │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘           │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                      Document Ingestion                               │   │
│  │                                                                       │   │
│  │  Upload PDF/DOCX → LLM Extraction → Human Review → Structured Data   │   │
│  │                                                                       │   │
│  │  Extracts: MQC definitions, KSA statements, fairness rules           │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  Publishes (CloudEvents):                                                   │
│  • blueprint.created.v1, blueprint.updated.v1                               │
│  • skill-template.created.v1, skill-template.updated.v1                     │
│  • form-spec.created.v1, form-spec.updated.v1                               │
│                                                                              │
│  Persistence:                                                               │
│  • MongoDB: Current state (MotorRepository)                                 │
│  • EventStoreDB: Audit trail for compliance                                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Integration Patterns

### Event Flow: Blueprint → Knowledge → Agent

```
blueprint-manager                knowledge-manager              agent-host
─────────────────                ─────────────────              ──────────

     │                                  │                           │
     │  CloudEvent:                     │                           │
     │  blueprint.updated.v1            │                           │
     ├─────────────────────────────────►│                           │
     │                                  │                           │
     │                                  │ Update namespace          │
     │                                  │ (terms, relations)        │
     │                                  │                           │
     │                                  │                           │
     │                                  │                           │
     │                                  │◄──────────────────────────┤
     │                                  │  POST /context/expand     │
     │                                  │                           │
     │                                  ├──────────────────────────►│
     │                                  │  Context block            │
     │                                  │                           │
```

### Tool Execution: Agent → Tools-Provider → External

```
agent-host                      tools-provider              ExamContentAuthoring
──────────                      ──────────────              ────────────────────

     │                                │                           │
     │  POST /mcp/execute/            │                           │
     │  generate_item                 │                           │
     ├───────────────────────────────►│                           │
     │                                │                           │
     │                                │  POST /api/items          │
     │                                │  (with user token)        │
     │                                ├──────────────────────────►│
     │                                │                           │
     │                                │◄──────────────────────────┤
     │                                │  Item created             │
     │◄───────────────────────────────┤                           │
     │  Tool result                   │                           │
     │                                │                           │
```

### Real-Time Events: Session → Knowledge → Agent

```
session-manager              knowledge-manager              agent-host (Proctor)
───────────────              ─────────────────              ────────────────────

     │                                │                           │
     │  CloudEvent:                   │                           │
     │  candidate.started.v1          │                           │
     ├───────────────────────────────►│                           │
     │                                │                           │
     │                                │ Update active-sessions    │
     │                                │ namespace (cache)         │
     │                                │                           │
     │                                │                           │
     │                                │◄──────────────────────────┤
     │                                │  "What's Candidate 123    │
     │                                │   working on?"            │
     │                                │                           │
     │                                ├──────────────────────────►│
     │                                │  Current item, progress   │
     │                                │                           │
```

---

## Data Ownership

| Data | Owning Service | Consumers | Sync Mechanism |
|------|----------------|-----------|----------------|
| ExamBlueprint | blueprint-manager | knowledge-manager, agent-host | CloudEvents |
| SkillTemplate | blueprint-manager | agent-host (item generation) | CloudEvents + REST |
| FormSpec | blueprint-manager | agent-host (templates) | CloudEvents + REST |
| AgentDefinition | agent-host | — | Internal |
| Conversation | agent-host | — | Internal |
| KnowledgeNamespace | knowledge-manager | agent-host | REST API |
| UpstreamSource | tools-provider | agent-host | REST API |
| Forms, Items | ExamContentAuthoring | tools-provider (wraps) | REST API |
| Pod State | pod-manager | tools-provider (wraps) | REST API + Events |
| Scores | grading-system | knowledge-manager (analytics) | CloudEvents |

---

## Deployment Topology

### Environment Overview

The Cisco Certifications infrastructure spans multiple environments with distinct purposes:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        PRODUCTION ENVIRONMENTS                               │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    San Jose (SJ) HostingSite                         │    │
│  │                                                                      │    │
│  │  ┌─────────────────────────────────────────────────────────────┐    │    │
│  │  │              SJ-LDS (K8s Cluster - PROD)                    │    │    │
│  │  │                                                              │    │    │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │    │    │
│  │  │  │ LDS         │  │ POD         │  │ Session     │          │    │    │
│  │  │  │ (Delivery)  │  │ Automation  │  │ Manager     │          │    │    │
│  │  │  └─────────────┘  └─────────────┘  └─────────────┘          │    │    │
│  │  │                                                              │    │    │
│  │  │  Physical POD Infrastructure ← Hardened Workstations        │    │    │
│  │  │  (Americas LabLocations connect here)                        │    │    │
│  │  └─────────────────────────────────────────────────────────────┘    │    │
│  │                                                                      │    │
│  │  ┌─────────────────────────────────────────────────────────────┐    │    │
│  │  │                STG (Staging - SJ)                            │    │    │
│  │  │                                                              │    │    │
│  │  │  Test & Content Development Environment                      │    │    │
│  │  │  (LDS, POD Automation - mirrored config)                     │    │    │
│  │  └─────────────────────────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                   Brussels (BRU) HostingSite                         │    │
│  │                                                                      │    │
│  │  ┌─────────────────────────────────────────────────────────────┐    │    │
│  │  │              BRU-LDS (K8s Cluster - PROD)                   │    │    │
│  │  │                                                              │    │    │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │    │    │
│  │  │  │ LDS         │  │ POD         │  │ Session     │          │    │    │
│  │  │  │ (Delivery)  │  │ Automation  │  │ Manager     │          │    │    │
│  │  │  └─────────────┘  └─────────────┘  └─────────────┘          │    │    │
│  │  │                                                              │    │    │
│  │  │  Physical POD Infrastructure ← Hardened Workstations        │    │    │
│  │  │  (EMEA/APJC LabLocations connect here)                       │    │    │
│  │  └─────────────────────────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         AWS Cloud                                    │    │
│  │                                                                      │    │
│  │  Services NOT requiring POD access:                                  │    │
│  │                                                                      │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │    │
│  │  │ Mosaic      │  │ Mozart      │  │ Analytics   │                  │    │
│  │  │ (Authoring) │  │ (Automation)│  │ Platform    │                  │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                  │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### LabLocation → HostingSite Assignment

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ~150+ LabLocations Globally                          │
│                          (~10 active at any time)                            │
│                                                                              │
│  ┌─────────────────────────────────┐  ┌─────────────────────────────────┐   │
│  │      Static LabLocations        │  │      Mobile LabLocations        │   │
│  │    (Dedicated Proctors)         │  │    (Guest/Traveling Proctors)   │   │
│  │                                  │  │                                 │   │
│  │  • Permanent facilities          │  │  • Ephemeral (1-2 weeks)        │   │
│  │  • Major city offices            │  │  • Cannot run concurrently     │   │
│  │  • Continuous availability       │  │    (POD capacity limits)        │   │
│  └─────────────────────────────────┘  └─────────────────────────────────┘   │
│                                                                              │
│                    Assignment based on distance/latency                      │
│                              ↓                                              │
│  ┌─────────────────────────────────┐  ┌─────────────────────────────────┐   │
│  │        SJ HostingSite           │  │        BRU HostingSite          │   │
│  │                                  │  │                                 │   │
│  │  Americas LabLocations          │  │  EMEA/APJC LabLocations         │   │
│  └─────────────────────────────────┘  └─────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Mozart Platform Deployment

The Mozart platform (agent-host, knowledge-manager, tools-provider, blueprint-manager) is deployed in AWS, integrating with on-premise systems via secure VPN/API connections:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AWS - Mozart Platform                                │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         Generic Core                                 │    │
│  │                                                                      │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │    │
│  │  │ agent-host  │  │ knowledge-  │  │ tools-      │                  │    │
│  │  │  (2 pods)   │  │ manager     │  │ provider    │                  │    │
│  │  │             │  │  (2 pods)   │  │  (2 pods)   │                  │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                  │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    Certification Domain                              │    │
│  │                                                                      │    │
│  │  ┌─────────────┐                                                    │    │
│  │  │ blueprint-  │                                                    │    │
│  │  │ manager     │                                                    │    │
│  │  │  (2 pods)   │                                                    │    │
│  │  └─────────────┘                                                    │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                       Infrastructure                                 │    │
│  │                                                                      │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │    │
│  │  │ MongoDB  │ │ Neo4j    │ │EventStore│ │ Redis    │ │ Keycloak │   │    │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘   │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │               External Systems (VPN/Secure API)                      │    │
│  │                                                                      │    │
│  │  SJ-LDS ←→ BRU-LDS ←→ Mosaic ←→ pod-manager ←→ session-manager      │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Open Questions

- [x] ~~Which external systems already have stable APIs?~~
- [ ] What authentication mechanism for external systems? (OAuth2? API keys?)
- [x] ~~Network connectivity to external systems (VPN? Direct?)~~ VPN/Secure API
- [ ] Latency requirements for tool execution?

---

_Last updated: December 25, 2025_
