# SkillTemplate Aggregate

> **Owning Service:** blueprint-manager
> **Consumed By:** agent-host (item generation)

## Purpose

A SkillTemplate defines how to generate unique, valid Items for a specific Skill. It includes stem templates, parameter specifications, difficulty calibration, and distractor generation strategies.

## Design Rationale

SkillTemplates enable:

1. **Unique Items Per Candidate**: Randomized parameters prevent memorization
2. **Consistent Quality**: Structured generation ensures item validity
3. **Scalable Authoring**: One template → many unique items
4. **Difficulty Control**: Parameterized difficulty for adaptive testing

## Aggregate Structure

```
SkillTemplate
├── id: str (UUID)
├── skill_id: str (references Skill in Blueprint)
├── name: str
├── description: str
├── version: str
├── status: TemplateStatus (draft, review, active, retired)
│
├── item_type: ItemType
│   ├── MULTIPLE_CHOICE
│   ├── MULTIPLE_SELECT
│   ├── FREE_TEXT
│   ├── CODE
│   ├── PRACTICAL_TASK
│   └── SIMULATION
│
├── stem_templates: list[StemTemplate]
│   ├── id: str
│   ├── template: str (with {placeholders})
│   ├── weight: float (selection probability)
│   └── cognitive_level: str
│
├── parameters: dict[str, ParameterSpec]
│   ├── name: str
│   ├── type: str (int, float, string, enum, ip_address, hostname, etc.)
│   ├── range: tuple | list (min/max or enumerated values)
│   ├── constraints: list[Constraint]
│   └── dependencies: list[str] (other parameters this depends on)
│
├── difficulty_levels: dict[str, DifficultyLevel]
│   ├── name: str (easy, medium, hard)
│   ├── value: float (0.0-1.0)
│   ├── constraints: list[str] (parameter constraints for this level)
│   └── weight: float (scoring weight multiplier)
│
├── answer_spec: AnswerSpec
│   ├── type: str (exact, range, regex, rubric)
│   ├── correct_answer_template: str (with {placeholders})
│   └── partial_credit_rules: list[PartialCreditRule] | None
│
├── distractor_strategies: list[DistractorStrategy] (for MCQ/MS)
│   ├── type: str
│   ├── description: str
│   └── generation_params: dict
│
├── option_count: int (for MCQ/MS)
│
├── evaluation_method: EvaluationMethod
│   ├── EXACT_MATCH
│   ├── REGEX_MATCH
│   ├── SEMANTIC_SIMILARITY
│   ├── CODE_EXECUTION
│   ├── DEVICE_STATE_CHECK
│   └── RUBRIC_BASED
│
├── time_limit_seconds: int | None
│
├── hints: list[Hint] | None (for candidate-tutor agent)
│   ├── level: int (1=subtle, 2=moderate, 3=direct)
│   └── text: str
│
├── metadata: TemplateMetadata
│   ├── created_by: str
│   ├── created_at: datetime
│   ├── reviewed_by: str | None
│   ├── reviewed_at: datetime | None
│   └── usage_count: int
│
└── state_version: int
```

## Example: Single-Digit Multiplication

```yaml
skill_id: 'MATH.ARITH.MUL.SINGLE'
name: 'Single-Digit Multiplication'
item_type: 'multiple_choice'

stem_templates:
  - id: 'stem-1'
    template: 'What is {a} × {b}?'
    weight: 1.0
  - id: 'stem-2'
    template: 'Calculate: {a} × {b} = ?'
    weight: 0.8

parameters:
  a:
    type: int
    range: [1, 9]
  b:
    type: int
    range: [1, 9]

difficulty_levels:
  easy:
    value: 0.3
    constraints:
      - 'a <= 5 and b <= 5'
      - 'a == 1 or b == 1 or a == 5 or b == 5'
  medium:
    value: 0.5
    constraints:
      - 'a >= 2 and b >= 2'
      - 'a in [6,7,8] or b in [6,7,8]'
  hard:
    value: 0.7
    constraints:
      - 'a >= 6 and b >= 6'

answer_spec:
  type: exact
  correct_answer_template: '{a * b}'

distractor_strategies:
  - type: 'off_by_one_factor'
    description: 'Result of adjacent multiplication fact'
  - type: 'digit_swap'
    description: 'Swap digits of answer (56 -> 65)'
  - type: 'addition_confusion'
    description: 'a + b instead of a × b'

option_count: 4
evaluation_method: EXACT_MATCH
time_limit_seconds: 45

hints:
  - level: 1
    text: 'Think about your multiplication tables.'
  - level: 2
    text: 'What is {a} groups of {b}?'
```

## Example: Practical Networking Task

```yaml
skill_id: 'NET.BGP.PEER.BASIC'
name: 'Configure BGP Peering'
item_type: 'practical_task'

stem_templates:
  - id: 'stem-1'
    template: |
      Configure BGP peering between Router {router_a} and Router {router_b}.

      Requirements:
      - Router {router_a} AS: {as_a}
      - Router {router_b} AS: {as_b}
      - Peering IP on {router_a}: {ip_a}
      - Peering IP on {router_b}: {ip_b}

      Verify the peering is established before submitting.

parameters:
  router_a:
    type: hostname
    range: ['R1', 'R2', 'R3', 'R4']
  router_b:
    type: hostname
    range: ['R1', 'R2', 'R3', 'R4']
    constraints:
      - 'router_b != router_a'
  as_a:
    type: int
    range: [64512, 65534]  # Private ASN range
  as_b:
    type: int
    range: [64512, 65534]
    constraints:
      - 'as_b != as_a'
  ip_a:
    type: ip_address
    range: '10.{subnet}.1.1/30'
    dependencies: ['subnet']
  ip_b:
    type: ip_address
    range: '10.{subnet}.1.2/30'
    dependencies: ['subnet']
  subnet:
    type: int
    range: [1, 254]

difficulty_levels:
  easy:
    value: 0.4
    constraints:
      - 'eBGP only (as_a != as_b always true)'
  hard:
    value: 0.7
    constraints:
      - 'iBGP (as_a == as_b)'
      - 'Route reflector required'

answer_spec:
  type: device_state
  correct_answer_template: |
    router_{router_a}_bgp_neighbor_{ip_b}_state: Established
    router_{router_b}_bgp_neighbor_{ip_a}_state: Established

evaluation_method: DEVICE_STATE_CHECK
time_limit_seconds: 900  # 15 minutes

hints:
  - level: 1
    text: 'BGP configuration is done under the router bgp process.'
  - level: 2
    text: 'Make sure the neighbor IP and remote-as are configured correctly.'
```

## Item Generation Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ITEM GENERATION PIPELINE                             │
│                                                                              │
│  ┌──────────────┐                                                            │
│  │SkillTemplate │                                                            │
│  └──────┬───────┘                                                            │
│         │                                                                    │
│         ▼                                                                    │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ 1. PARAMETER INSTANTIATION                                            │   │
│  │                                                                       │   │
│  │    Select difficulty level → Apply constraints → Randomize params     │   │
│  │    Example: difficulty=hard → a∈[6,9], b∈[6,9] → a=7, b=8            │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│         │                                                                    │
│         ▼                                                                    │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ 2. STEM GENERATION                                                    │   │
│  │                                                                       │   │
│  │    Select template (weighted) → Substitute parameters                 │   │
│  │    Example: "What is {a} × {b}?" → "What is 7 × 8?"                  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│         │                                                                    │
│         ▼                                                                    │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ 3. ANSWER COMPUTATION                                                 │   │
│  │                                                                       │   │
│  │    Evaluate answer template → Correct answer = 56                     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│         │                                                                    │
│         ▼                                                                    │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ 4. DISTRACTOR GENERATION (MCQ only)                                   │   │
│  │                                                                       │   │
│  │    Apply strategies:                                                  │   │
│  │    - off_by_one_factor: 7×7=49, 7×9=63                               │   │
│  │    - digit_swap: 65                                                   │   │
│  │    - addition_confusion: 15                                           │   │
│  │                                                                       │   │
│  │    Validate: no duplicates, no correct answer, plausible values      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│         │                                                                    │
│         ▼                                                                    │
│  ┌──────────────┐                                                            │
│  │  UniqueItem  │                                                            │
│  │              │                                                            │
│  │ • stem       │                                                            │
│  │ • options[]  │                                                            │
│  │ • correct_idx│                                                            │
│  │ • difficulty │                                                            │
│  │ • params{}   │                                                            │
│  └──────────────┘                                                            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Domain Events

| Event | Trigger | Key Data |
|-------|---------|----------|
| `skill-template.created.v1` | New template created | id, skill_id, name |
| `skill-template.updated.v1` | Template modified | id, changed_fields |
| `skill-template.submitted.v1` | Submitted for review | id, submitted_by |
| `skill-template.approved.v1` | Approved for use | id, approved_by |
| `skill-template.retired.v1` | Marked as retired | id, replacement_id |

## Validation Rules

| Rule | Condition | Error |
|------|-----------|-------|
| `valid_placeholders` | All {placeholders} in stems exist in parameters | "Unknown parameter in stem" |
| `difficulty_constraints_valid` | All constraints reference valid parameters | "Invalid constraint expression" |
| `answer_template_valid` | Answer template evaluates correctly | "Answer template error" |
| `sufficient_distractors` | distractor_strategies.count >= option_count - 1 | "Not enough distractor strategies" |
| `time_limit_reasonable` | time_limit >= 30 | "Time limit too short" |

## LLM Assistance Opportunities

| Task | LLM Role |
|------|----------|
| Stem variation | Generate alternative phrasings maintaining semantics |
| Distractor quality | Suggest plausible but incorrect options |
| Difficulty estimation | Predict difficulty based on parameters |
| Hint generation | Create progressive hints for candidate-tutor |
| Validation | Check for ambiguity, bias, clarity issues |

---

_Last updated: December 24, 2025_
