# blueprint-manager Service Architecture

> **Status:** Design Document
> **Version:** 1.0.0
> **Last Updated:** December 25, 2025
> **Related:** [Certification Program Overview](../domain/certification-program/00-overview.md)

## Executive Summary

The `blueprint-manager` service is the **authoring tool** for Exam Blueprints, SkillTemplates, and FormSpecs. It enables EPMs and SMEs to collaboratively build exam specifications with AI assistance, validates against program rules from knowledge-manager, and publishes approved blueprints to Mosaic for Form assembly.

## Service Boundary

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                            blueprint-manager SERVICE BOUNDARY                                │
│                                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────────────────────┐ │
│  │                              AGGREGATES (Dual-Persistence)                              │ │
│  │                                                                                         │ │
│  │  ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐                   │ │
│  │  │   ExamBlueprint   │   │  SkillTemplate   │   │     FormSpec     │                   │ │
│  │  │                   │   │                   │   │                   │                   │ │
│  │  │ • Topics          │   │ • Stem templates  │   │ • Item slots      │                   │ │
│  │  │ • Skills          │   │ • Parameters      │   │ • Sections        │                   │ │
│  │  │ • KSA Statements  │   │ • Difficulty      │   │ • Scoring rules   │                   │ │
│  │  │ • Weights         │   │ • Distractors     │   │ • Time limits     │                   │ │
│  │  │ • MQC Definition  │   │ • Evaluation      │   │ • Constraints     │                   │ │
│  │  └──────────────────┘   └──────────────────┘   └──────────────────┘                   │ │
│  │                                                                                         │ │
│  │  ┌──────────────────────────────────────────────────────────────────────────────────┐ │ │
│  │  │                     PracticalExamTemplate (Future)                                │ │ │
│  │  │   • Scenario templates  • Variable dimensions  • Grading rules                    │ │ │
│  │  └──────────────────────────────────────────────────────────────────────────────────┘ │ │
│  │                                                                                         │ │
│  └────────────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────────────────────┐ │
│  │                              INTEGRATION POINTS                                         │ │
│  │                                                                                         │ │
│  │  INBOUND:                           OUTBOUND:                                           │ │
│  │  • REST API (CRUD on aggregates)    • CloudEvents (to knowledge-manager)               │ │
│  │  • agent-host (via tools-provider)  • REST API (to Mosaic on publish)                  │ │
│  │  • CloudEvents (external triggers)  • REST API (to knowledge-manager for validation)   │ │
│  │                                                                                         │ │
│  └────────────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                              │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

## Key Design Decisions

### 1. Dual-Persistence Strategy

All aggregates use **dual persistence** for strong auditing:

| Storage | Purpose | Data |
|---------|---------|------|
| **EventStoreDB** | Audit trail, compliance, time-travel | All domain events |
| **MongoDB** | Query optimization, read models | Projected aggregate state |

```
Command ──► Aggregate ──► DomainEvents ──┬──► EventStoreDB (append)
                                         │
                                         └──► MongoDB (upsert projection)
```

### 2. SkillTemplate as Independent Aggregate

SkillTemplates have their own lifecycle, separate from Blueprints:

- **Many-to-Many relationship**: One SkillTemplate can be linked to multiple Skills across Blueprints
- **Cross-track sharing**: Enterprise and Service Provider tracks can share routing templates
- **Independent versioning**: SkillTemplate updates don't require Blueprint republishing
- **Linkage via reference**: Skills contain `skill_template_ids: list[str]`

### 3. Mosaic as Downstream Recipient

```
┌─────────────────┐                    ┌─────────────────┐
│ blueprint-manager│                    │     Mosaic      │
│                 │                    │                 │
│  Draft ──────►  │                    │                 │
│  Review ─────►  │                    │                 │
│  Approved ───►  │ ════publish════►   │  Blueprint      │
│  Published ──►  │    (REST API)      │  (reference     │
│                 │                    │   for Forms)    │
└─────────────────┘                    └─────────────────┘
```

### 4. Validation via knowledge-manager

Runtime validation flow (not hard blocking in blueprint-manager):

```
agent-host ──► tools-provider ──► blueprint-manager
                    │
                    └──► knowledge-manager.validate_against_rules(blueprint)
                                │
                                ▼
                         Validation Report
                         (warnings, suggestions)
```

---

## Aggregate Designs

### ExamBlueprint Aggregate

```python
# domain/entities/exam_blueprint.py

class ExamBlueprintState(AggregateState[str]):
    """Persisted state for ExamBlueprint aggregate."""

    # Identity
    id: str
    name: str
    description: str
    version: str  # semver: 1.0.0, 1.1.0, 2.0.0

    # Classification
    track_id: str  # e.g., "enterprise", "security", "devnet"
    level: str  # "associate", "professional", "expert"
    type: str  # "core", "concentration", "specialist"

    # Status
    status: str  # "draft", "review", "approved", "published", "retired"

    # MQC Definition
    mqc_definition: dict  # {description, cut_score_method, cut_score}

    # Hierarchical Content
    topics: dict[str, dict]  # topic_id -> Topic
    # Each Topic contains:
    #   - id, name, description, weight, order
    #   - skills: dict[str, dict]  # skill_id -> Skill
    #     Each Skill contains:
    #       - id, name, description, skill_type
    #       - ksa_statements: list[dict]  # KSAStatement
    #       - skill_template_ids: list[str]  # References

    # Constraints
    constraints: dict  # {min_items, max_items, time_limit_minutes, balance_rules}

    # Audit
    created_by: str
    created_at: datetime
    updated_by: str
    updated_at: datetime
    submitted_by: str | None
    submitted_at: datetime | None
    approved_by: str | None
    approved_at: datetime | None
    published_by: str | None
    published_at: datetime | None

    # Mosaic Integration
    mosaic_blueprint_id: str | None  # Set after first publish to Mosaic

    # Concurrency
    state_version: int
```

### SkillTemplate Aggregate

```python
# domain/entities/skill_template.py

class SkillTemplateState(AggregateState[str]):
    """Persisted state for SkillTemplate aggregate."""

    # Identity
    id: str
    name: str
    description: str
    version: str

    # Status
    status: str  # "draft", "review", "active", "retired"

    # Item Generation Configuration
    item_type: str  # "multiple_choice", "multiple_select", "free_text",
                    # "code", "practical_task", "simulation"

    # Stem Templates (weighted selection)
    stem_templates: list[dict]
    # Each: {id, template, weight, cognitive_level}

    # Parameters for template instantiation
    parameters: dict[str, dict]
    # Each: {name, type, range, constraints, dependencies}

    # Difficulty calibration
    difficulty_levels: dict[str, dict]
    # Each: {name, value, constraints, weight}

    # Answer specification
    answer_spec: dict
    # {type, correct_answer_template, partial_credit_rules}

    # Distractor strategies (for MCQ)
    distractor_strategies: list[dict]
    # Each: {type, description, generation_params}

    option_count: int  # For MCQ/MS

    # Evaluation method
    evaluation_method: str  # "exact_match", "regex_match", "semantic_similarity",
                           # "code_execution", "device_state_check", "rubric_based"

    # Optional fields
    time_limit_seconds: int | None
    hints: list[dict] | None  # For candidate tutor agent

    # Usage tracking
    linked_skill_count: int  # Denormalized count of skills using this template

    # Audit
    created_by: str
    created_at: datetime
    reviewed_by: str | None
    reviewed_at: datetime | None

    state_version: int
```

### FormSpec Aggregate

```python
# domain/entities/form_spec.py

class FormSpecState(AggregateState[str]):
    """Persisted state for FormSpec aggregate."""

    # Identity
    id: str
    blueprint_id: str  # References ExamBlueprint
    name: str
    description: str
    version: str

    # Status
    status: str  # "draft", "active", "retired"

    # Form structure
    form_type: str  # "linear", "sectioned", "randomized", "adaptive"

    # Sections with item slots
    sections: list[dict]
    # Each section: {id, name, topic_id, item_slots, time_limit_minutes,
    #                allow_navigation, order}
    # Each item_slot: {id, skill_template_id, difficulty_constraint,
    #                  required, weight}

    # Global constraints
    global_constraints: dict
    # {total_items, total_time_minutes, passing_score,
    #  topic_distribution, difficulty_distribution}

    # Scoring rules
    scoring_rules: dict
    # {base_points_per_item, difficulty_multipliers,
    #  partial_credit_enabled, penalty_for_wrong, penalty_for_skip}

    # Delivery configuration
    delivery_config: dict
    # {show_progress, show_time_remaining, allow_review,
    #  allow_flag, shuffle_options, submit_confirmation}

    # Practical exam config (optional)
    practical_config: dict | None
    # {pod_type, initial_state_template, submission_points, cleanup_policy}

    # Usage tracking
    usage_count: int
    last_used_at: datetime | None

    # Audit
    created_by: str
    created_at: datetime

    state_version: int
```

---

## Domain Events

### ExamBlueprint Events

```python
# domain/events/exam_blueprint.py

@cloudevent("io.certification.blueprint.created.v1")
class ExamBlueprintCreatedDomainEvent(DomainEvent[str]):
    aggregate_id: str
    name: str
    track_id: str
    level: str
    type: str
    created_by: str
    created_at: datetime

@cloudevent("io.certification.blueprint.updated.v1")
class ExamBlueprintUpdatedDomainEvent(DomainEvent[str]):
    aggregate_id: str
    changed_fields: list[str]
    updated_by: str
    updated_at: datetime

@cloudevent("io.certification.blueprint.topic-added.v1")
class ExamBlueprintTopicAddedDomainEvent(DomainEvent[str]):
    aggregate_id: str
    topic_id: str
    name: str
    weight: float
    order: int
    added_by: str
    added_at: datetime

@cloudevent("io.certification.blueprint.skill-added.v1")
class ExamBlueprintSkillAddedDomainEvent(DomainEvent[str]):
    aggregate_id: str
    topic_id: str
    skill_id: str
    name: str
    skill_type: str
    added_by: str
    added_at: datetime

@cloudevent("io.certification.blueprint.ksa-added.v1")
class ExamBlueprintKSAAddedDomainEvent(DomainEvent[str]):
    aggregate_id: str
    skill_id: str
    ksa_id: str
    statement: str
    cognitive_level: str
    item_count_target: int
    added_by: str
    added_at: datetime

@cloudevent("io.certification.blueprint.submitted.v1")
class ExamBlueprintSubmittedDomainEvent(DomainEvent[str]):
    aggregate_id: str
    submitted_by: str
    submitted_at: datetime
    validation_report: dict | None  # Warnings from knowledge-manager

@cloudevent("io.certification.blueprint.approved.v1")
class ExamBlueprintApprovedDomainEvent(DomainEvent[str]):
    aggregate_id: str
    approved_by: str
    approved_at: datetime
    comments: str | None

@cloudevent("io.certification.blueprint.published.v1")
class ExamBlueprintPublishedDomainEvent(DomainEvent[str]):
    aggregate_id: str
    version: str
    published_by: str
    published_at: datetime
    mosaic_blueprint_id: str  # ID in Mosaic after sync

@cloudevent("io.certification.blueprint.retired.v1")
class ExamBlueprintRetiredDomainEvent(DomainEvent[str]):
    aggregate_id: str
    retired_by: str
    retired_at: datetime
    replacement_id: str | None
```

### SkillTemplate Events

```python
# domain/events/skill_template.py

@cloudevent("io.certification.skill-template.created.v1")
class SkillTemplateCreatedDomainEvent(DomainEvent[str]):
    aggregate_id: str
    name: str
    item_type: str
    created_by: str
    created_at: datetime

@cloudevent("io.certification.skill-template.updated.v1")
class SkillTemplateUpdatedDomainEvent(DomainEvent[str]):
    aggregate_id: str
    changed_fields: list[str]
    updated_by: str
    updated_at: datetime

@cloudevent("io.certification.skill-template.activated.v1")
class SkillTemplateActivatedDomainEvent(DomainEvent[str]):
    aggregate_id: str
    reviewed_by: str
    activated_at: datetime

@cloudevent("io.certification.skill-template.linked.v1")
class SkillTemplateLinkedDomainEvent(DomainEvent[str]):
    aggregate_id: str
    blueprint_id: str
    skill_id: str
    linked_by: str
    linked_at: datetime

@cloudevent("io.certification.skill-template.unlinked.v1")
class SkillTemplateUnlinkedDomainEvent(DomainEvent[str]):
    aggregate_id: str
    blueprint_id: str
    skill_id: str
    unlinked_by: str
    unlinked_at: datetime
```

---

## State Machine: ExamBlueprint

```
                                    ┌──────────────────────────────┐
                                    │                              │
                                    ▼                              │
     ┌─────────┐  update()    ┌─────────┐  reject()               │
     │  DRAFT  │◄────────────►│  DRAFT  │─────────────────────────┘
     └────┬────┘              └─────────┘
          │
          │ submit()
          │ (optional: request validation from knowledge-manager)
          ▼
     ┌─────────┐
     │ REVIEW  │◄──────────────────────────────────┐
     └────┬────┘                                   │
          │                                        │
          ├─── reject() ───────────────────────────┘
          │    (returns to DRAFT with feedback)
          │
          │ approve()
          ▼
     ┌──────────┐
     │ APPROVED │
     └────┬─────┘
          │
          │ publish()
          │ (sync to Mosaic, emit CloudEvent)
          ▼
     ┌──────────┐
     │PUBLISHED │
     └────┬─────┘
          │
          │ retire()
          ▼
     ┌─────────┐
     │ RETIRED │
     └─────────┘

Transitions:
- DRAFT → REVIEW: submit(submitted_by)
- REVIEW → DRAFT: reject(rejected_by, reason)
- REVIEW → APPROVED: approve(approved_by, comments)
- APPROVED → PUBLISHED: publish(published_by) → sync to Mosaic
- PUBLISHED → RETIRED: retire(retired_by, replacement_id)

Note: DRAFT allows multiple update cycles before submission
```

---

## Repository Pattern (Dual-Persistence)

```python
# domain/repositories/exam_blueprint_repository.py

class ExamBlueprintRepository(ABC):
    """Repository interface for ExamBlueprint aggregate.

    Implementations must support dual-persistence:
    - EventStoreDB for domain events (audit trail)
    - MongoDB for query-optimized read model
    """

    @abstractmethod
    async def get_async(self, blueprint_id: str) -> ExamBlueprint | None:
        """Load aggregate by replaying events from EventStoreDB."""
        ...

    @abstractmethod
    async def save_async(self, blueprint: ExamBlueprint) -> None:
        """
        Persist aggregate:
        1. Append new events to EventStoreDB
        2. Update MongoDB read model projection
        """
        ...

    @abstractmethod
    async def get_by_status_async(
        self,
        status: BlueprintStatus,
        track_id: str | None = None,
        level: str | None = None,
    ) -> list[ExamBlueprintSummary]:
        """Query read model for blueprints by status."""
        ...

    @abstractmethod
    async def get_by_mosaic_id_async(
        self,
        mosaic_blueprint_id: str
    ) -> ExamBlueprint | None:
        """Find blueprint by Mosaic integration ID."""
        ...
```

---

## Integration Flows

### Flow 1: Blueprint Creation & Authoring

```
EPM                 agent-host              blueprint-manager        knowledge-manager
 │                      │                         │                        │
 │  "Create a new       │                         │                        │
 │   CCNP Enterprise    │                         │                        │
 │   Core blueprint"    │                         │                        │
 │─────────────────────►│                         │                        │
 │                      │                         │                        │
 │                      │  MCP: create_blueprint  │                        │
 │                      │────────────────────────►│                        │
 │                      │                         │                        │
 │                      │                         │ CloudEvent:            │
 │                      │                         │ blueprint.created.v1   │
 │                      │                         │───────────────────────►│
 │                      │                         │                        │
 │                      │  Blueprint created      │                        │
 │                      │◄────────────────────────│                        │
 │                      │                         │                        │
 │  "Add Topic:         │                         │                        │
 │   Network Infra"     │                         │                        │
 │─────────────────────►│                         │                        │
 │                      │                         │                        │
 │                      │  MCP: add_topic         │                        │
 │                      │────────────────────────►│                        │
 │                      │                         │                        │
 │                      │                         │ Validate topic against │
 │                      │                         │ level invariants       │
 │                      │                         │───────────────────────►│
 │                      │                         │                        │
 │                      │                         │ Validation OK          │
 │                      │                         │◄───────────────────────│
 │                      │                         │                        │
 │                      │  Topic added            │                        │
 │                      │◄────────────────────────│                        │
```

### Flow 2: Blueprint Publication to Mosaic

```
EPM                 blueprint-manager              Mosaic              knowledge-manager
 │                         │                         │                        │
 │  publish()              │                         │                        │
 │────────────────────────►│                         │                        │
 │                         │                         │                        │
 │                         │  POST /api/blueprints   │                        │
 │                         │  (or PUT if updating)   │                        │
 │                         │────────────────────────►│                        │
 │                         │                         │                        │
 │                         │  { mosaic_id: "..." }   │                        │
 │                         │◄────────────────────────│                        │
 │                         │                         │                        │
 │                         │ Store mosaic_id         │                        │
 │                         │ in aggregate            │                        │
 │                         │                         │                        │
 │                         │                         │                        │
 │                         │ CloudEvent:             │                        │
 │                         │ blueprint.published.v1  │                        │
 │                         │─────────────────────────────────────────────────►│
 │                         │                         │                        │
 │                         │                         │       Update namespace │
 │                         │                         │       with blueprint   │
 │                         │                         │       terms/relations  │
 │                         │                         │                        │
 │  Published successfully │                         │                        │
 │◄────────────────────────│                         │                        │
```

### Flow 3: SkillTemplate Linking

```
SME                blueprint-manager              (SkillTemplate already exists)
 │                         │
 │  link_skill_template(   │
 │    blueprint_id,        │
 │    skill_id,            │
 │    template_id          │
 │  )                      │
 │────────────────────────►│
 │                         │
 │                         │  Validate template exists
 │                         │  Validate skill exists in blueprint
 │                         │
 │                         │  Add template_id to skill.skill_template_ids
 │                         │  Emit SkillTemplateLinkedDomainEvent
 │                         │
 │                         │  Update template.linked_skill_count
 │                         │
 │  Linked successfully    │
 │◄────────────────────────│
```

---

## MCP Tools (via tools-provider)

### Blueprint Tools

| Tool | Operation | Description |
|------|-----------|-------------|
| `blueprint.create` | Command | Create new blueprint shell |
| `blueprint.get` | Query | Get blueprint by ID |
| `blueprint.list` | Query | List blueprints with filters |
| `blueprint.update` | Command | Update blueprint metadata |
| `blueprint.add_topic` | Command | Add topic to blueprint |
| `blueprint.update_topic` | Command | Update topic (name, weight, order) |
| `blueprint.remove_topic` | Command | Remove topic from blueprint |
| `blueprint.add_skill` | Command | Add skill to topic |
| `blueprint.update_skill` | Command | Update skill details |
| `blueprint.add_ksa` | Command | Add KSA statement to skill |
| `blueprint.update_ksa` | Command | Update KSA statement |
| `blueprint.set_mqc` | Command | Set MQC definition |
| `blueprint.submit` | Command | Submit for review |
| `blueprint.approve` | Command | Approve blueprint |
| `blueprint.reject` | Command | Reject with feedback |
| `blueprint.publish` | Command | Publish to Mosaic |
| `blueprint.retire` | Command | Retire blueprint |
| `blueprint.validate` | Query | Validate against level rules |

### SkillTemplate Tools

| Tool | Operation | Description |
|------|-----------|-------------|
| `skill_template.create` | Command | Create new template |
| `skill_template.get` | Query | Get template by ID |
| `skill_template.list` | Query | List templates with filters |
| `skill_template.update` | Command | Update template configuration |
| `skill_template.add_stem` | Command | Add stem template variant |
| `skill_template.add_parameter` | Command | Add template parameter |
| `skill_template.set_difficulty` | Command | Set difficulty levels |
| `skill_template.add_distractor` | Command | Add distractor strategy |
| `skill_template.activate` | Command | Activate after review |
| `skill_template.link` | Command | Link to blueprint skill |
| `skill_template.unlink` | Command | Unlink from blueprint skill |
| `skill_template.preview` | Query | Generate preview item instance |

---

## knowledge-manager Namespaces

### Namespace: `certification-program`

**Purpose:** Certification level definitions, invariants, track structure

```yaml
namespace_id: 'certification-program'
name: 'Certification Program Structure'
description: 'Level definitions, invariants, and program rules'
access_level: 'public'

# Seed content (loaded on first startup)
terms:
  - term_id: 'level-associate'
    term: 'Associate Level'
    definition: |
      Entry-level certification validating foundational knowledge and skills.
      Bloom's distribution: Remember (20-30%), Understand (30-40%), Apply (25-35%)
    aliases: ['CCA', 'CCNA-level', 'Entry Level']

  - term_id: 'level-professional'
    term: 'Professional Level'
    definition: |
      Mid-level certification validating comprehensive knowledge and practical skills.
      Bloom's distribution: Apply (30-40%), Analyze (20-30%), Evaluate (5-15%)
    aliases: ['CCP', 'CCNP-level', 'Mid Level']

  - term_id: 'level-expert'
    term: 'Expert Level'
    definition: |
      Elite certification validating expert-level mastery.
      Bloom's distribution: Analyze (25-35%), Evaluate (25-35%), Create (10-20%)
    aliases: ['CCIE', 'CCIE-level', 'Expert Level']

  - term_id: 'type-core'
    term: 'Core Exam'
    definition: 'Required foundational exam within a certification track'

  - term_id: 'type-concentration'
    term: 'Concentration Exam'
    definition: 'Specialized depth exam, one required alongside core'

  - term_id: 'track-enterprise'
    term: 'Enterprise Track'
    definition: 'Certifications focused on enterprise networking infrastructure'
    aliases: ['Enterprise Infrastructure', 'CCNP Enterprise']

rules:
  - rule_id: 'bloom-001'
    name: 'Associate Bloom Distribution'
    condition: 'blueprint.level == "associate"'
    rule_text: 'Associate blueprints must have ≥50% items at Remember/Understand/Apply'
    rule_type: 'validation'
    priority: 1

  - rule_id: 'bloom-002'
    name: 'Expert Bloom Distribution'
    condition: 'blueprint.level == "expert"'
    rule_text: 'Expert blueprints must have ≥40% items at Analyze/Evaluate/Create'
    rule_type: 'validation'
    priority: 1

  - rule_id: 'verb-001'
    name: 'Associate Prohibited Verbs'
    condition: 'blueprint.level == "associate"'
    rule_text: 'Associate items should not use "design" or "architect" verbs'
    rule_type: 'validation'
    priority: 2

relationships:
  - source: 'level-associate'
    target: 'level-professional'
    type: 'PREREQUISITE_FOR'

  - source: 'level-professional'
    target: 'level-expert'
    type: 'PREREQUISITE_FOR'
```

### Namespace: `certification-blueprints`

**Purpose:** Published blueprints indexed for AI context expansion

```yaml
namespace_id: 'certification-blueprints'
name: 'Published Exam Blueprints'
description: 'Indexed blueprint content for AI agent context'
access_level: 'tenant'  # Restricted to certification team

# Populated dynamically from blueprint.published.v1 events
# Example term (auto-generated):
terms:
  - term_id: 'bp-encor-2025'
    term: 'ENCOR 350-401 Blueprint v2025.1'
    definition: |
      CCNP Enterprise Core exam blueprint.
      Topics: Network Infrastructure (25%), Virtualization (10%),
              Infrastructure (30%), Network Assurance (10%),
              Security (20%), Automation (5%)
    context_hint: 'Use for CCNP Enterprise Core exam queries'
```

---

## Folder Structure

```
src/blueprint-manager/
├── __init__.py
├── main.py
├── pyproject.toml
├── pytest.ini
├── Makefile
│
├── domain/
│   ├── __init__.py
│   ├── entities/
│   │   ├── __init__.py
│   │   ├── exam_blueprint.py
│   │   ├── skill_template.py
│   │   ├── form_spec.py
│   │   └── practical_exam_template.py  # Future
│   ├── enums/
│   │   ├── __init__.py
│   │   ├── blueprint_status.py
│   │   ├── skill_type.py
│   │   ├── cognitive_level.py
│   │   └── item_type.py
│   ├── events/
│   │   ├── __init__.py
│   │   ├── exam_blueprint.py
│   │   ├── skill_template.py
│   │   └── form_spec.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── topic.py
│   │   ├── skill.py
│   │   ├── ksa_statement.py
│   │   ├── mqc_definition.py
│   │   └── stem_template.py
│   └── repositories/
│       ├── __init__.py
│       ├── exam_blueprint_repository.py
│       ├── skill_template_repository.py
│       └── form_spec_repository.py
│
├── application/
│   ├── __init__.py
│   ├── settings.py
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── command_handler_base.py
│   │   ├── blueprint/
│   │   │   ├── create_blueprint_command.py
│   │   │   ├── update_blueprint_command.py
│   │   │   ├── add_topic_command.py
│   │   │   ├── add_skill_command.py
│   │   │   ├── add_ksa_command.py
│   │   │   ├── submit_blueprint_command.py
│   │   │   ├── approve_blueprint_command.py
│   │   │   ├── publish_blueprint_command.py
│   │   │   └── retire_blueprint_command.py
│   │   └── skill_template/
│   │       ├── create_skill_template_command.py
│   │       ├── update_skill_template_command.py
│   │       ├── link_skill_template_command.py
│   │       └── activate_skill_template_command.py
│   └── queries/
│       ├── __init__.py
│       ├── query_handler_base.py
│       ├── blueprint/
│       │   ├── get_blueprint_query.py
│       │   ├── list_blueprints_query.py
│       │   └── validate_blueprint_query.py
│       └── skill_template/
│           ├── get_skill_template_query.py
│           ├── list_skill_templates_query.py
│           └── preview_item_query.py
│
├── api/
│   ├── __init__.py
│   ├── dependencies.py
│   ├── description.md
│   ├── controllers/
│   │   ├── __init__.py
│   │   ├── blueprints_controller.py
│   │   ├── skill_templates_controller.py
│   │   └── form_specs_controller.py
│   └── services/
│       ├── __init__.py
│       ├── auth_service.py
│       ├── mosaic_client.py
│       └── knowledge_client.py
│
├── integration/
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── exam_blueprint_dto.py
│   │   ├── skill_template_dto.py
│   │   └── form_spec_dto.py
│   └── repositories/
│       ├── __init__.py
│       ├── dual_exam_blueprint_repository.py
│       ├── dual_skill_template_repository.py
│       └── dual_form_spec_repository.py
│
├── infrastructure/
│   ├── __init__.py
│   └── session_store.py
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── unit/
│   │   ├── domain/
│   │   │   ├── test_exam_blueprint.py
│   │   │   └── test_skill_template.py
│   │   └── application/
│   │       ├── test_create_blueprint_command.py
│   │       └── test_add_topic_command.py
│   └── integration/
│       └── test_blueprint_publication.py
│
└── static/
    └── (UI assets)
```

---

## Next Steps

1. **Create `src/blueprint-manager/` directory structure**
2. **Implement ExamBlueprint aggregate** following dual-persistence pattern
3. **Implement SkillTemplate aggregate** with linking logic
4. **Create command handlers** for CRUD operations
5. **Implement Mosaic client** for publish sync
6. **Create knowledge-manager event handlers** for blueprint indexing
7. **Define MCP tool schemas** in tools-provider

---

## Open Items for Future Design Sessions

| Item | Priority | Notes |
|------|----------|-------|
| PracticalExamTemplate aggregate | Medium | Complex templating, grading rules |
| FormSpec integration with LDS | Medium | How does LDS consume FormSpecs? |
| Version management strategy | High | How to handle blueprint revisions? |
| Mosaic API contract | High | Need exact API documentation |
| Cross-track template sharing | Medium | How to discover shared templates? |
