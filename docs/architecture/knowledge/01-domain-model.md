# Knowledge Manager - Domain Model

## Overview

The knowledge-manager follows DDD/ES/CQRS patterns consistent with agent-host and tools-provider. Aggregates use hybrid persistence: state-based (MongoDB via `MotorRepository`) for most entities, event-sourced (EventStoreDB) for audit-critical aggregates.

## Namespace Architecture

Namespaces have a **dual structure**:

### Internal Structure: Knowledge Domains

Each namespace contains a hierarchical knowledge structure organized by:

- **DomainEvent type hierarchy** (mirrors the aggregate event streams)
- **Semantic aspects** (graph clusters of related concepts)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    NAMESPACE INTERNAL STRUCTURE                              │
│                                                                              │
│   Namespace: "engineering-certification"                                    │
│   ├── SemanticGroup: "python-development"                                   │
│   │     ├── Skill: Python                                                   │
│   │     ├── Concept: Decorators, Generators, Async                         │
│   │     ├── Resource: Tutorial videos, exercises                           │
│   │     └── BusinessRules: [validation constraints, incentives]            │
│   │                                                                          │
│   ├── SemanticGroup: "cloud-infrastructure"                                 │
│   │     ├── Skill: AWS, Kubernetes                                          │
│   │     ├── Concept: Lambda, EKS, IAM                                       │
│   │     └── BusinessRules: [certification prerequisites]                   │
│   │                                                                          │
│   └── Cross-Group Edges (explicit, opt-in)                                  │
│         └── Python [:USED_IN] AWS-Lambda                                    │
│                                                                              │
│   DomainEvent Hierarchy:                                                    │
│   └── namespace.term.added.v1                                               │
│   └── namespace.relationship.added.v1                                       │
│   └── namespace.rule.added.v1                                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

### External Structure: Inter-Namespace Topology

Namespaces exist in an **organizational graph** with peer relationships:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    NAMESPACE EXTERNAL TOPOLOGY (Neo4j)                       │
│                                                                              │
│   ┌─────────────────┐         ┌─────────────────┐                           │
│   │   engineering   │◄───────►│   compliance    │                           │
│   │  certification  │ DEPENDS │  requirements   │                           │
│   └────────┬────────┘   ON    └─────────────────┘                           │
│            │                                                                 │
│            │ EXTENDS                                                         │
│            ▼                                                                 │
│   ┌─────────────────┐         ┌─────────────────┐                           │
│   │    platform     │◄───────►│   security      │                           │
│   │   fundamentals  │ RELATED │   standards     │                           │
│   └─────────────────┘   TO    └─────────────────┘                           │
│                                                                              │
│   Relationship Types:                                                        │
│   - [:EXTENDS] - Inherits terms and rules                                   │
│   - [:DEPENDS_ON] - Requires concepts from peer                             │
│   - [:RELATED_TO] - Advisory association                                    │
│   - [:SUPERSEDES] - Version replacement                                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Agent Entities in the Organizational Graph

Agents are **first-class AggregateRoot entities** that participate in the namespace topology. Each agent exposes a **public API** via Tasks (tools/RPC) that defines its behavioral contract.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    AGENT AS AGGREGATEROOT ENTITY                             │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  AgentDefinition (AggregateRoot)                                     │   │
│   │                                                                      │   │
│   │  Identity:                                                           │   │
│   │    id: "tutor-python-senior"                                        │   │
│   │    namespace_id: "engineering-certification"                        │   │
│   │                                                                      │   │
│   │  Public API (Tasks):                      ◄── Defines behavioral    │   │
│   │    - explain_concept(concept_id)              contract              │   │
│   │    - assess_mastery(skill_id)                                       │   │
│   │    - suggest_resource(learning_style)                               │   │
│   │                                                                      │   │
│   │  Capabilities (Claims):                   ◄── What agent can do     │   │
│   │    - tutoring: ["python", "testing"]                                │   │
│   │    - assessment: ["quiz", "code-review"]                            │   │
│   │                                                                      │   │
│   │  Goals (Alignment):                       ◄── What agent optimizes  │   │
│   │    - user_mastery_improvement                                       │   │
│   │    - engagement_without_burnout                                     │   │
│   │                                                                      │   │
│   │  Skills (Autonomous Tasks):               ◄── Self-directed work   │   │
│   │    - detect_struggle → offer_hint                                   │   │
│   │    - track_velocity → adjust_pacing                                 │   │
│   │                                                                      │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### A2A (Agent-to-Agent) Communication

Entities engage asynchronously using the **A2A standard** for inter-agent communication:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    A2A COMMUNICATION PATTERNS                                │
│                                                                              │
│   ┌─────────────┐                              ┌─────────────┐              │
│   │ Tutor Agent │                              │ Mentor Agent│              │
│   │             │   ──── A2A Message ────►     │             │              │
│   │ (Candidate  │   { task: "find_mentor",     │ (Peer       │              │
│   │  support)   │     context: {...},          │  matching)  │              │
│   │             │     reply_to: "..." }        │             │              │
│   └─────────────┘                              └─────────────┘              │
│                                                                              │
│   Communication Modes:                                                       │
│   ─────────────────────                                                      │
│   • RPC (Sync):   Direct task invocation via MCP tools                      │
│   • A2A (Async):  Message-based, supports complex negotiations              │
│   • Events:       CloudEvent pub/sub for observability                      │
│                                                                              │
│   A2A Message Structure:                                                     │
│   ─────────────────────                                                      │
│   {                                                                          │
│     "id": "msg-uuid",                                                        │
│     "from": "agent://tutor-python-senior",                                  │
│     "to": "agent://mentor-matching-service",                                │
│     "task": "find_available_mentor",                                        │
│     "context": {                                                             │
│       "skill_id": "python-decorators",                                      │
│       "candidate_id": "user-123",                                           │
│       "urgency": "low"                                                       │
│     },                                                                       │
│     "reply_to": "agent://tutor-python-senior/inbox",                        │
│     "timeout_ms": 30000                                                      │
│   }                                                                          │
│                                                                              │
│   Trust-Gated Invocation:                                                    │
│   ───────────────────────                                                    │
│   • Agents verify trust level before accepting tasks                        │
│   • Capabilities are checked against requested task                         │
│   • Goal alignment is evaluated for delegation decisions                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Agent Aggregate Model

```python
class AgentDefinitionState(AggregateState[str]):
    """State for Agent as an AggregateRoot entity."""

    # Identity
    id: str
    namespace_id: str
    display_name: str

    # Public API - Tasks exposed via MCP/RPC
    tasks: list[AgentTask]  # Defines behavioral contract

    # Capabilities - What the agent claims it can do
    capabilities: dict[str, list[str]]  # e.g., {"tutoring": ["python", "testing"]}

    # Goals - What the agent optimizes for
    goals: list[AgentGoal]  # Alignment criteria for collaboration

    # Skills - Tasks agent can execute autonomously
    skills: list[AgentSkill]  # Self-directed, trigger-based actions

    # Trust & Discovery
    trust_level: int  # Current trust level (0-4)
    discoverable: bool  # Visible in agent discovery queries

    # State tracking
    state_version: int
    created_at: datetime
    last_modified: datetime


@dataclass
class AgentTask:
    """A task exposed in the agent's public API."""

    name: str                    # "explain_concept"
    description: str             # Human-readable purpose
    input_schema: dict           # JSON Schema for parameters
    output_schema: dict          # JSON Schema for response
    required_trust_level: int    # Minimum trust to invoke
    is_synchronous: bool         # RPC (True) or A2A async (False)


@dataclass
class AgentGoal:
    """A goal the agent optimizes for."""

    name: str                    # "user_mastery_improvement"
    metric: str                  # How to measure progress
    priority: int                # Relative importance (1-10)
    alignment_keywords: list[str]  # For goal-matching in discovery


@dataclass
class AgentSkill:
    """An autonomous capability the agent can execute."""

    name: str                    # "detect_struggle_offer_hint"
    trigger_events: list[str]   # DomainEvents that activate this skill
    action: str                  # Task to execute when triggered
    requires_approval: bool      # Human-in-loop for this skill?
    cooldown_seconds: int        # Minimum time between activations
```

### Graph Locality Principle

**Edges are scoped to semantic groups by default** to limit complexity:

| Edge Scope | Discovery | Rationale |
|------------|-----------|-----------|
| **Intra-SemanticGroup** | Automatic | Concepts within same group are implicitly related |
| **Cross-SemanticGroup** | Explicit opt-in | Requires intentional edge creation |
| **Cross-Namespace** | Explicit + Trust | Requires namespace-level relationship + access control |

## Business Rules Integration

Business rules leverage Neuroglia's `BusinessRule` validation system (`neuroglia.validation.business_rules`):

```python
from neuroglia.validation.business_rules import BusinessRule, PropertyRule, ConditionalRule

class NamespaceBusinessRule(BusinessRule[KnowledgeNamespace]):
    """Business rule evaluated within the Reconciliation Loop."""

    # Rule metadata
    rule_type: str  # "constraint", "incentive", "procedure"
    applies_to_semantic_groups: list[str]
    evaluated_on_events: list[str]  # DomainEvent types that trigger evaluation

    @abstractmethod
    def is_satisfied_by(self, entity: KnowledgeNamespace) -> bool:
        """Evaluate rule against namespace state."""
        pass


# Example: Hardcoded seed rules
SEED_RULES = [
    PropertyRule(
        name="blueprint_min_sections",
        property_getter=lambda bp: len(bp.sections),
        predicate=lambda count: count >= 3,
        field_name="sections",
        message="ExamBlueprint must have at least 3 sections"
    ),
    ConditionalRule(
        name="certification_prereq_check",
        condition=lambda intent: intent.goal_type == "certification",
        rule=PropertyRule(
            name="has_required_skills",
            property_getter=lambda intent: intent.completed_prerequisites,
            predicate=lambda prereqs: all(p.status == "mastered" for p in prereqs),
            message="All prerequisite skills must be mastered"
        ),
        condition_description="when pursuing certification"
    ),
]
```

### Rule Lifecycle

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BUSINESS RULE LIFECYCLE                              │
│                                                                              │
│   PHASE 1: Seed                    PHASE 2: Refine                          │
│   ────────────────                 ───────────────                          │
│   - Hardcoded rules                - Agent suggestions                      │
│   - Admin UI entry                 - Usage analytics                        │
│   - Import from docs               - A/B testing variants                   │
│                                                                              │
│   PHASE 3: Emerge                  PHASE 4: Stabilize                       │
│   ───────────────                  ──────────────────                       │
│   - Pattern detection              - Promote to "blessed" rules             │
│   - Anomaly-based rules            - Version and audit                      │
│   - Agent-proposed rules           - Cross-namespace propagation            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Agent-to-Agent Discovery & Trust

"Levels of entity connection" applies to agent discovery, engagement, and delegation:

```python
class AgentTrustLevel:
    """Trust levels for agent-to-agent interactions."""

    UNKNOWN = 0      # No prior interaction
    DISCOVERED = 1   # Found via namespace/capability search
    ENGAGED = 2      # Has successfully collaborated
    TRUSTED = 3      # Proven track record, can delegate
    DELEGATED = 4    # Authorized for autonomous action

class AgentCapability:
    """Advertised capability for discovery."""

    namespace_id: str           # Semantic scope
    capability_type: str        # "tutor", "reviewer", "analyst"
    goal_alignment: list[str]   # Goals this agent can contribute to
    trust_requirements: int     # Minimum trust level to engage
```

### Goal-Driven Convergence

Agent collaboration emerges from **convergent goals**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    GOAL-DRIVEN AGENT COLLABORATION                           │
│                                                                              │
│   Candidate Goal: "Pass Python Senior Certification"                        │
│                              │                                               │
│                              ▼                                               │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                    AGENT DISCOVERY                                   │   │
│   │  Query: agents with goal_alignment ∩ "python-certification"         │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                              │                                               │
│              ┌───────────────┼───────────────┐                              │
│              ▼               ▼               ▼                              │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                     │
│   │ Tutor Agent  │  │ Mentor Agent │  │Practice Agent│                     │
│   │ (Concepts)   │  │ (Guidance)   │  │ (Exercises)  │                     │
│   └──────────────┘  └──────────────┘  └──────────────┘                     │
│          │                  │                  │                            │
│          └──────────────────┴──────────────────┘                            │
│                              │                                               │
│                              ▼                                               │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  TRUST ACCUMULATION: Successful interactions → Higher trust levels  │   │
│   │  DELEGATION: Trusted agents can act autonomously on sub-goals       │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Workflow Orchestration (External)

Complex workflows are delegated to **Synapse** (ServerlessWorkflow runtime):

```yaml
# Example: Certification workflow triggered by CloudEvent
id: certification-workflow
version: 1.0.0
specVersion: "0.8"
start: validate-prerequisites
functions:
  - name: validatePrereqs
    operation: knowledge-manager/api/validate-prerequisites
  - name: scheduleExam
    operation: exam-service/api/schedule
  - name: notifyCandidate
    operation: notification-service/api/send
states:
  - name: validate-prerequisites
    type: operation
    actions:
      - functionRef: validatePrereqs
    transition: schedule-exam
  # ... workflow continues
```

**Integration Pattern**:

- knowledge-manager emits CloudEvents (e.g., `intent.goal.achieved.v1`)
- Synapse subscribes and triggers workflow instances
- Workflow steps call back to knowledge-manager APIs
- Results update aggregate state via commands

## Aggregate Roots

### 1. KnowledgeNamespace (Primary Aggregate)

The namespace is the top-level container for domain knowledge. It owns terms, relationships, and rules.

```python
# domain/entities/knowledge_namespace.py

from datetime import datetime
from typing import Any
from neuroglia.data.abstractions import AggregateRoot, AggregateState
from neuroglia.mapping.mapper import map_to

@map_to(KnowledgeNamespaceDto)
class KnowledgeNamespaceState(AggregateState[str]):
    """State for KnowledgeNamespace aggregate."""

    # Identity
    id: str  # Slug: "assessments", "networking"

    # Ownership
    owner_tenant_id: str | None  # None = global/shared
    owner_user_id: str | None  # Creator

    # Display
    name: str  # "Assessment Domain"
    description: str
    icon: str | None  # Bootstrap icon class

    # Versioning
    current_revision: int  # Current active revision
    revisions: list[dict]  # Revision metadata

    # Access Control
    is_public: bool  # Available to all tenants
    allowed_tenant_ids: list[str]  # Explicit tenant allow list

    # Statistics (denormalized for performance)
    term_count: int
    relationship_count: int
    rule_count: int

    # Audit
    created_by: str
    created_at: datetime
    updated_at: datetime
    version: int  # Optimistic concurrency


class KnowledgeNamespace(AggregateRoot[KnowledgeNamespaceState, str]):
    """Aggregate root for knowledge namespaces.

    A namespace groups related domain terms, their relationships,
    and business rules. Namespaces support versioning for
    revision history and rollback.
    """

    def __init__(
        self,
        namespace_id: str,
        name: str,
        description: str = "",
        owner_user_id: str | None = None,
        owner_tenant_id: str | None = None,
        **kwargs
    ) -> None:
        super().__init__()
        # Emit KnowledgeNamespaceCreatedDomainEvent
        ...

    # === Term Management ===
    def add_term(
        self,
        term: str,
        definition: str,
        aliases: list[str] | None = None,
        examples: list[str] | None = None,
        context_hint: str | None = None,
    ) -> str:
        """Add a term to this namespace. Returns term_id."""
        # Emit KnowledgeTermAddedDomainEvent
        ...

    def update_term(self, term_id: str, **updates) -> bool:
        """Update an existing term."""
        # Emit KnowledgeTermUpdatedDomainEvent
        ...

    def remove_term(self, term_id: str) -> bool:
        """Remove a term (soft delete)."""
        # Emit KnowledgeTermRemovedDomainEvent
        ...

    # === Relationship Management ===
    def add_relationship(
        self,
        source_term_id: str,
        target_term_id: str,
        relationship_type: str,
        description: str | None = None,
        bidirectional: bool = False,
        weight: float = 1.0,
    ) -> str:
        """Add a relationship between terms. Returns relationship_id."""
        # Emit KnowledgeRelationshipAddedDomainEvent
        ...

    def remove_relationship(self, relationship_id: str) -> bool:
        """Remove a relationship."""
        # Emit KnowledgeRelationshipRemovedDomainEvent
        ...

    # === Rule Management ===
    def add_rule(
        self,
        name: str,
        condition: str,
        rule_text: str,
        applies_to_term_ids: list[str],
        priority: int = 0,
    ) -> str:
        """Add a business rule. Returns rule_id."""
        # Emit KnowledgeRuleAddedDomainEvent
        ...

    def update_rule(self, rule_id: str, **updates) -> bool:
        """Update an existing rule."""
        ...

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule."""
        ...

    # === Versioning ===
    def create_revision(self, message: str, created_by: str) -> int:
        """Create a new revision snapshot. Returns revision number."""
        # Emit KnowledgeRevisionCreatedDomainEvent
        ...

    def rollback_to_revision(self, revision: int, rolled_back_by: str) -> bool:
        """Rollback to a previous revision."""
        # Emit KnowledgeRevisionRolledBackDomainEvent
        ...

    # === Access Control ===
    def update_access(
        self,
        is_public: bool | None = None,
        allowed_tenant_ids: list[str] | None = None,
    ) -> bool:
        """Update access control settings."""
        ...
```

## Value Objects

### KnowledgeTerm

```python
# domain/models/knowledge_term.py

@dataclass(frozen=True)
class KnowledgeTerm:
    """A domain-specific term with definition and metadata.

    Terms are the atomic units of knowledge. They have:
    - Canonical definition
    - Aliases for matching variations
    - Examples for context
    - Context hint for when to inject
    """
    id: str  # UUID
    term: str  # "ExamBlueprint"
    definition: str  # Markdown-supported
    aliases: tuple[str, ...]  # Frozen for immutability
    examples: tuple[str, ...]
    context_hint: str | None  # "When discussing exam structure"

    # Metadata
    created_at: datetime
    updated_at: datetime
    is_active: bool = True

    def matches(self, text: str) -> bool:
        """Check if this term or its aliases appear in text."""
        text_lower = text.lower()
        if self.term.lower() in text_lower:
            return True
        return any(alias.lower() in text_lower for alias in self.aliases)

    def to_context_block(self) -> str:
        """Format as a context injection block."""
        block = f"**{self.term}**: {self.definition}"
        if self.examples:
            block += f"\n  Examples: {', '.join(self.examples[:2])}"
        return block
```

### KnowledgeRelationship

```python
# domain/models/knowledge_relationship.py

@dataclass(frozen=True)
class KnowledgeRelationship:
    """Directed relationship between two terms.

    Relationship types:
    - contains: Parent contains child (ExamBlueprint contains ExamDomain)
    - references: Entity references another (ExamDomain references Skill)
    - is_instance_of: Concrete instance of abstract (Item is_instance_of Skill)
    - parent_of: Hierarchical parent
    - depends_on: Dependency relationship
    - related_to: General association
    """
    id: str
    source_term_id: str
    target_term_id: str
    relationship_type: str
    description: str | None
    bidirectional: bool
    weight: float  # For graph algorithms

    created_at: datetime
    is_active: bool = True
```

### KnowledgeRule

```python
# domain/models/knowledge_rule.py

@dataclass(frozen=True)
class KnowledgeRule:
    """Business rule or constraint in the domain.

    Rules are injected into context when their associated terms
    are detected in the user's query.
    """
    id: str
    name: str  # "Blueprint Domain Requirement"
    condition: str  # "When discussing ExamBlueprint structure"
    rule_text: str  # The actual rule content
    applies_to_term_ids: tuple[str, ...]
    priority: int  # Higher = inject first

    created_at: datetime
    updated_at: datetime
    is_active: bool = True

    def to_context_block(self) -> str:
        """Format as a rule injection block."""
        return f"**Rule - {self.name}**: {self.rule_text}"
```

### KnowledgeRevision

```python
# domain/models/knowledge_revision.py

@dataclass(frozen=True)
class KnowledgeRevision:
    """Snapshot of namespace state at a point in time.

    Revisions enable:
    - Audit trail of changes
    - Rollback to previous state
    - Branching (future)
    """
    revision_number: int
    message: str  # Commit message
    created_by: str
    created_at: datetime

    # Snapshot data
    term_snapshot: dict[str, dict]  # term_id -> term data
    relationship_snapshot: dict[str, dict]
    rule_snapshot: dict[str, dict]

    # Statistics at time of revision
    term_count: int
    relationship_count: int
    rule_count: int
```

## Domain Events

```python
# domain/events/knowledge_namespace.py

from neuroglia.eventing.cloud_events import cloudevent

@cloudevent("knowledge.namespace.created.v1")
@dataclass
class KnowledgeNamespaceCreatedDomainEvent(DomainEvent):
    aggregate_id: str
    name: str
    description: str
    owner_user_id: str | None
    owner_tenant_id: str | None
    created_at: datetime

@cloudevent("knowledge.namespace.updated.v1")
@dataclass
class KnowledgeNamespaceUpdatedDomainEvent(DomainEvent):
    aggregate_id: str
    name: str | None
    description: str | None
    icon: str | None
    updated_at: datetime

@cloudevent("knowledge.namespace.deleted.v1")
@dataclass
class KnowledgeNamespaceDeletedDomainEvent(DomainEvent):
    aggregate_id: str
    deleted_by: str
    deleted_at: datetime


# === Term Events ===

@cloudevent("knowledge.term.added.v1")
@dataclass
class KnowledgeTermAddedDomainEvent(DomainEvent):
    aggregate_id: str  # namespace_id
    term_id: str
    term: str
    definition: str
    aliases: list[str]
    examples: list[str]
    context_hint: str | None
    created_at: datetime

@cloudevent("knowledge.term.updated.v1")
@dataclass
class KnowledgeTermUpdatedDomainEvent(DomainEvent):
    aggregate_id: str
    term_id: str
    term: str | None
    definition: str | None
    aliases: list[str] | None
    examples: list[str] | None
    context_hint: str | None
    updated_at: datetime

@cloudevent("knowledge.term.removed.v1")
@dataclass
class KnowledgeTermRemovedDomainEvent(DomainEvent):
    aggregate_id: str
    term_id: str
    removed_at: datetime


# === Relationship Events ===

@cloudevent("knowledge.relationship.added.v1")
@dataclass
class KnowledgeRelationshipAddedDomainEvent(DomainEvent):
    aggregate_id: str
    relationship_id: str
    source_term_id: str
    target_term_id: str
    relationship_type: str
    description: str | None
    bidirectional: bool
    weight: float
    created_at: datetime

@cloudevent("knowledge.relationship.removed.v1")
@dataclass
class KnowledgeRelationshipRemovedDomainEvent(DomainEvent):
    aggregate_id: str
    relationship_id: str
    removed_at: datetime


# === Rule Events ===

@cloudevent("knowledge.rule.added.v1")
@dataclass
class KnowledgeRuleAddedDomainEvent(DomainEvent):
    aggregate_id: str
    rule_id: str
    name: str
    condition: str
    rule_text: str
    applies_to_term_ids: list[str]
    priority: int
    created_at: datetime

@cloudevent("knowledge.rule.updated.v1")
@dataclass
class KnowledgeRuleUpdatedDomainEvent(DomainEvent):
    aggregate_id: str
    rule_id: str
    name: str | None
    condition: str | None
    rule_text: str | None
    priority: int | None
    updated_at: datetime

@cloudevent("knowledge.rule.removed.v1")
@dataclass
class KnowledgeRuleRemovedDomainEvent(DomainEvent):
    aggregate_id: str
    rule_id: str
    removed_at: datetime


# === Revision Events ===

@cloudevent("knowledge.revision.created.v1")
@dataclass
class KnowledgeRevisionCreatedDomainEvent(DomainEvent):
    aggregate_id: str
    revision_number: int
    message: str
    created_by: str
    created_at: datetime
    term_count: int
    relationship_count: int
    rule_count: int

@cloudevent("knowledge.revision.rolledback.v1")
@dataclass
class KnowledgeRevisionRolledBackDomainEvent(DomainEvent):
    aggregate_id: str
    from_revision: int
    to_revision: int
    rolled_back_by: str
    rolled_back_at: datetime
```

## Repository Architecture

### Multi-Dimensional Repository Pattern

The knowledge-manager extends Neuroglia's repository pattern to support multiple storage dimensions:

```python
# domain/repositories/knowledge_namespace_repository.py

from abc import ABC, abstractmethod
from typing import Any

class KnowledgeNamespaceRepository(ABC):
    """Repository interface for KnowledgeNamespace aggregate.

    Implementations must coordinate writes across:
    1. EventStoreDB (event sourcing - source of truth)
    2. MongoDB (read model projections)
    3. Neo4j (graph relationships)
    4. Vector Store (term embeddings)
    """

    @abstractmethod
    async def get_async(self, namespace_id: str) -> KnowledgeNamespace | None:
        """Load aggregate by rehydrating from events."""
        ...

    @abstractmethod
    async def add_async(self, namespace: KnowledgeNamespace) -> None:
        """Persist new aggregate and publish events."""
        ...

    @abstractmethod
    async def update_async(self, namespace: KnowledgeNamespace) -> None:
        """Persist changes and publish events."""
        ...

    @abstractmethod
    async def delete_async(self, namespace_id: str) -> None:
        """Delete aggregate (soft delete via event)."""
        ...


class KnowledgeNamespaceDtoRepository(ABC):
    """Read model repository for queryable projections."""

    @abstractmethod
    async def get_by_tenant_async(self, tenant_id: str) -> list[KnowledgeNamespaceDto]:
        """Get all namespaces accessible by tenant."""
        ...

    @abstractmethod
    async def search_terms_async(
        self,
        query: str,
        namespace_ids: list[str],
        limit: int = 10,
    ) -> list[KnowledgeTermDto]:
        """Search terms by text (keyword matching)."""
        ...


class KnowledgeGraphRepository(ABC):
    """Graph-specific operations for relationship traversal."""

    @abstractmethod
    async def traverse_relationships(
        self,
        term_id: str,
        relationship_types: list[str] | None = None,
        direction: str = "outgoing",  # "outgoing", "incoming", "both"
        max_depth: int = 2,
    ) -> list[dict]:
        """Traverse graph from a starting term."""
        ...

    @abstractmethod
    async def find_paths(
        self,
        source_term_id: str,
        target_term_id: str,
        max_length: int = 5,
    ) -> list[list[dict]]:
        """Find all paths between two terms."""
        ...

    @abstractmethod
    async def get_community(
        self,
        term_id: str,
        algorithm: str = "louvain",
    ) -> list[dict]:
        """Get the community/cluster a term belongs to."""
        ...


class KnowledgeVectorRepository(ABC):
    """Vector-specific operations for semantic search."""

    @abstractmethod
    async def search_similar(
        self,
        embedding: list[float],
        namespace_ids: list[str],
        limit: int = 10,
        min_score: float = 0.7,
    ) -> list[tuple[KnowledgeTermDto, float]]:
        """Search terms by embedding similarity."""
        ...

    @abstractmethod
    async def update_embedding(
        self,
        term_id: str,
        embedding: list[float],
    ) -> None:
        """Update the embedding for a term."""
        ...
```

## Projection Handlers

Event handlers that maintain read models across multiple stores:

```python
# application/events/knowledge_projection_handler.py

class KnowledgeProjectionHandler:
    """Handles domain events to update read models.

    Maintains consistency across:
    - MongoDB (namespace/term/rule documents)
    - Neo4j (graph nodes and edges)
    - Vector Store (term embeddings)
    """

    def __init__(
        self,
        mongo_repo: KnowledgeNamespaceDtoRepository,
        graph_repo: KnowledgeGraphRepository,
        vector_repo: KnowledgeVectorRepository,
        embedding_service: EmbeddingService,
    ):
        ...

    async def handle(self, event: DomainEvent) -> None:
        """Route event to appropriate handler."""
        ...

    async def _on_term_added(self, event: KnowledgeTermAddedDomainEvent) -> None:
        """Handle term addition across all stores."""
        # 1. Create MongoDB document
        await self._mongo_repo.add_term(...)

        # 2. Create Neo4j node
        await self._graph_repo.create_term_node(...)

        # 3. Generate and store embedding
        text = f"{event.term}: {event.definition}"
        embedding = await self._embedding_service.embed(text)
        await self._vector_repo.store_embedding(event.term_id, embedding)

    async def _on_relationship_added(
        self, event: KnowledgeRelationshipAddedDomainEvent
    ) -> None:
        """Handle relationship addition."""
        # 1. Update MongoDB
        await self._mongo_repo.add_relationship(...)

        # 2. Create Neo4j edge
        await self._graph_repo.create_edge(
            source_id=event.source_term_id,
            target_id=event.target_term_id,
            edge_type=event.relationship_type,
            properties={"weight": event.weight, "description": event.description},
        )
```

---

_Next: [02-api-contracts.md](02-api-contracts.md) - REST API Design_
