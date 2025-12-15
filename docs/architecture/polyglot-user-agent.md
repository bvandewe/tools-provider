# Polyglot Entity Model: Stateful Users and Agents

**Version:** 1.0.0
**Status:** `DRAFT`
**Date:** December 15, 2025
**Application:** agent-host (primary), tools-provider (extension)

---

## 1. Executive Summary

This document defines the architecture for extending the **User** and **Agent** entities with multi-dimensional aspects, enabling **stateful, context-aware AI agents** that continuously adapt to users based on:

1. **Semantic Aspect** ("The Map") - Knowledge & Social Graph
2. **Intentional Aspect** ("The Compass") - Goals & Plans with Spec/Status reconciliation
3. **Observational Aspect** ("The Pulse") - Telemetry for empathy & adaptation

### The Vision

> A "Session" is not just a chat window. It is a **Reconciliation Loop** where an AI Agent continuously observes a Human User's Telemetry, references their Graph, and steers them toward their Intent.

### Why This Matters

Standard LLMs fail at personalization because they lack structured context. By feeding the LLM a context vector of `[GraphNode, Spec, Telemetry]`, we:

- Reduce hallucinations through grounded, user-specific context
- Enable proactive support (agent initiates based on observations)
- Maintain alignment between user intent and agent behavior
- Create psychological safety through empathy-aware interactions

---

## 2. The Three Aspects

### 2.1 Aspect Overview

| Aspect | Metaphor | Purpose | Data Store | Query Pattern |
|--------|----------|---------|------------|---------------|
| **Semantic** | "The Map" | Context & Connection | Neo4j | Graph traversal |
| **Intentional** | "The Compass" | Goals & Plans | Redis | Spec/Status comparison |
| **Observational** | "The Pulse" | Empathy & Adaptation | InfluxDB/Redis | Time-series analysis |

### 2.2 Semantic Aspect: "The Map"

The Semantic Aspect projects the **User** and **Agent** into a Knowledge & Social Graph.

#### Graph Model

```cypher
// User nodes with skills, knowledge, relationships
(:User {id, name, created_at})
(:Skill {id, name, category})
(:Concept {id, name, domain})
(:Resource {id, name, type, url})
(:Agent {id, name, blueprint_id})

// User relationships
(User)-[:MASTERED]->(Skill)
(User)-[:STRUGGLING_WITH]->(Concept)
(User)-[:COMPLETED]->(Resource)
(User)-[:MENTORED_BY]->(User)
(User)-[:PREFERS]->(Agent)

// Agent relationships
(Agent)-[:SPECIALIZES_IN]->(Skill)
(Agent)-[:REQUIRES]->(Tool)
(Agent)-[:ASSIGNED_TO]->(User)
```

#### AI Use Cases

**Reactive Support (Tutor Role):**

```
User Query: "I don't understand 'Decorators' in Python."
AI Action: Query Graph for user's prior knowledge
Insight: (User)-[:MASTERED]->(Functions) but (User)-[:STRUGGLING_WITH]->(Closures)
Response: "Since you know Functions but struggled with Closures, let's review
          Closures first, as they are the building block for Decorators."
```

**Proactive Support (Connector Role):**

```
Trigger: User completes a certification
AI Action: Scan Graph for (UserB)-[:NEEDS_MENTORING_IN]->(Skill)
Response: "Congratulations! I found 3 peers struggling with this topic.
          Would you like to mentor one of them?"
```

#### Domain Model

```python
# domain/aspects/semantic_aspect.py

from dataclasses import dataclass
from typing import Any


@dataclass
class GraphNode:
    """Entity representation in the knowledge graph."""
    entity_id: str
    entity_type: str  # User, Agent, Skill, etc.
    labels: list[str]
    properties: dict[str, Any]


@dataclass
class GraphEdge:
    """Relationship between entities."""
    from_id: str
    to_id: str
    relation_type: str  # MASTERED, STRUGGLING_WITH, etc.
    properties: dict[str, Any]


@dataclass
class SemanticAspect:
    """The Map - User/Agent position in the knowledge graph."""
    node: GraphNode
    inbound_edges: list[GraphEdge]  # Relationships TO this entity
    outbound_edges: list[GraphEdge]  # Relationships FROM this entity

    def get_related(self, relation_type: str) -> list[str]:
        """Get entity IDs related by a specific relation."""
        return [
            edge.to_id for edge in self.outbound_edges
            if edge.relation_type == relation_type
        ]
```

### 2.3 Intentional Aspect: "The Compass"

The Intentional Aspect acts as a **Kubernetes Manifest for Goals**. It defines "Desired State" (Spec) vs "Actual Status" and uses reconciliation to close the gap.

#### Spec/Status Model

```python
# domain/aspects/intentional_aspect.py

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class IntentStatus(str, Enum):
    """Reconciliation state of an intent."""
    ALIGNED = "aligned"       # Status matches Spec
    DRIFTING = "drifting"     # Minor deviation
    DIVERGED = "diverged"     # Significant gap
    STALLED = "stalled"       # No progress detected


@dataclass
class Condition:
    """Status condition (K8s pattern)."""
    type: str                # e.g., "OnTrack", "Blocked", "Completed"
    status: bool
    reason: str
    message: str
    last_transition_time: datetime


@dataclass
class IntentSpec:
    """Desired state declaration for a goal/plan."""
    goal_id: str
    goal_type: str           # CertificationTrack, LearningPath, Project
    target_state: str        # The desired outcome
    target_date: datetime | None
    constraints: dict        # weekly_commitment, learning_style, etc.
    revision: int            # Incremented on spec change


@dataclass
class IntentStatus:
    """Observed actual state toward a goal."""
    current_state: str
    completion_percentage: float
    velocity: float          # Progress rate (e.g., hours/week)
    conditions: list[Condition]
    last_reconciled_at: datetime
    observed_revision: int   # Which spec revision was reconciled


@dataclass
class IntentionalAspect:
    """The Compass - Goals, plans, and reconciliation state."""
    entity_id: str
    entity_type: str         # User, Agent, Session
    intents: list[tuple[IntentSpec, IntentStatus]]
    mode: str                # "learning", "exam", "exploration"

    def is_drifting(self, intent_id: str) -> bool:
        """Check if an intent is drifting from spec."""
        for spec, status in self.intents:
            if spec.goal_id == intent_id:
                return status.velocity < spec.constraints.get("weekly_commitment", 0)
        return False
```

#### AI Use Cases

**Reactive Support (Coach Role):**

```
User Action: Requests to skip a difficult module
AI Action: Check Spec - is this module a hard_requirement?
Insight: Spec says mode="certification", module is critical
Response: "I can't let you skip this. Your goal is 'Senior Architect',
          and this module is critical for the final exam.
          Let's break it down into smaller pieces instead."
```

**Proactive Support (Planner Role):**

```
Trigger: IntentStatus.velocity drops below Spec.weekly_commitment
AI Action: Detect drift (Intent vs Reality)
Response: "I noticed you've only logged 2 hours this week, but your plan
          requires 5 hours to hit your December deadline. I've re-optimized
          your schedule: if you do 30 mins tonight, we get back on track."
```

#### Reconciliation Loop

```python
# application/reconciliation/intent_reconciliator.py

class IntentReconciliator:
    """Kubernetes-style reconciliation for user intents."""

    async def reconcile(self, user_id: str) -> list[ReconciliationAction]:
        """Compare spec vs status and generate actions."""
        intentional = await self._intent_repo.get_aspect(user_id)
        actions = []

        for spec, status in intentional.intents:
            if status.observed_revision < spec.revision:
                # Spec was updated, need to re-plan
                actions.append(ReplanAction(spec, status))

            elif self._is_drifting(spec, status):
                # Status is drifting from spec
                actions.append(NudgeAction(spec, status))

            elif self._is_stalled(status):
                # No progress detected
                actions.append(CheckInAction(spec, status))

        return actions

    def _is_drifting(self, spec: IntentSpec, status: IntentStatus) -> bool:
        target_velocity = spec.constraints.get("weekly_commitment", 0)
        return status.velocity < target_velocity * 0.8  # 20% tolerance

    def _is_stalled(self, status: IntentStatus) -> bool:
        days_since_progress = (datetime.now() - status.last_reconciled_at).days
        return days_since_progress > 7
```

### 2.4 Observational Aspect: "The Pulse"

The Observational Aspect processes **high-frequency, ephemeral telemetry** to enable empathy and real-time adaptation.

#### Telemetry Model

```python
# domain/aspects/observational_aspect.py

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class TelemetryPoint:
    """Single observation from user behavior."""
    metric_name: str         # TimeOnTask, ClickRageCount, etc.
    value: float
    timestamp: datetime
    tags: dict[str, str]     # session_id, resource_id, etc.


@dataclass
class TelemetryWindow:
    """Aggregated observations over a time window."""
    window_start: datetime
    window_end: datetime
    metrics: dict[str, float]  # Aggregated values
    anomalies: list[str]       # Detected anomalies


@dataclass
class CognitiveState:
    """Inferred cognitive/emotional state from telemetry."""
    engagement_level: float    # 0.0 (disengaged) to 1.0 (focused)
    frustration_level: float   # 0.0 (calm) to 1.0 (frustrated)
    fatigue_level: float       # 0.0 (fresh) to 1.0 (exhausted)
    confusion_level: float     # 0.0 (clear) to 1.0 (lost)
    confidence: float          # Inference confidence


@dataclass
class ObservationalAspect:
    """The Pulse - Real-time empathy and adaptation."""
    entity_id: str
    session_id: str
    current_window: TelemetryWindow
    cognitive_state: CognitiveState
    intervention_history: list[dict]  # Past interventions in this session
```

#### Metrics Collected

| Metric | Description | Inference |
|--------|-------------|-----------|
| `TimeOnTask` | Duration on current activity | Engagement |
| `IdleTime` | Seconds without input | Stuck/Distracted |
| `SeekRate` | Video rewind frequency | Confusion |
| `TypingSpeed` | Characters per minute | Fatigue |
| `TypingErrorRate` | Errors per minute | Frustration/Fatigue |
| `ClickRageCount` | Rapid repeated clicks | Frustration |
| `SessionDuration` | Total session length | Fatigue risk |

#### AI Use Cases

**Reactive Support (Facilitator Role):**

```
Observation: User pausing video every 10 seconds, rewinding (High SeekRate)
AI Inference: Cognitive overload / Confusion
Response: "This section seems dense. I've paused the video.
          Here is a simple diagram summarizing the last 2 minutes.
          Does this help?"
```

**Proactive Support (Wellness Role):**

```
Observation: SessionDuration > 90 mins AND TypingErrorRate spiking
AI Inference: Fatigue
Response: "You're grinding hard, but your error rate is climbing.
          Science says you've hit the point of diminishing returns.
          I'm locking the session for 15 minutes. Go take a walk!"
```

---

## 3. The Integrated Session Loop

How the three aspects work together in a single interaction:

### Scenario: User Struggling with a Coding Exercise

```
1. OBSERVATIONAL (The Pulse)
   Input: User has not typed for 45 seconds. Focus window is lost.
   Agent: Wakes up. "User is stuck."

2. SEMANTIC (The Map)
   Input: Agent queries Graph. "What is this exercise testing?"
          → ListComprehensions. "Does the user know prerequisites?" → Yes.
   Agent: "They have the knowledge, so this is likely a syntax error
           or logic block, not a conceptual gap."

3. INTENTIONAL (The Compass)
   Input: Agent checks Spec. "Is user in 'Exploration Mode' or 'Exam Mode'?"
   Spec: mode = "Learning"
   Agent: "I am allowed to give hints. If mode was 'Exam',
           I would only be allowed to encourage."

4. FINAL ACTION
   Agent: "You've been quiet for a minute. Remember, a List Comprehension
           always starts with the expression, not the loop.
           Want to see the syntax template again?"
```

---

## 4. Domain Model: Polyglot User

### 4.1 User Aggregate with Aspects

```python
# domain/entities/user.py (agent-host)

from neuroglia.data.abstractions import AggregateRoot, AggregateState
from domain.aspects import SemanticAspect, IntentionalAspect, ObservationalAspect


class UserState(AggregateState[str]):
    """State for the User aggregate."""
    id: str
    email: str
    name: str
    preferences: dict

    # Aspect snapshots (denormalized for fast access)
    active_intents: list[str]  # IDs of current goals
    current_mode: str          # learning, exam, exploration

    created_at: datetime
    updated_at: datetime


class User(AggregateRoot[UserState, str]):
    """Multi-dimensional User aggregate.

    The User exists across three aspects:
    - Semantic: Graph node with skills, relationships
    - Intentional: Goals/plans with spec/status
    - Observational: Session telemetry (ephemeral, not persisted)
    """

    def set_goal(self, goal_type: str, target: str, target_date: datetime, constraints: dict):
        """Create or update a goal (Intent Spec)."""
        self.state.on(
            self.register_event(
                UserGoalSetDomainEvent(
                    aggregate_id=self.id(),
                    goal_type=goal_type,
                    target=target,
                    target_date=target_date,
                    constraints=constraints,
                )
            )
        )

    def add_skill(self, skill_id: str, mastery_level: str):
        """Add a skill relationship to graph."""
        self.state.on(
            self.register_event(
                UserSkillAddedDomainEvent(
                    aggregate_id=self.id(),
                    skill_id=skill_id,
                    mastery_level=mastery_level,
                )
            )
        )

    def record_progress(self, goal_id: str, progress_delta: float, evidence: dict):
        """Record progress toward a goal (updates Intent Status)."""
        self.state.on(
            self.register_event(
                UserProgressRecordedDomainEvent(
                    aggregate_id=self.id(),
                    goal_id=goal_id,
                    progress_delta=progress_delta,
                    evidence=evidence,
                )
            )
        )
```

### 4.2 Domain Events with Aspect Projections

```python
# domain/events/user.py

from neuroglia.data.abstractions import DomainEvent
from neuroglia.eventing.cloud_events import cloudevent


@cloudevent("user.goal.set.v1")
class UserGoalSetDomainEvent(DomainEvent[str]):
    """User declared a new goal (Intent Spec)."""
    goal_type: str
    target: str
    target_date: datetime | None
    constraints: dict


@cloudevent("user.skill.added.v1")
class UserSkillAddedDomainEvent(DomainEvent[str]):
    """User acquired or demonstrated a skill (Graph edge)."""
    skill_id: str
    mastery_level: str  # novice, intermediate, expert


@cloudevent("user.progress.recorded.v1")
class UserProgressRecordedDomainEvent(DomainEvent[str]):
    """Progress toward a goal (Intent Status update)."""
    goal_id: str
    progress_delta: float
    evidence: dict
```

### 4.3 Aspect Projection Handlers

Events from the User aggregate are projected to multiple stores:

```python
# application/events/user_graph_handler.py

class UserGraphProjectionHandler:
    """Projects user events to Neo4j graph."""

    @on(UserSkillAddedDomainEvent)
    async def handle_skill_added(self, event: UserSkillAddedDomainEvent):
        await self._graph.execute(
            """
            MATCH (u:User {id: $user_id})
            MERGE (s:Skill {id: $skill_id})
            MERGE (u)-[r:MASTERED {level: $level}]->(s)
            """,
            user_id=event.aggregate_id,
            skill_id=event.skill_id,
            level=event.mastery_level,
        )


# application/events/user_intent_handler.py

class UserIntentProjectionHandler:
    """Projects user events to Redis for intent tracking."""

    @on(UserGoalSetDomainEvent)
    async def handle_goal_set(self, event: UserGoalSetDomainEvent):
        spec = IntentSpec(
            goal_id=str(uuid4()),
            goal_type=event.goal_type,
            target_state=event.target,
            target_date=event.target_date,
            constraints=event.constraints,
            revision=1,
        )
        await self._redis.hset(
            f"user:{event.aggregate_id}:intents",
            spec.goal_id,
            spec.to_json(),
        )

    @on(UserProgressRecordedDomainEvent)
    async def handle_progress(self, event: UserProgressRecordedDomainEvent):
        # Update intent status
        status = await self._redis.hget(
            f"user:{event.aggregate_id}:intent_status",
            event.goal_id,
        )
        status.completion_percentage += event.progress_delta
        status.last_reconciled_at = datetime.now()
        await self._redis.hset(
            f"user:{event.aggregate_id}:intent_status",
            event.goal_id,
            status.to_json(),
        )
```

---

## 5. Domain Model: Stateful Agent

### 5.1 Agent Aggregate

Currently, Agents are **stateless** - defined by blueprints and instantiated per-session. The Polyglot model makes Agents **stateful** entities that:

- Learn user preferences over time
- Track their own performance (observational)
- Build relationships in the graph (semantic)
- Have operational targets (intentional)

```python
# domain/entities/agent.py (agent-host)

class AgentState(AggregateState[str]):
    """State for the Agent aggregate."""
    id: str
    blueprint_id: str
    name: str
    version: str

    # Stateful properties
    interactions_count: int
    successful_completions: int
    user_satisfaction_avg: float

    # Specializations (derived from graph)
    specialized_skills: list[str]

    created_at: datetime
    updated_at: datetime


class Agent(AggregateRoot[AgentState, str]):
    """Multi-dimensional Agent aggregate.

    Unlike stateless blueprints, Agent aggregates track:
    - Semantic: Which users/skills they're connected to
    - Intentional: Operational targets (response time, accuracy)
    - Observational: Performance metrics over time
    """

    def record_interaction(self, session_id: str, outcome: str, satisfaction: float):
        """Record an interaction outcome for learning."""
        self.state.on(
            self.register_event(
                AgentInteractionRecordedDomainEvent(
                    aggregate_id=self.id(),
                    session_id=session_id,
                    outcome=outcome,
                    satisfaction=satisfaction,
                )
            )
        )

    def assign_to_user(self, user_id: str, role: str):
        """Create assignment relationship in graph."""
        self.state.on(
            self.register_event(
                AgentAssignedToUserDomainEvent(
                    aggregate_id=self.id(),
                    user_id=user_id,
                    role=role,
                )
            )
        )
```

### 5.2 Agent Operational Intents

Agents can have their own "goals" - operational targets for quality:

```python
# Example: Agent Intent Spec
AgentIntentSpec(
    goal_id="response_quality",
    goal_type="operational_target",
    target_state="95% satisfaction",
    constraints={
        "min_response_time_ms": 500,
        "max_hallucination_rate": 0.01,
        "required_citation_rate": 0.9,
    },
)

# Reconciliation: If agent's satisfaction_avg drops below target,
# trigger retraining or escalation
```

---

## 6. Infrastructure Requirements

### 6.1 New Services

| Service | Purpose | Docker Image |
|---------|---------|--------------|
| Neo4j | Graph database for semantic aspect | `neo4j:5.15-community` |
| InfluxDB | Time-series for observational aspect | `influxdb:2.7` |

### 6.2 Docker Compose Additions

```yaml
# docker-compose.yml additions

  neo4j:
    image: neo4j:5.15-community
    ports:
      - "7474:7474"  # HTTP
      - "7687:7687"  # Bolt
    environment:
      NEO4J_AUTH: neo4j/password123
      NEO4J_PLUGINS: '["apoc"]'
    volumes:
      - neo4j_data:/data

  influxdb:
    image: influxdb:2.7
    ports:
      - "8086:8086"
    environment:
      DOCKER_INFLUXDB_INIT_MODE: setup
      DOCKER_INFLUXDB_INIT_USERNAME: admin
      DOCKER_INFLUXDB_INIT_PASSWORD: password123
      DOCKER_INFLUXDB_INIT_ORG: agent-host
      DOCKER_INFLUXDB_INIT_BUCKET: telemetry
    volumes:
      - influxdb_data:/var/lib/influxdb2

volumes:
  neo4j_data:
  influxdb_data:
```

### 6.3 Settings Additions

```python
# application/settings.py

    # Neo4j Configuration
    neo4j_url: str = Field(default="bolt://neo4j:7687", env="NEO4J_URL")
    neo4j_user: str = Field(default="neo4j", env="NEO4J_USER")
    neo4j_password: str = Field(default="password123", env="NEO4J_PASSWORD")

    # InfluxDB Configuration
    influxdb_url: str = Field(default="http://influxdb:8086", env="INFLUXDB_URL")
    influxdb_token: str = Field(default="", env="INFLUXDB_TOKEN")
    influxdb_org: str = Field(default="agent-host", env="INFLUXDB_ORG")
    influxdb_bucket: str = Field(default="telemetry", env="INFLUXDB_BUCKET")
```

---

## 7. Implementation Phases

### Phase 1: Infrastructure Foundation (Week 1)

- Add Neo4j and InfluxDB to docker-compose
- Create connection factories and base repositories
- Add settings for new databases

### Phase 2: Semantic Aspect (Week 2)

- Define graph schema (User, Agent, Skill, Concept nodes)
- Create GraphProjectionHandler base class
- Implement UserGraphHandler for skill/relationship events
- Create GraphQueryService for traversals

### Phase 3: Intentional Aspect (Week 3)

- Create IntentSpec/IntentStatus models
- Implement Redis projection for intents
- Create IntentReconciliator
- Add reconciliation background worker

### Phase 4: Observational Aspect (Week 4)

- Create TelemetryCollector service
- Implement CognitiveStateInferrer
- Create session-scoped telemetry aggregation
- Integrate with agent decision loop

### Phase 5: Integration (Week 5)

- Wire aspects into Session controller
- Create unified AspectLoader for agent context
- Update agent prompts to include aspect context
- End-to-end testing

---

## 8. Key Benefits

### For Users

- **Reduced Cognitive Load**: AI manages schedule (Intent) and finds resources (Semantic)
- **Psychological Safety**: Observational aspect ensures supportive, non-judgmental interventions
- **Personalization**: Responses grounded in user's actual knowledge and goals

### For Agents

- **Stateful Learning**: Agents improve through tracked interactions
- **Context Awareness**: Graph provides "zero-shot" understanding of user context
- **Goal Alignment**: Intentional aspect ensures agent serves user's declared objectives

### For the System

- **Clean Separation**: Each aspect has its own projection, query patterns, and lifecycle
- **Scalable**: Time-series and graph databases optimized for their access patterns
- **Event-Driven**: Standard DomainEvents project to all aspects

---

## 9. References

- [AI-Augmented Learning Session](https://gist.github.com/bvandewe/7011d1a183f85d9064d1a44316cc0cc8) - Source concept
- [Polyglot Entity Model Architecture](./polyglot-entity-model.md) - Framework theory
- [Event Sourcing Architecture](./event-sourcing.md) - Base patterns
- [Agent-Host LLD](../specs/agent-host-lld.md) - Current Session model
