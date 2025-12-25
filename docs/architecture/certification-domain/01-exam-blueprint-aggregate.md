# ExamBlueprint Aggregate Design

> **Bounded Context:** Exam Content (blueprint-manager service)
> **Persistence:** MongoDB via MotorRepository (state-based with CloudEvent publishing)
> **Status:** Design In Progress
> **Last Updated:** December 2025

## Overview

The `ExamBlueprint` aggregate is the primary domain entity in blueprint-manager, representing the authoritative definition of an exam. It captures the hierarchical structure (Domains → Topics → Skills), psychometric requirements (MQC Definition), and lifecycle management (DRAFT → PUBLISHED).

### Key Clarifications

- **ValidationResult**: Represents the outcome of validating a blueprint against rules defined in knowledge-manager's `certification-program` namespace. When an author submits a blueprint for review, blueprint-manager calls knowledge-manager's validation endpoint, which evaluates the blueprint against Bloom distribution rules, verb usage rules, etc. The results (pass/warning/error per rule) are stored with the blueprint for reviewer visibility.

- **knowledge-manager Updates**: When terms, rules, or relationships are updated in a namespace, the knowledge-manager aggregate emits domain events (e.g., `KnowledgeTermUpdatedDomainEvent`). These events trigger:
  1. **State update** in MongoDB via MotorRepository
  2. **CloudEvent publishing** for external consumers
  3. Graph infrastructure (Neo4j, if configured) would receive these events via a dedicated handler that adds/removes edges based on relationship changes

- **RBAC Enforcement**: blueprint-manager enforces granular scope-based permissions. All aggregate methods require authorization context, validated at the controller/command handler layer before invoking aggregate operations.

## Domain Model

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ExamBlueprint Aggregate                             │
│                                                                              │
│  Content Hierarchy (Mosaic-aligned)                                          │
│  └─ domains: dict[str, Domain]                                               │
│      ├─ id, name, description                                                │
│      ├─ weight_percentage: float (all domains must sum to 100%)              │
│      ├─ subdomains: dict[str, Subdomain] (optional)                          │
│      └─ topics: dict[str, Topic]                                             │
│          ├─ parent_topic_id: str | None (enables tree structure)             │
│          ├─ children: list[str] (child topic IDs)                            │
│          ├─ frequency: float (relevancy/item distribution weight)            │
│          └─ skills: dict[str, Skill]                                         │
│              └─ ksa_statements: dict[str, KSAStatement]                      │
│                                                                              │
│  Methods (Commands)                                                          │
│  ├─ create_blueprint()                                                       │
│  ├─ add_domain() / update_domain() / remove_domain()                        │
│  ├─ set_domain_weight()                                                      │
│  ├─ add_topic() / update_topic() / remove_topic() / move_topic()            │
│  ├─ add_skill() / update_skill() / remove_skill()                           │
│  ├─ link_skill_template() / unlink_skill_template()                         │
│  ├─ submit_for_review() / approve() / request_changes()                     │
│  ├─ publish() / retire()                                                     │
│  └─ validate_domain_weights() (invariant: must sum to 100% before publish)  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## RBAC Requirements

Blueprint-manager enforces role-based access control with granular scope permissions:

```python
class BlueprintPermission(str, Enum):
    """Granular permissions for blueprint operations."""

    # Read permissions
    VIEW = "blueprint:view"
    VIEW_DRAFT = "blueprint:view:draft"
    VIEW_ALL = "blueprint:view:all"

    # Write permissions
    CREATE = "blueprint:create"
    EDIT = "blueprint:edit"
    EDIT_DOMAIN = "blueprint:edit:domain"
    EDIT_TOPIC = "blueprint:edit:topic"
    EDIT_SKILL = "blueprint:edit:skill"

    # Workflow permissions
    SUBMIT_FOR_REVIEW = "blueprint:submit"
    APPROVE = "blueprint:approve"
    REQUEST_CHANGES = "blueprint:request_changes"
    PUBLISH = "blueprint:publish"
    RETIRE = "blueprint:retire"


class BlueprintScope(str, Enum):
    """Scope restrictions for permissions."""
    OWN = "own"           # Only blueprints created by this user
    TRACK = "track"       # Blueprints in user's assigned tracks
    ALL = "all"           # All blueprints (admin)
```

Authorization is checked at the command handler layer:

```python
class UpdateDomainCommandHandler(CommandHandler[UpdateDomainCommand, OperationResult]):
    async def handle(self, command: UpdateDomainCommand) -> OperationResult:
        if not await self.auth_service.has_permission(
            user=command.user_info,
            permission=BlueprintPermission.EDIT_DOMAIN,
            resource_id=command.blueprint_id,
            scope=BlueprintScope.TRACK,
        ):
            return OperationResult.forbidden("Insufficient permissions")
        # Proceed with domain update...
```

## Value Objects

### Domain (Value Object)

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass
class Domain:
    """A semantic group of topics with weighted scoring contribution.

    Domains are the top-level organizational unit in a blueprint.
    All domain weights must sum to 100% before publishing.
    """

    id: str
    """Unique ID (e.g., 'domain-arch')."""

    number: str
    """Display number (e.g., '1.0')."""

    name: str
    """Domain name (e.g., 'Architecture')."""

    description: str
    """Detailed description of what this domain covers."""

    weight_percentage: float
    """Percentage of exam score from this domain (must sum to 100%)."""

    subdomains: dict[str, "Subdomain"] = field(default_factory=dict)
    """Optional subdomains for further grouping, keyed by subdomain_id."""

    topics: dict[str, "Topic"] = field(default_factory=dict)
    """Topics within this domain, keyed by topic_id."""

    order: int = 0
    is_active: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "number": self.number,
            "name": self.name,
            "description": self.description,
            "weight_percentage": self.weight_percentage,
            "subdomains": {k: v.to_dict() for k, v in self.subdomains.items()},
            "topics": {k: v.to_dict() for k, v in self.topics.items()},
            "order": self.order,
            "is_active": self.is_active,
        }


@dataclass
class Subdomain:
    """Optional grouping within a domain."""

    id: str
    number: str
    name: str
    description: str = ""
    order: int = 0
    is_active: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "number": self.number,
            "name": self.name,
            "description": self.description,
            "order": self.order,
            "is_active": self.is_active,
        }
```

### Topic (Value Object) - with Tree Structure

```python
@dataclass
class Topic:
    """A topic within a domain, supporting hierarchical tree structure.

    Topics can have parent/children relationships for nested organization
    (matching Mosaic's topic tree model).
    """

    id: str
    number: str
    title: str
    description: str

    # Tree structure
    parent_topic_id: str | None = None
    """Parent topic ID for nested topics (None = root topic)."""

    children: list[str] = field(default_factory=list)
    """List of child topic IDs."""

    subdomain_id: str | None = None
    """Optional subdomain this topic belongs to."""

    # Weighting for item distribution
    frequency: float = 1.0
    """Relative frequency/relevancy weight for item distribution."""

    relevancy_score: float = 1.0
    """Relevancy score (0.0-1.0) for prioritizing topics."""

    target_item_count: int = 0
    """Target number of items for this topic."""

    skills: dict[str, "Skill"] = field(default_factory=dict)
    order: int = 0
    is_active: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "number": self.number,
            "title": self.title,
            "description": self.description,
            "parent_topic_id": self.parent_topic_id,
            "children": self.children,
            "subdomain_id": self.subdomain_id,
            "frequency": self.frequency,
            "relevancy_score": self.relevancy_score,
            "target_item_count": self.target_item_count,
            "skills": {k: v.to_dict() for k, v in self.skills.items()},
            "order": self.order,
            "is_active": self.is_active,
        }
```

### Skill and KSAStatement

```python
@dataclass
class Skill:
    """A testable skill within a topic."""

    id: str
    number: str
    statement: str
    bloom_level: int
    ksa_statements: dict[str, "KSAStatement"] = field(default_factory=dict)
    linked_template_id: str | None = None
    linked_template_version: str | None = None
    order: int = 0
    is_active: bool = True


@dataclass
class KSAStatement:
    """A specific Knowledge, Skill, or Ability statement."""

    id: str
    identifier: str
    type: str  # "knowledge", "skill", or "ability"
    statement: str
    bloom_level: int
    item_count_target: int = 0
    notes: str = ""
    order: int = 0
    is_active: bool = True
```

### ValidationResult (Clarified)

```python
@dataclass
class ValidationResult:
    """Result from knowledge-manager validation.

    When a blueprint is validated against the certification-program namespace,
    knowledge-manager evaluates each applicable rule and returns results.

    Example rules evaluated:
    - "bloom-dist-professional": Bloom distribution meets Professional level
    - "verb-prohibited-associate": No prohibited verbs in Associate-level KSAs
    """

    validated_at: datetime
    validated_by: str
    rule_id: str
    rule_name: str
    severity: str  # "error", "warning", "info"
    passed: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)
```

## Domain Events

All events follow the `@cloudevent` decorator pattern. Events are:

1. Applied to state via `self.state.on(...)`
2. Registered via `self.register_event(...)` for CloudEvent publishing
3. **NOT** persisted to EventStoreDB (we use state-based persistence)

### Blueprint Lifecycle Events

```python
from dataclasses import dataclass
from datetime import datetime
from neuroglia.data.abstractions import DomainEvent
from neuroglia.eventing.cloud_events.decorators import cloudevent


@cloudevent("blueprint.created.v1")
@dataclass
class BlueprintCreatedDomainEvent(DomainEvent):
    aggregate_id: str
    exam_code: str
    exam_name: str
    version: str
    level: str
    type: str
    track: str
    certification_path: str
    created_by: str
    created_at: datetime


@cloudevent("blueprint.published.v1")
@dataclass
class BlueprintPublishedDomainEvent(DomainEvent):
    aggregate_id: str
    exam_code: str
    exam_name: str
    version: str
    mosaic_blueprint_id: str
    published_by: str
    published_at: datetime
```

### Domain Events

```python
@cloudevent("blueprint.domain.added.v1")
@dataclass
class DomainAddedDomainEvent(DomainEvent):
    aggregate_id: str
    domain_id: str
    number: str
    name: str
    description: str
    weight_percentage: float
    order: int
    added_by: str
    added_at: datetime


@cloudevent("blueprint.domain.weight.updated.v1")
@dataclass
class DomainWeightUpdatedDomainEvent(DomainEvent):
    aggregate_id: str
    domain_id: str
    weight_percentage: float
    updated_by: str
    updated_at: datetime
```

### Topic Events (with tree support)

```python
@cloudevent("blueprint.topic.added.v1")
@dataclass
class TopicAddedDomainEvent(DomainEvent):
    aggregate_id: str
    domain_id: str
    topic_id: str
    number: str
    title: str
    description: str
    parent_topic_id: str | None  # For nested topics
    subdomain_id: str | None
    frequency: float
    relevancy_score: float
    order: int
    added_by: str
    added_at: datetime


@cloudevent("blueprint.topic.moved.v1")
@dataclass
class TopicMovedDomainEvent(DomainEvent):
    """Emitted when a topic is moved in the tree (reparented)."""
    aggregate_id: str
    domain_id: str
    topic_id: str
    old_parent_topic_id: str | None
    new_parent_topic_id: str | None
    moved_by: str
    moved_at: datetime
```

## Aggregate State

```python
from datetime import UTC, datetime
from multipledispatch import dispatch
from neuroglia.data.abstractions import AggregateState


class ExamBlueprintState(AggregateState[str]):
    """Encapsulates the persisted state for the ExamBlueprint aggregate.

    Persistence Strategy:
    - MongoDB via MotorRepository (state-based)
    - Domain events are published as CloudEvents for external consumers
    - Domain events are NOT persisted to EventStoreDB
    """

    # Identity
    id: str
    exam_code: str
    exam_name: str
    version: str

    # Classification
    level: str
    type: str
    track: str
    certification_path: str

    # Content hierarchy (Domains → Topics → Skills)
    domains: dict[str, dict]

    # Lifecycle
    status: str
    status_history: list[dict]

    # Validation (from knowledge-manager)
    validation_results: list[dict]
    last_validated_at: datetime | None

    # Statistics (denormalized)
    domain_count: int
    topic_count: int
    skill_count: int

    # Audit
    created_by: str | None
    created_at: datetime
    updated_at: datetime

    def __init__(self) -> None:
        super().__init__()
        self.id = ""
        self.exam_code = ""
        self.exam_name = ""
        self.version = "1.0"
        self.level = ""
        self.type = ""
        self.track = ""
        self.certification_path = ""
        self.domains = {}
        self.status = BlueprintStatus.DRAFT.value
        self.status_history = []
        self.validation_results = []
        self.last_validated_at = None
        self.domain_count = 0
        self.topic_count = 0
        self.skill_count = 0
        self.created_by = None
        now = datetime.now(UTC)
        self.created_at = now
        self.updated_at = now

    # Event Handlers - Apply events to state (using @dispatch)

    @dispatch(BlueprintCreatedDomainEvent)
    def on(self, event: BlueprintCreatedDomainEvent) -> None:
        self.id = event.aggregate_id
        self.exam_code = event.exam_code
        self.exam_name = event.exam_name
        self.version = event.version
        self.level = event.level
        self.type = event.type
        self.track = event.track
        self.certification_path = event.certification_path
        self.created_by = event.created_by
        self.created_at = event.created_at
        self.updated_at = event.created_at

    @dispatch(DomainAddedDomainEvent)
    def on(self, event: DomainAddedDomainEvent) -> None:
        self.domains[event.domain_id] = {
            "id": event.domain_id,
            "number": event.number,
            "name": event.name,
            "description": event.description,
            "weight_percentage": event.weight_percentage,
            "subdomains": {},
            "topics": {},
            "order": event.order,
            "is_active": True,
        }
        self.domain_count = len([d for d in self.domains.values() if d.get("is_active")])
        self.updated_at = event.added_at

    @dispatch(DomainWeightUpdatedDomainEvent)
    def on(self, event: DomainWeightUpdatedDomainEvent) -> None:
        if event.domain_id in self.domains:
            self.domains[event.domain_id]["weight_percentage"] = event.weight_percentage
        self.updated_at = event.updated_at

    @dispatch(TopicAddedDomainEvent)
    def on(self, event: TopicAddedDomainEvent) -> None:
        if event.domain_id in self.domains:
            self.domains[event.domain_id]["topics"][event.topic_id] = {
                "id": event.topic_id,
                "number": event.number,
                "title": event.title,
                "description": event.description,
                "parent_topic_id": event.parent_topic_id,
                "children": [],
                "subdomain_id": event.subdomain_id,
                "frequency": event.frequency,
                "relevancy_score": event.relevancy_score,
                "skills": {},
                "order": event.order,
                "is_active": True,
            }
            # Update parent's children list if nested
            if event.parent_topic_id:
                parent = self.domains[event.domain_id]["topics"].get(event.parent_topic_id)
                if parent:
                    parent["children"].append(event.topic_id)
        self._recount_topics()
        self.updated_at = event.added_at

    def _recount_topics(self) -> None:
        count = 0
        for domain in self.domains.values():
            if domain.get("is_active", True):
                for topic in domain.get("topics", {}).values():
                    if topic.get("is_active", True):
                        count += 1
        self.topic_count = count
```

## Aggregate Root Implementation

Following the **agent-host pattern**: events are applied to state via `self.state.on()` AND registered via `self.register_event()`.

```python
from datetime import UTC, datetime
from typing import cast
from uuid import uuid4
from neuroglia.data.abstractions import AggregateRoot


class ExamBlueprint(AggregateRoot[ExamBlueprintState, str]):
    """Aggregate root for exam blueprints.

    Persistence: MongoDB via MotorRepository (state-based).
    Domain events are published as CloudEvents but NOT persisted.
    """

    def __init__(
        self,
        exam_code: str,
        exam_name: str,
        level: CertificationLevel,
        type: CertificationType,
        track: str,
        certification_path: str,
        created_by: str,
        version: str = "1.0",
        blueprint_id: str | None = None,
    ) -> None:
        super().__init__()
        aggregate_id = blueprint_id or str(uuid4())
        now = datetime.now(UTC)

        # CORRECT PATTERN: Apply event to state, then register for publishing
        self.state.on(
            self.register_event(
                BlueprintCreatedDomainEvent(
                    aggregate_id=aggregate_id,
                    exam_code=exam_code,
                    exam_name=exam_name,
                    version=version,
                    level=level.value,
                    type=type.value,
                    track=track,
                    certification_path=certification_path,
                    created_by=created_by,
                    created_at=now,
                )
            )
        )

    def id(self) -> str:
        aggregate_id = super().id()
        if aggregate_id is None:
            raise ValueError("Blueprint aggregate identifier has not been initialized")
        return cast(str, aggregate_id)

    # Domain CRUD

    def add_domain(
        self,
        domain_id: str,
        number: str,
        name: str,
        description: str,
        weight_percentage: float,
        order: int,
        added_by: str,
    ) -> None:
        """Add a domain to the blueprint."""
        self._assert_editable()

        if domain_id in self.state.domains:
            raise ValueError(f"Domain {domain_id} already exists")

        self.state.on(
            self.register_event(
                DomainAddedDomainEvent(
                    aggregate_id=self.id(),
                    domain_id=domain_id,
                    number=number,
                    name=name,
                    description=description,
                    weight_percentage=weight_percentage,
                    order=order,
                    added_by=added_by,
                    added_at=datetime.now(UTC),
                )
            )
        )

    def set_domain_weight(
        self,
        domain_id: str,
        weight_percentage: float,
        updated_by: str,
    ) -> None:
        """Update a domain's weight percentage."""
        self._assert_editable()
        self._assert_domain_exists(domain_id)

        self.state.on(
            self.register_event(
                DomainWeightUpdatedDomainEvent(
                    aggregate_id=self.id(),
                    domain_id=domain_id,
                    weight_percentage=weight_percentage,
                    updated_by=updated_by,
                    updated_at=datetime.now(UTC),
                )
            )
        )

    # Topic CRUD (with tree structure support)

    def add_topic(
        self,
        domain_id: str,
        topic_id: str,
        number: str,
        title: str,
        description: str,
        added_by: str,
        parent_topic_id: str | None = None,
        subdomain_id: str | None = None,
        frequency: float = 1.0,
        relevancy_score: float = 1.0,
        order: int = 0,
    ) -> None:
        """Add a topic to a domain, optionally as a child of another topic."""
        self._assert_editable()
        self._assert_domain_exists(domain_id)

        if parent_topic_id:
            self._assert_topic_exists(domain_id, parent_topic_id)

        self.state.on(
            self.register_event(
                TopicAddedDomainEvent(
                    aggregate_id=self.id(),
                    domain_id=domain_id,
                    topic_id=topic_id,
                    number=number,
                    title=title,
                    description=description,
                    parent_topic_id=parent_topic_id,
                    subdomain_id=subdomain_id,
                    frequency=frequency,
                    relevancy_score=relevancy_score,
                    order=order,
                    added_by=added_by,
                    added_at=datetime.now(UTC),
                )
            )
        )

    def move_topic(
        self,
        domain_id: str,
        topic_id: str,
        new_parent_topic_id: str | None,
        moved_by: str,
    ) -> None:
        """Move a topic to a different parent (or to root level)."""
        self._assert_editable()
        self._assert_topic_exists(domain_id, topic_id)

        if new_parent_topic_id:
            self._assert_topic_exists(domain_id, new_parent_topic_id)
            if self._is_descendant_of(domain_id, new_parent_topic_id, topic_id):
                raise ValueError("Cannot move topic to its own descendant")

        topic = self.state.domains[domain_id]["topics"][topic_id]
        old_parent = topic.get("parent_topic_id")

        self.state.on(
            self.register_event(
                TopicMovedDomainEvent(
                    aggregate_id=self.id(),
                    domain_id=domain_id,
                    topic_id=topic_id,
                    old_parent_topic_id=old_parent,
                    new_parent_topic_id=new_parent_topic_id,
                    moved_by=moved_by,
                    moved_at=datetime.now(UTC),
                )
            )
        )
```

### Invariant: Domain Weights Must Sum to 100%

```python
    def validate_domain_weights(self) -> bool:
        """Validate that all domain weights sum to 100%."""
        total = sum(
            d.get("weight_percentage", 0.0)
            for d in self.state.domains.values()
            if d.get("is_active", True)
        )
        return abs(total - 100.0) < 0.01  # Allow small floating point variance

    def publish(self, mosaic_blueprint_id: str, published_by: str) -> None:
        """Publish blueprint to Mosaic."""
        if self.state.status != BlueprintStatus.APPROVED.value:
            raise ValueError(f"Cannot publish from status {self.state.status}")

        # Enforce domain weight invariant
        if not self.validate_domain_weights():
            total = sum(
                d.get("weight_percentage", 0.0)
                for d in self.state.domains.values()
                if d.get("is_active", True)
            )
            raise ValueError(f"Domain weights must sum to 100% (current: {total}%)")

        self.state.on(
            self.register_event(
                BlueprintPublishedDomainEvent(
                    aggregate_id=self.id(),
                    exam_code=self.state.exam_code,
                    exam_name=self.state.exam_name,
                    version=self.state.version,
                    mosaic_blueprint_id=mosaic_blueprint_id,
                    published_by=published_by,
                    published_at=datetime.now(UTC),
                )
            )
        )

    # Validation Helpers

    def _assert_editable(self) -> None:
        if self.state.status not in [BlueprintStatus.DRAFT.value, BlueprintStatus.CHANGES_REQUESTED.value]:
            raise ValueError(f"Blueprint cannot be edited in status {self.state.status}")

    def _assert_domain_exists(self, domain_id: str) -> None:
        if domain_id not in self.state.domains:
            raise ValueError(f"Domain {domain_id} not found")

    def _assert_topic_exists(self, domain_id: str, topic_id: str) -> None:
        self._assert_domain_exists(domain_id)
        if topic_id not in self.state.domains[domain_id].get("topics", {}):
            raise ValueError(f"Topic {topic_id} not found")

    def _is_descendant_of(self, domain_id: str, parent_id: str, child_id: str) -> bool:
        """Check if child_id is a descendant of parent_id."""
        topics = self.state.domains[domain_id].get("topics", {})
        topic = topics.get(parent_id)
        if not topic:
            return False
        for c in topic.get("children", []):
            if c == child_id or self._is_descendant_of(domain_id, c, child_id):
                return True
        return False
```

## Repository Configuration

Following the **agent-host pattern** with MotorRepository (state-based):

```python
# In main.py - Data Access Layer configuration
from neuroglia.data.infrastructure.mongo import MotorRepository

MotorRepository.configure(
    builder,
    entity_type=ExamBlueprint,
    key_type=str,
    database_name=app_settings.database_name,
    collection_name="blueprints",
    domain_repository_type=ExamBlueprintRepository,
    implementation_type=MotorExamBlueprintRepository,
)

# Domain events are published via CloudEventPublisher (configured separately)
# They are NOT persisted to EventStoreDB in this architecture
CloudEventPublisher.configure(builder)
```

## State Machine

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     EXAM BLUEPRINT STATE MACHINE                             │
│                                                                              │
│                          ┌──────────────┐                                    │
│                          │    DRAFT     │◄──────────────────────┐            │
│                          └──────┬───────┘                       │            │
│                                 │                               │            │
│                      submit_for_review()                        │            │
│                      (validation results attached)              │            │
│                                 ▼                               │            │
│                          ┌──────────────┐                       │            │
│               ┌─────────►│    REVIEW    │────────────┐          │            │
│               │          └──────┬───────┘            │          │            │
│               │                 │                    │          │            │
│    request_changes()     approve()            request_changes() │            │
│               │                 │                    │          │            │
│               │                 ▼                    │          │            │
│    ┌──────────────────┐  ┌──────────────┐            │          │            │
│    │CHANGES_REQUESTED │  │   APPROVED   │◄───────────┘          │            │
│    └────────┬─────────┘  └──────┬───────┘                       │            │
│             │                   │                               │            │
│             │                   │ publish()                     │            │
│             │                   │ (validates domain weights=100%)            │
│             │                   ▼                               │            │
│             │            ┌──────────────┐                       │            │
│             │            │  PUBLISHED   │                       │            │
│             │            └──────┬───────┘                       │            │
│             │                   │ retire()                      │            │
│             │                   ▼                               │            │
│             │            ┌──────────────┐                       │            │
│             └───────────►│   RETIRED    │───────────────────────┘            │
│                          └──────────────┘                                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

## knowledge-manager Integration

### How Updates Propagate

When seed data in knowledge-manager is updated (e.g., changing a rule):

1. **Aggregate Command** (`UpdateRuleCommand`) updates the namespace aggregate
2. **Event Applied**: `self.state.on(self.register_event(KnowledgeRuleUpdatedDomainEvent(...)))`
3. **State Persisted**: MotorRepository saves updated state to MongoDB
4. **CloudEvent Published**: Event → message broker
5. **Downstream Consumers**:
   - **Graph Handler** (if configured): Updates Neo4j edges if relationship changed
   - **blueprint-manager**: May invalidate cached rules, trigger re-validation

```python
# Example: Updating a rule in knowledge-manager
class UpdateRuleCommandHandler(CommandHandler[UpdateRuleCommand, OperationResult]):
    async def handle(self, command: UpdateRuleCommand) -> OperationResult:
        namespace = await self.repository.get_async(command.namespace_id)

        # Update rule in aggregate (emits event)
        namespace.update_rule(
            rule_id=command.rule_id,
            name=command.name,
            rule_text=command.rule_text,
            updated_by=command.user_id,
        )

        # Save to MongoDB; CloudEventPublisher publishes event
        await self.repository.update_async(namespace)

        return OperationResult.success(...)
```

---

_Last updated: December 2025_
