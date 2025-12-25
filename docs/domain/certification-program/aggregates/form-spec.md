# FormSpec Aggregate

> **Owning Service:** blueprint-manager
> **Consumed By:** agent-host (ConversationTemplate)

## Purpose

A FormSpec defines the structure of an Exam Form—which items to include, how to sequence them, time constraints, and scoring rules. It bridges the gap between abstract Blueprints and concrete Exam delivery.

## Design Rationale

FormSpecs enable:

1. **Blueprint Coverage**: Ensure all required Skills/Topics are represented
2. **Balanced Forms**: Control item distribution across topics
3. **Flexible Delivery**: Support different exam modes (linear, sectioned, adaptive)
4. **Scoring Consistency**: Define scoring rules per form

## Aggregate Structure

```
FormSpec
├── id: str (UUID)
├── blueprint_id: str (references ExamBlueprint)
├── name: str
├── description: str
├── version: str
├── status: FormSpecStatus (draft, active, retired)
│
├── form_type: FormType
│   ├── LINEAR          # All items in sequence
│   ├── SECTIONED       # Items grouped by topic/section
│   ├── RANDOMIZED      # Items shuffled per candidate
│   └── ADAPTIVE        # Items selected based on performance (future)
│
├── sections: list[FormSection]
│   ├── id: str
│   ├── name: str
│   ├── topic_id: str | None (optional topic constraint)
│   ├── item_slots: list[ItemSlot]
│   │   ├── id: str
│   │   ├── skill_template_id: str
│   │   ├── difficulty_constraint: DifficultyConstraint | None
│   │   │   ├── min: float
│   │   │   ├── max: float
│   │   │   └── target: float | None
│   │   ├── required: bool
│   │   └── weight: float (scoring weight)
│   ├── time_limit_minutes: int | None
│   ├── allow_navigation: bool (can go back?)
│   └── order: int
│
├── global_constraints: GlobalConstraints
│   ├── total_items: int
│   ├── total_time_minutes: int
│   ├── passing_score: float (0.0-1.0)
│   ├── topic_distribution: dict[str, float] (topic_id → percentage)
│   └── difficulty_distribution: dict[str, float] (easy/medium/hard → %)
│
├── scoring_rules: ScoringRules
│   ├── base_points_per_item: float
│   ├── difficulty_multipliers: dict[str, float]
│   ├── partial_credit_enabled: bool
│   ├── penalty_for_wrong: float | None (negative scoring)
│   └── penalty_for_skip: float | None
│
├── delivery_config: DeliveryConfig
│   ├── show_progress: bool
│   ├── show_time_remaining: bool
│   ├── allow_review: bool
│   ├── allow_flag: bool
│   ├── shuffle_options: bool (for MCQ)
│   └── submit_confirmation: bool
│
├── practical_config: PracticalConfig | None (for practical exams)
│   ├── pod_type: str
│   ├── initial_state_template: str
│   ├── submission_points: list[SubmissionPoint]
│   │   ├── id: str
│   │   ├── name: str
│   │   ├── after_section_id: str | None
│   │   └── triggers_grading: bool
│   └── cleanup_policy: str
│
├── metadata: FormSpecMetadata
│   ├── created_by: str
│   ├── created_at: datetime
│   ├── last_used_at: datetime | None
│   └── usage_count: int
│
└── state_version: int
```

## Example: MCQ Certification Exam

```yaml
id: 'form-spec-net-cert-2024-a'
blueprint_id: 'blueprint-network-cert'
name: 'Network Certification Form A'
form_type: SECTIONED

sections:
  - id: 'section-1'
    name: 'Network Fundamentals'
    topic_id: 'topic-net-fundamentals'
    item_slots:
      - id: 'slot-1-1'
        skill_template_id: 'skill-tpl-osi-model'
        difficulty_constraint:
          min: 0.2
          max: 0.5
        required: true
        weight: 1.0
      - id: 'slot-1-2'
        skill_template_id: 'skill-tpl-tcp-ip'
        difficulty_constraint:
          target: 0.5
        required: true
        weight: 1.0
      # ... more slots
    time_limit_minutes: 20
    allow_navigation: true
    order: 1

  - id: 'section-2'
    name: 'Routing & Switching'
    topic_id: 'topic-routing-switching'
    item_slots:
      # ... slots
    time_limit_minutes: 30
    allow_navigation: true
    order: 2

global_constraints:
  total_items: 60
  total_time_minutes: 90
  passing_score: 0.7
  topic_distribution:
    'topic-net-fundamentals': 0.25
    'topic-routing-switching': 0.35
    'topic-security': 0.25
    'topic-troubleshooting': 0.15
  difficulty_distribution:
    easy: 0.3
    medium: 0.5
    hard: 0.2

scoring_rules:
  base_points_per_item: 1.0
  difficulty_multipliers:
    easy: 0.8
    medium: 1.0
    hard: 1.5
  partial_credit_enabled: false
  penalty_for_wrong: null
  penalty_for_skip: null

delivery_config:
  show_progress: true
  show_time_remaining: true
  allow_review: true
  allow_flag: true
  shuffle_options: true
  submit_confirmation: true
```

## Example: Practical Exam (Lablets)

```yaml
id: 'form-spec-practical-2024-b'
blueprint_id: 'blueprint-network-practical'
name: 'Network Practical Exam Form B'
form_type: SECTIONED

sections:
  - id: 'lablet-1'
    name: 'Basic Router Configuration'
    item_slots:
      - id: 'task-1-1'
        skill_template_id: 'skill-tpl-router-basic-config'
        required: true
        weight: 2.0
      - id: 'task-1-2'
        skill_template_id: 'skill-tpl-interface-config'
        required: true
        weight: 1.5
    time_limit_minutes: 15
    allow_navigation: false  # Linear within lablet
    order: 1

  - id: 'lablet-2'
    name: 'BGP Peering'
    item_slots:
      - id: 'task-2-1'
        skill_template_id: 'skill-tpl-bgp-peering'
        difficulty_constraint:
          target: 0.5
        required: true
        weight: 3.0
    time_limit_minutes: 15
    allow_navigation: false
    order: 2

  # ... more lablets

global_constraints:
  total_items: 12
  total_time_minutes: 180  # 3 hours
  passing_score: 0.65

practical_config:
  pod_type: 'network-lab-v2'
  initial_state_template: 'pod-init-network-basic'
  submission_points:
    - id: 'submit-lablet-1'
      name: 'Submit Lablet 1'
      after_section_id: 'lablet-1'
      triggers_grading: true
    - id: 'submit-lablet-2'
      name: 'Submit Lablet 2'
      after_section_id: 'lablet-2'
      triggers_grading: true
  cleanup_policy: 'reset_between_lablets'

scoring_rules:
  base_points_per_item: 10.0
  partial_credit_enabled: true
```

## Mapping to ConversationTemplate

FormSpecs map to agent-host ConversationTemplates:

| FormSpec | ConversationTemplate |
|----------|---------------------|
| `id` | `id` |
| `sections[].item_slots[]` | `items[]` (with generation config) |
| `delivery_config` | `ui_config` |
| `scoring_rules` | `scoring_config` |
| `practical_config` | `device_config` |

```python
# agent-host/application/services/form_spec_adapter.py

class FormSpecAdapter:
    """Converts FormSpec to ConversationTemplate."""

    async def to_conversation_template(
        self,
        form_spec: FormSpec,
        skill_templates: dict[str, SkillTemplate],
    ) -> ConversationTemplate:
        items = []
        for section in form_spec.sections:
            for slot in section.item_slots:
                template = skill_templates[slot.skill_template_id]
                items.append(ItemConfig(
                    slot_id=slot.id,
                    skill_template=template,
                    difficulty_constraint=slot.difficulty_constraint,
                    weight=slot.weight,
                    section_id=section.id,
                ))

        return ConversationTemplate(
            id=form_spec.id,
            name=form_spec.name,
            items=items,
            ui_config=self._map_delivery_config(form_spec.delivery_config),
            scoring_config=self._map_scoring_rules(form_spec.scoring_rules),
            # ...
        )
```

## Domain Events

| Event | Trigger | Key Data |
|-------|---------|----------|
| `form-spec.created.v1` | New FormSpec created | id, blueprint_id, name |
| `form-spec.updated.v1` | FormSpec modified | id, changed_fields |
| `form-spec.activated.v1` | FormSpec ready for use | id, activated_by |
| `form-spec.retired.v1` | FormSpec retired | id, replacement_id |
| `form-spec.used.v1` | FormSpec used for exam | id, session_id |

## Validation Rules

| Rule | Condition | Error |
|------|-----------|-------|
| `blueprint_exists` | blueprint_id valid | "Invalid Blueprint reference" |
| `templates_exist` | All skill_template_ids valid | "Invalid SkillTemplate reference" |
| `topic_coverage` | All Blueprint topics represented | "Missing topic coverage" |
| `time_sufficient` | sum(section.time) <= global.time | "Section times exceed total" |
| `weights_valid` | All weights > 0 | "Invalid item weight" |
| `practical_config_required` | If any PRACTICAL_TASK items → practical_config | "Practical config required" |

---

_Last updated: December 24, 2025_
