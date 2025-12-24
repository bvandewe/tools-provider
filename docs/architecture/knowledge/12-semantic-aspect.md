# Semantic Aspect: "The Map"

## Purpose

The Semantic Aspect projects **all entities and their relationships** into a **Knowledge & Social Graph**, enabling the AI to understand:

- **Entity Relationships**: Interdependencies between any entities over time
- **Blueprint Topology**: How Topics relate within ExamBlueprints, prerequisite chains
- **User Context**: What users know (mastery), what they're struggling with, who they're connected to
- **Performance Correlations**: KPI patterns across Candidates via similarity search and statistical analysis
- **Resource Coverage**: Which concepts are well-covered vs. gaps in learning materials

## Scope: Beyond User-Focused

Unlike typical user-profile systems, the Semantic Aspect models **relationships between any entities**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SEMANTIC ASPECT: ENTITY RELATIONSHIPS                     │
│                                                                              │
│  ┌──────────────────────┐   ┌──────────────────────┐   ┌──────────────────────┐│
│  │  BLUEPRINT TOPOLOGY  │   │    USER CONTEXT      │   │ PERFORMANCE ANALYSIS ││
│  │                      │   │                      │   │                      ││
│  │  Topic ←→ Topic      │   │  User ←→ Skill      │   │  Candidate ←→ KPI    ││
│  │  Concept ←→ Concept  │   │  User ←→ Concept    │   │  Exam ←→ PassRate    ││
│  │  Skill ←→ Skill      │   │  User ←→ User       │   │  Topic ←→ Difficulty ││
│  │  Resource ←→ Concept │   │  User ←→ Cohort     │   │  Time ←→ Completion  ││
│  └──────────────────────┘   └──────────────────────┘   └──────────────────────┘│
│                              │                              │               │
│                              ▼                              ▼               │
│                    ┌────────────────────────────────────────────┐              │
│                    │      UNIFIED GRAPH (Neo4j)                 │              │
│                    │                                            │              │
│                    │  Nodes: User, Skill, Concept, Blueprint,   │              │
│                    │         Topic, Resource, Cohort, Exam...   │              │
│                    │                                            │              │
│                    │  Edges: PREREQUISITE_FOR, MASTERED,        │              │
│                    │         TEACHES, CORRELATES_WITH,          │              │
│                    │         PREDICTS_SUCCESS_IN...              │              │
│                    └────────────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Temporal Versioning on Nodes and Edges

Graphs and Vectors include **temporal attributes** that enable revisions of entities over time, mirroring how versioned DomainEvents map to Node/Edge/Vector revisions:

### Node Revision Model

```cypher
// Every node has revision tracking
(:Concept {
  id: string,
  namespace_id: string,
  name: string,
  description: string,

  // Temporal attributes
  revision: int,                    // Monotonically increasing version
  revision_timestamp: datetime,     // When this version was created
  source_event_id: string,          // DomainEvent that caused this revision

  // Vector embedding with revision
  embedding: list[float],
  embedding_revision: int,

  // Lifecycle
  created_at: datetime,
  created_by: string,
  is_current: boolean,              // Only latest revision is current
  deleted_at: datetime | null       // Soft delete timestamp
})

// Historical revisions stored as separate nodes
(:ConceptRevision {
  concept_id: string,
  revision: int,
  snapshot: map,                    // Full state at this revision
  changed_fields: list[string],     // What changed from previous
  source_event_id: string,
  timestamp: datetime
})

// Link current node to its revision history
(:Concept)-[:HAS_REVISION {revision: 3}]->(:ConceptRevision)
```

### Edge Revision Model

```cypher
// Edges also have revision tracking
(:Concept)-[:PREREQUISITE_FOR {
  id: string,
  strength: float,                  // 0.0 - 1.0

  // Temporal attributes
  revision: int,
  created_at: datetime,
  modified_at: datetime,
  source_event_id: string,

  // Validity window (bi-temporal)
  valid_from: datetime,
  valid_until: datetime | null,     // null = currently valid

  // Audit
  created_by: string,
  is_current: boolean
}]->(:Concept)
```

### Time-Travel Queries

```cypher
// Query: What were the prerequisites for "Decorators" on December 1st?
MATCH (c:Concept {name: "Decorators"})<-[r:PREREQUISITE_FOR]-(prereq:Concept)
WHERE r.valid_from <= datetime("2024-12-01")
  AND (r.valid_until IS NULL OR r.valid_until > datetime("2024-12-01"))
RETURN prereq.name, r.strength, r.revision

// Query: How has the skill graph evolved over the last 6 months?
MATCH (s:SkillRevision)
WHERE s.timestamp > datetime() - duration('P6M')
RETURN s.skill_id, s.revision, s.changed_fields, s.timestamp
ORDER BY s.timestamp
```

## Persistence Strategy

The Semantic Aspect uses **State-Based Persistence** with the Neuroglia `MotorRepository` pattern:

### SemanticProfile Aggregate

```python
class SemanticProfileState(AggregateState[str]):
    """State persisted to MongoDB, synced to Neo4j."""

    # Identity
    id: str
    user_id: str
    tenant_id: str

    # Mastery (denormalized for fast queries)
    mastered_skill_ids: list[str]
    learning_skill_ids: list[str]
    struggling_concept_ids: list[str]

    # Social (denormalized)
    mentor_user_ids: list[str]
    mentee_user_ids: list[str]
    cohort_ids: list[str]

    # Timestamps
    created_at: datetime
    last_modified: datetime
    state_version: int  # Optimistic concurrency

class SemanticProfile(AggregateRoot[SemanticProfileState, str]):
    """
    Aggregate managing user's semantic context.

    Persistence: State-based (MongoDB via MotorRepository)
    Graph Sync: Changes emit events that sync to Neo4j
    """

    def record_mastery(self, skill_id: str, confidence: float, source: str) -> None:
        if skill_id not in self.state.mastered_skill_ids:
            self.state.mastered_skill_ids.append(skill_id)
            # Remove from learning if present
            if skill_id in self.state.learning_skill_ids:
                self.state.learning_skill_ids.remove(skill_id)
        self.register_event(MasteryRecordedDomainEvent(
            aggregate_id=self.id(),
            skill_id=skill_id,
            confidence=confidence,
            source=source
        ))

    def detect_struggle(self, concept_id: str, attempt_count: int) -> None:
        if concept_id not in self.state.struggling_concept_ids:
            self.state.struggling_concept_ids.append(concept_id)
        self.register_event(StruggleDetectedDomainEvent(
            aggregate_id=self.id(),
            concept_id=concept_id,
            attempt_count=attempt_count
        ))
```

### Domain Events (CloudEvents, Not Persisted)

```python
@cloudevent("semantic.mastery.recorded.v1")
class MasteryRecordedDomainEvent(DomainEvent):
    skill_id: str
    confidence: float
    source: str  # "assessment", "self_reported", "inferred"

@cloudevent("semantic.struggle.detected.v1")
class StruggleDetectedDomainEvent(DomainEvent):
    concept_id: str
    attempt_count: int
```

**Key Pattern**: Events are published as CloudEvents for external observability but NOT persisted to EventStoreDB. The aggregate state in MongoDB is the source of truth.

## Role-Specific Graph Projections

Each user role sees a different view of the same underlying graph:

### Candidate View

```cypher
// What the Candidate sees: their own mastery and available mentors
MATCH (u:User {id: $user_id})-[r:MASTERED|LEARNING|STRUGGLING_WITH]->(node)
RETURN node, type(r), r.confidence_score

MATCH (u:User {id: $user_id})-[:MEMBER_OF]->(:Cohort)<-[:MEMBER_OF]-(peer:User)
WHERE (peer)-[:MASTERED]->(:Skill)<-[:STRUGGLING_WITH]-(u)
RETURN peer.display_name, peer.id
```

### Author View

```cypher
// What the Author sees: content coverage and prerequisite chains
MATCH (c:Concept)-[:PREREQUISITE_FOR*1..3]->(target:Concept)
WHERE c.namespace_id = $namespace_id
RETURN c, target, length(path) as depth

// Gap analysis: concepts without resources
MATCH (c:Concept)
WHERE c.namespace_id = $namespace_id
AND NOT (c)<-[:TEACHES]-(:Resource)
RETURN c.name as uncovered_concept
```

### Analyst View

```cypher
// What the Analyst sees: anonymized aggregates only
MATCH (u:User)-[r:STRUGGLING_WITH]->(c:Concept)
WHERE c.namespace_id = $namespace_id
WITH c, count(u) as struggle_count
RETURN c.name, struggle_count
ORDER BY struggle_count DESC
LIMIT 10
```

## Neo4j Vector Search Integration

Neo4j 5.11+ supports native vector indexes, enabling unified Graph + Vector queries:

### Index Creation

```cypher
// Create vector index on Concept embeddings
CREATE VECTOR INDEX concept_embedding_idx IF NOT EXISTS
FOR (c:Concept)
ON (c.embedding)
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 384,
    `vector.similarity_function`: 'cosine'
  }
}
```

## Blueprint Topic Interdependencies

The Semantic Aspect models relationships **between Topics within ExamBlueprints**:

```cypher
// Blueprint contains Topics with weighted relationships
(:ExamBlueprint {
  id: string,
  name: string,
  version: string,
  namespace_id: string
})-[:CONTAINS {weight: float, section: string}]->(:Topic {
  id: string,
  name: string,
  difficulty_level: int,
  cognitive_level: string  // "remember", "understand", "apply", "analyze"
})

// Topics have prerequisite chains
(:Topic)-[:PREREQUISITE_FOR {
  strength: float,
  is_strict: boolean,       // Must complete before vs. recommended
  revision: int
}]->(:Topic)

// Topics map to underlying Concepts
(:Topic)-[:COVERS {
  depth: string,            // "intro", "intermediate", "advanced"
  assessment_weight: float
}]->(:Concept)
```

### Topic Dependency Analysis

```cypher
// Find all prerequisite chains for a Topic (transitive closure)
MATCH path = (root:Topic)-[:PREREQUISITE_FOR*1..5]->(target:Topic {id: $topic_id})
WHERE root.blueprint_id = $blueprint_id
RETURN root, relationships(path), target,
       reduce(s = 1.0, r IN relationships(path) | s * r.strength) as chain_strength
ORDER BY length(path), chain_strength DESC

// Identify Topic clusters (strongly connected components)
CALL gds.scc.stream('topic-graph', {relationshipTypes: ['PREREQUISITE_FOR']})
YIELD nodeId, componentId
MATCH (t:Topic) WHERE id(t) = nodeId
RETURN componentId, collect(t.name) as topics_in_cluster
```

## Performance Correlation Analysis (KPIs)

The Semantic Aspect enables **statistical and probabilistic analysis** of Candidate performance by integrating with external analytical engines:

### KPI Graph Model

```cypher
// Anonymized performance metrics (no PII)
(:CandidateProfile {
  id: string,               // Anonymized ID
  cohort_id: string,

  // Aggregate KPIs (denormalized for query performance)
  avg_completion_time_minutes: float,
  avg_score_percent: float,
  attempt_count: int,
  topic_struggle_ids: list[string],

  // Embedding for similarity search
  performance_embedding: list[float],
  embedding_revision: int
})

// Topic-level performance
(:CandidateProfile)-[:PERFORMED_ON {
  score_percent: float,
  time_spent_minutes: int,
  attempt_count: int,
  last_attempt: datetime
}]->(:Topic)

// Correlation edges discovered by analytics
(:Topic)-[:CORRELATES_WITH {
  correlation_coefficient: float,  // -1.0 to 1.0
  sample_size: int,
  confidence: float,
  computed_at: datetime,
  revision: int
}]->(:Topic)

// Predictive edges
(:Topic)-[:PREDICTS_SUCCESS_IN {
  probability: float,
  model_version: string,
  computed_at: datetime
}]->(:ExamBlueprint)
```

### Similarity Search for Candidate Patterns

```cypher
// Find candidates with similar performance profiles (for cohort analysis)
CALL db.index.vector.queryNodes(
  'candidate_performance_idx',
  10,
  $candidate_embedding
)
YIELD node AS similar_candidate, score
WHERE similar_candidate.id <> $current_candidate_id

// What topics did similar successful candidates excel at?
MATCH (similar_candidate)-[p:PERFORMED_ON]->(t:Topic)
WHERE p.score_percent > 0.8
RETURN t.name, avg(p.score_percent) as avg_score, count(*) as candidate_count
ORDER BY candidate_count DESC
```

### External Analytics Integration

For complex statistical/probabilistic analysis, the Semantic Aspect delegates to external engines:

```python
# integration/services/analytics_client.py

from dataclasses import dataclass
from typing import Protocol

@dataclass
class CorrelationRequest:
    """Request for topic correlation analysis."""
    blueprint_id: str
    topic_ids: list[str]
    metric: str  # "score", "time", "attempts"
    min_sample_size: int = 30

@dataclass
class CorrelationResult:
    """Result from correlation analysis."""
    topic_a: str
    topic_b: str
    correlation: float
    p_value: float
    sample_size: int
    confidence_interval: tuple[float, float]

class AnalyticsEngine(Protocol):
    """Protocol for external statistical/probabilistic analytics."""

    async def compute_correlations(
        self, request: CorrelationRequest
    ) -> list[CorrelationResult]:
        """Compute pairwise correlations between topics."""
        ...

    async def query_event_store(
        self, query: str, params: dict
    ) -> list[dict]:
        """Query the event store for historical analysis."""
        ...

    async def similarity_cluster(
        self, embeddings: list[list[float]], n_clusters: int
    ) -> list[int]:
        """Cluster embeddings for cohort discovery."""
        ...
```

### EventStore Query Integration

The Semantic Aspect can query the **event store** for historical analysis:

```python
# Query: What's the success rate for candidates who struggled with Topic X first?
event_query = """
SELECT
    e1.aggregate_id as candidate_id,
    e2.data->>'passed' as exam_passed
FROM events e1
JOIN events e2 ON e1.aggregate_id = e2.aggregate_id
WHERE e1.event_type = 'candidate.topic.struggled.v1'
  AND e1.data->>'topic_id' = $topic_id
  AND e2.event_type = 'candidate.exam.completed.v1'
  AND e2.data->>'blueprint_id' = $blueprint_id
  AND e2.timestamp > e1.timestamp
"""

results = await analytics.query_event_store(event_query, {
    "topic_id": "topic-decorators",
    "blueprint_id": "python-senior",
})

success_rate = sum(1 for r in results if r["exam_passed"]) / len(results)
```

```

### Hybrid Query: Semantic + Graph

```cypher
// Find concepts similar to user query, then traverse prerequisites
WITH $query_embedding AS query_vec
CALL db.index.vector.queryNodes('concept_embedding_idx', 5, query_vec)
YIELD node AS similar_concept, score

// Enrich with prerequisite context
MATCH (prereq:Concept)-[:PREREQUISITE_FOR]->(similar_concept)
OPTIONAL MATCH (user:User {id: $user_id})-[mastery:MASTERED]->(prereq)

RETURN similar_concept.name,
       score as similarity,
       prereq.name as prerequisite,
       CASE WHEN mastery IS NOT NULL THEN 'mastered' ELSE 'not_mastered' END as user_status
ORDER BY score DESC
```

## Graph Schema

### Nodes

```cypher
(:User {
  id: string,
  tenant_id: string,
  display_name: string,
  learning_style: string,  // "visual", "auditory", "kinesthetic"
  created_at: datetime
})

(:Skill {
  id: string,
  namespace_id: string,
  name: string,            // "Python", "Networking"
  category: string,
  difficulty_level: int    // 1-5
})

(:Concept {
  id: string,
  namespace_id: string,
  name: string,            // "Recursion", "Closures"
  parent_skill_id: string,
  description: string
})

(:Resource {
  id: string,
  type: string,            // "video", "article", "exercise"
  title: string,
  url: string,
  duration_minutes: int,
  difficulty_level: int
})

(:Cohort {
  id: string,
  name: string,
  start_date: date,
  end_date: date
})
```

### Relationships (Edges)

```cypher
// Mastery relationships
(:User)-[:MASTERED {
  achieved_at: datetime,
  confidence_score: float,  // 0.0 - 1.0
  certification_id: string
}]->(:Skill)

(:User)-[:STRUGGLING_WITH {
  detected_at: datetime,
  attempt_count: int,
  last_attempt: datetime
}]->(:Concept)

(:User)-[:LEARNING {
  started_at: datetime,
  progress_percent: float,
  current_concept_id: string
}]->(:Skill)

// Knowledge structure
(:Concept)-[:PREREQUISITE_FOR {
  strength: float  // How critical is this prereq
}]->(:Concept)

(:Skill)-[:CONTAINS]->(:Concept)
(:Resource)-[:TEACHES]->(:Concept)

// Social relationships
(:User)-[:MENTORED_BY {
  since: datetime,
  topic_skill_id: string
}]->(:User)

(:User)-[:MEMBER_OF {
  joined_at: datetime,
  role: string  // "student", "mentor", "instructor"
}]->(:Cohort)

(:User)-[:COMPLETED {
  completed_at: datetime,
  score: float,
  time_spent_minutes: int
}]->(:Resource)

(:User)-[:NEEDS_MENTORING_IN]->(:Skill)
```

## AI Benefit: Zero-Shot Context Awareness

The AI queries the graph instead of asking the user for context.

### Example: Reactive Support (Tutor Role)

**User Query**: "I don't understand Decorators in Python."

**AI Action**:

```cypher
MATCH (u:User {id: $user_id})-[r]->(c:Concept)
WHERE c.name = 'Decorators' OR c.name IN ['Closures', 'Functions', 'First-Class Functions']
RETURN c.name, type(r), r.confidence_score
```

**Graph Response**:

- `(User)-[:MASTERED {confidence: 0.9}]->(Functions)`
- `(User)-[:STRUGGLING_WITH {attempts: 3}]->(Closures)`
- No edge to `Decorators` (never attempted)

**AI Response**:
> "Since you already know Functions but struggled with Closures, let's review Closures first—they're the building block for Decorators."

### Example: Proactive Support (Connector Role)

**Trigger**: User completes a certification.

**AI Action**:

```cypher
MATCH (u:User {id: $user_id})-[:MASTERED]->(s:Skill)
MATCH (peer:User)-[:NEEDS_MENTORING_IN]->(s)
WHERE peer.id <> u.id AND (peer)-[:MEMBER_OF]->(:Cohort)<-[:MEMBER_OF]-(u)
RETURN peer.display_name, s.name
LIMIT 3
```

**AI Response**:
> "Congratulations on your certification! I found 3 peers in your cohort who are struggling with this topic. Would you like to mentor one of them to reinforce your learning?"

## API Endpoints

### Query User Mastery

```
GET /semantic/users/{user_id}/mastery
Response: {
  mastered_skills: [...],
  learning_skills: [...],
  struggling_concepts: [...]
}
```

### Record Mastery Event

```
POST /semantic/users/{user_id}/mastery
Body: { skill_id, confidence_score, source: "assessment|self-reported|inferred" }
```

### Query Prerequisites

```
GET /semantic/concepts/{concept_id}/prerequisites
Query: ?depth=2
Response: {
  prerequisites: [
    { concept: "Closures", strength: 0.9, user_status: "struggling" },
    { concept: "Functions", strength: 0.7, user_status: "mastered" }
  ]
}
```

### Find Mentors

```
GET /semantic/users/{user_id}/mentors?skill_id={skill_id}
Response: {
  available_mentors: [...],
  suggested_peers: [...]
}
```

## Event Sources

The semantic graph is updated from:

| Source | Events |
|--------|--------|
| **Assessments** | `quiz_completed`, `exam_passed`, `certification_earned` |
| **Activity** | `resource_completed`, `exercise_submitted`, `conversation_ended` |
| **Inference** | `struggle_detected`, `mastery_inferred`, `learning_velocity_calculated` |
| **Social** | `mentor_assigned`, `cohort_joined`, `peer_helped` |

## Integration with Context Expander

When building the context vector, the semantic aspect contributes:

```python
semantic_context = {
    "user_mastery": ["Functions", "Loops", "Conditionals"],
    "user_struggles": ["Closures"],
    "relevant_prereqs": ["Closures is prerequisite for Decorators"],
    "social_context": "User has 2 peers also learning Decorators"
}
```

---

_Next: [13-intentional-aspect.md](13-intentional-aspect.md) - Goals & Plans_
