# ExamBlueprint Aggregate

> **Owning Service:** blueprint-manager

## Purpose

The ExamBlueprint aggregate represents the complete specification of what an Exam measures. It defines the hierarchical structure of Topics, Skills, and KSA Statements that constitute a Minimally Qualified Candidate (MQC).

## Aggregate Structure

```
ExamBlueprint
├── id: str (UUID)
├── name: str
├── description: str
├── version: str (semver)
├── status: BlueprintStatus (draft, review, published, retired)
│
├── mqc_definition: MQCDefinition
│   ├── description: str (narrative description of MQC)
│   ├── cut_score_method: str (Angoff, Bookmark, etc.)
│   └── cut_score: float (0.0-1.0)
│
├── topics: list[Topic]
│   ├── id: str
│   ├── name: str
│   ├── description: str
│   ├── weight: float (percentage of exam)
│   ├── skills: list[Skill]
│   │   ├── id: str
│   │   ├── name: str
│   │   ├── description: str
│   │   ├── skill_type: SkillType (knowledge, skill, attitude)
│   │   ├── ksa_statements: list[KSAStatement]
│   │   │   ├── id: str
│   │   │   ├── statement: str (measurable objective)
│   │   │   ├── cognitive_level: str (Bloom's taxonomy)
│   │   │   └── item_count_target: int
│   │   └── skill_template_ids: list[str] (references)
│   └── order: int
│
├── constraints: BlueprintConstraints
│   ├── min_items: int
│   ├── max_items: int
│   ├── time_limit_minutes: int
│   └── topic_balance_rules: list[BalanceRule]
│
├── audit: AuditInfo
│   ├── created_by: str
│   ├── created_at: datetime
│   ├── updated_by: str
│   ├── updated_at: datetime
│   └── published_at: datetime | None
│
└── state_version: int (optimistic concurrency)
```

## Value Objects

### MQCDefinition

```python
@dataclass(frozen=True)
class MQCDefinition:
    """Minimally Qualified Candidate specification."""
    description: str  # Narrative: "A candidate who can independently..."
    cut_score_method: str  # "angoff", "bookmark", "modified_angoff"
    cut_score: float  # 0.0-1.0
```

### Topic

```python
@dataclass
class Topic:
    """Major content area within a Blueprint."""
    id: str
    name: str
    description: str
    weight: float  # Percentage (0.0-1.0)
    skills: list[Skill]
    order: int
```

### Skill

```python
@dataclass
class Skill:
    """Specific competency to be measured."""
    id: str
    name: str
    description: str
    skill_type: SkillType  # KNOWLEDGE, SKILL, ATTITUDE
    ksa_statements: list[KSAStatement]
    skill_template_ids: list[str]  # Links to SkillTemplate
```

### KSAStatement

```python
@dataclass(frozen=True)
class KSAStatement:
    """Measurable learning objective."""
    id: str
    statement: str  # "Configure BGP peering between two routers"
    cognitive_level: str  # "remember", "understand", "apply", "analyze", "evaluate", "create"
    item_count_target: int  # Target number of items measuring this
```

## Domain Events

| Event | Trigger | Key Data |
|-------|---------|----------|
| `blueprint.created.v1` | New Blueprint created | id, name, owner |
| `blueprint.updated.v1` | Blueprint modified | id, changed_fields |
| `blueprint.topic.added.v1` | Topic added | blueprint_id, topic |
| `blueprint.skill.added.v1` | Skill added | blueprint_id, topic_id, skill |
| `blueprint.submitted.v1` | Submitted for review | id, submitted_by |
| `blueprint.published.v1` | Published for use | id, version, published_by |
| `blueprint.retired.v1` | Marked as retired | id, retired_by, replacement_id |

## Business Rules

### Structural Constraints

| Rule | Condition | Error Message |
|------|-----------|---------------|
| `min_topics` | len(topics) >= 2 | "Blueprint must have at least 2 Topics" |
| `topic_weights_sum` | sum(topic.weight) == 1.0 | "Topic weights must sum to 100%" |
| `skills_per_topic` | all(len(t.skills) >= 1) | "Each Topic must have at least 1 Skill" |
| `ksa_per_skill` | all(len(s.ksa) >= 1) | "Each Skill must have at least 1 KSA Statement" |

### Publishing Constraints

| Rule | Condition | Error Message |
|------|-----------|---------------|
| `has_cut_score` | mqc_definition.cut_score > 0 | "Cut score required for publishing" |
| `sufficient_templates` | all skills have templates | "All Skills must have linked SkillTemplates" |
| `template_coverage` | item_count >= min_items | "Insufficient item pool for exam generation" |

## State Machine

```
     ┌─────────┐
     │  DRAFT  │◄─────────────────────────────┐
     └────┬────┘                              │
          │ submit()                          │ reject()
          ▼                                   │
     ┌─────────┐                              │
     │ REVIEW  │──────────────────────────────┘
     └────┬────┘
          │ approve()
          ▼
     ┌─────────┐
     │PUBLISHED│
     └────┬────┘
          │ retire()
          ▼
     ┌─────────┐
     │ RETIRED │
     └─────────┘
```

## Repository Interface

```python
class ExamBlueprintRepository(ABC):
    """Repository interface for ExamBlueprint aggregate."""

    @abstractmethod
    async def get_async(self, blueprint_id: str) -> ExamBlueprint | None:
        """Load Blueprint by ID."""
        ...

    @abstractmethod
    async def save_async(self, blueprint: ExamBlueprint) -> None:
        """Persist Blueprint (creates or updates)."""
        ...

    @abstractmethod
    async def list_by_status_async(
        self, status: BlueprintStatus
    ) -> list[ExamBlueprintSummary]:
        """List Blueprints by status."""
        ...

    @abstractmethod
    async def get_with_templates_async(
        self, blueprint_id: str
    ) -> tuple[ExamBlueprint, list[SkillTemplate]]:
        """Load Blueprint with all linked SkillTemplates."""
        ...
```

## Integration with knowledge-manager

When a Blueprint is published, the following data is synchronized to knowledge-manager:

| Blueprint Data | Namespace Term |
|----------------|----------------|
| Blueprint name/description | Namespace term |
| Topic names | Terms with `:TOPIC_OF` relationship |
| Skill names | Terms with `:SKILL_OF` relationship |
| KSA statements | Terms with `:MEASURES` relationship |
| MQC definition | Business rule in namespace |

This enables agents to answer questions like:

- "What skills are covered in the Network Security topic?"
- "What is the MQC definition for this certification?"
- "Which topics have the highest weight?"

---

_Last updated: December 24, 2025_
