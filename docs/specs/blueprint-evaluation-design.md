# Blueprint-Driven Evaluation System

**Version:** 1.0.0
**Status:** `APPROVED`
**Date:** December 12, 2025
**Author:** Architecture Team

---

## 1. Executive Summary

This document defines the architecture for a **Blueprint-Driven Evaluation System** that uses LLM to generate assessment items on-the-fly from validated skill blueprints. This approach eliminates traditional item bank costs while maintaining psychometric validity.

### Key Innovation

Instead of authoring thousands of individual assessment items, we author **Skill Blueprints** that define:

- What skill to assess
- Constraints for item generation
- Difficulty factors
- Evaluation method

**The LLM generates BOTH the item content AND the correct answer** from the blueprint. The backend only stores and verifies - it does NOT compute answers.

### Critical Design Principle: LLM Generates, Backend Stores

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     WHO DOES WHAT?                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  LLM (Item Generator Agent):                                                 │
│  ─────────────────────────────                                               │
│  ✓ Reads blueprint constraints                                              │
│  ✓ Generates item content (stem, scenario, code snippet)                    │
│  ✓ Generates correct answer/solution                                        │
│  ✓ Generates plausible distractors                                          │
│  ✓ Returns structured JSON with ALL of the above                            │
│                                                                              │
│  Backend (Item Generator Service):                                           │
│  ──────────────────────────────────                                          │
│  ✓ Loads blueprint from YAML                                                │
│  ✓ Calls LLM with blueprint + generation prompt                             │
│  ✓ Validates LLM output against blueprint schema                            │
│  ✓ Stores generated item (including correct answer)                         │
│  ✓ Returns item to Proactive Agent WITHOUT correct answer                   │
│                                                                              │
│  Proactive Agent (Session Driver):                                           │
│  ──────────────────────────────────                                          │
│  ✓ Receives item without correct answer                                     │
│  ✓ Presents to user via client tools                                        │
│  ✓ Can see correct answer AFTER user responds (for feedback in Learning)    │
│  ✗ NEVER sends correct answer to browser                                    │
│                                                                              │
│  Browser/User:                                                               │
│  ───────────────                                                             │
│  ✗ NEVER sees correct answer until session complete (Evaluation)            │
│  ✓ Sees feedback with correct answer (Learning mode only)                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Why LLM Can See the Correct Answer

The LLM knowing the correct answer is **not a security risk** because:

1. The LLM is server-side - it cannot be inspected by the user
2. The system prompt instructs the LLM not to reveal answers (Evaluation mode)
3. For Learning sessions, the LLM SHOULD know the answer to provide feedback
4. The critical boundary is **browser ↔ server**, not **LLM ↔ backend**

### Scope

**Phase 1 Domains:**

- Mathematics (arithmetic operations)
- Networking (IP addressing, subnetting)

**Future Domains:**

- Programming (Python code challenges)
- Systems administration
- Database queries

---

## 2. Architecture Overview

### 2.1 System Components

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           EVALUATION SYSTEM                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌───────────────────┐     ┌───────────────────┐     ┌──────────────────┐   │
│  │  Blueprint Store  │     │  Item Generator   │     │ Session Manager  │   │
│  │  (YAML Files)     │────▶│  Service          │────▶│                  │   │
│  │                   │     │                   │     │                  │   │
│  │  - Skill defs     │     │  - Load blueprint │     │  - Orchestrate   │   │
│  │  - Constraints    │     │  - Call LLM to    │     │  - Track state   │   │
│  │  - Difficulty     │     │    generate item  │     │  - Store results │   │
│  │  - Assessment     │     │  - Validate output│     │  - Score session │   │
│  │    blueprints     │     │  - Store item     │     │                  │   │
│  └───────────────────┘     └───────────────────┘     └──────────────────┘   │
│                                   │                          │               │
│                                   ▼                          ▼               │
│  ┌───────────────────┐     ┌───────────────────┐     ┌──────────────────┐   │
│  │  LLM Provider     │     │  Evaluation Store │     │  Proactive Agent │   │
│  │  (Item Gen Agent) │     │  (MongoDB)        │     │  (Session Driver)│   │
│  │                   │     │                   │     │                  │   │
│  │  - Generate item  │     │  - Sessions       │     │  - Present items │   │
│  │    content        │     │  - Generated items│     │  - Handle flow   │   │
│  │  - Generate answer│     │  - Responses      │     │  - Give feedback │   │
│  │  - Generate       │     │  - Audit trail    │     │    (Learning)    │   │
│  │    distractors    │     │                   │     │                  │   │
│  └───────────────────┘     └───────────────────┘     └──────────────────┘   │
│                                                                              │
│  Note: There are TWO LLM usages:                                            │
│  1. Item Generator Agent - generates items from blueprints (internal)       │
│  2. Proactive Agent - drives session, presents items to user                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           EVALUATION FLOW                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. SESSION CREATION                                                         │
│  ───────────────────                                                         │
│                                                                              │
│  POST /session/ {assessment_id: "MATH-FUNDAMENTALS-L1"}                     │
│                                   │                                          │
│                                   ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Session Manager                                                     │    │
│  │  1. Load Assessment Blueprint (YAML)                                 │    │
│  │  2. Build item_plan: [(blueprint_id, difficulty, domain), ...]      │    │
│  │  3. Create Session aggregate                                         │    │
│  │  4. Return session_id + stream_url                                   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  2. ITEM GENERATION (per item, via LLM)                                      │
│  ──────────────────────────────────────                                      │
│                                                                              │
│  GET /session/{id}/stream                                                    │
│                                   │                                          │
│                                   ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Proactive Agent calls get_next_item()                               │    │
│  │                          │                                           │    │
│  │                          ▼                                           │    │
│  │  ┌─────────────────────────────────────────────────────────────┐    │    │
│  │  │  Item Generator Service                                      │    │    │
│  │  │  1. Get next blueprint_id from item_plan                     │    │    │
│  │  │  2. Load Skill Blueprint (YAML)                              │    │    │
│  │  │  3. ════════════════════════════════════════════════════     │    │    │
│  │  │     CALL LLM (Item Generator Agent) WITH:                    │    │    │
│  │  │     - Blueprint constraints                                   │    │    │
│  │  │     - Target difficulty level                                 │    │    │
│  │  │     - Generation prompt                                       │    │    │
│  │  │                                                               │    │    │
│  │  │     LLM RETURNS:                                              │    │    │
│  │  │     {                                                         │    │    │
│  │  │       "stem": "What is 47 + 38?",                             │    │    │
│  │  │       "options": ["75", "85", "86", "95"],                    │    │    │
│  │  │       "correct_answer": "85",         ◄── LLM generates this │    │    │
│  │  │       "correct_index": 1,                                     │    │    │
│  │  │       "explanation": "47+38=85..."    ◄── For feedback later │    │    │
│  │  │     }                                                         │    │    │
│  │  │     ════════════════════════════════════════════════════     │    │    │
│  │  │  4. Validate LLM output (schema, constraints)                │    │    │
│  │  │  5. Store complete item (WITH answer) for audit              │    │    │
│  │  │  6. Return item to Proactive Agent                           │    │    │
│  │  └─────────────────────────────────────────────────────────────┘    │    │
│  │                          │                                           │    │
│  │                          ▼                                           │    │
│  │  Proactive Agent receives (mode-dependent):                          │    │
│  │                                                                      │    │
│  │  EVALUATION MODE:                                                    │    │
│  │  {                                                                   │    │
│  │    "item_id": "gen_abc123",                                         │    │
│  │    "stem": "What is 47 + 38?",                                      │    │
│  │    "options": ["75", "85", "86", "95"]                              │    │
│  │    // NO correct_answer - proctor should not reveal                 │    │
│  │  }                                                                   │    │
│  │                                                                      │    │
│  │  LEARNING MODE:                                                      │    │
│  │  {                                                                   │    │
│  │    "item_id": "gen_abc123",                                         │    │
│  │    "stem": "What is 47 + 38?",                                      │    │
│  │    "options": ["75", "85", "86", "95"],                             │    │
│  │    "correct_answer": "85",        ◄── Tutor CAN see this            │    │
│  │    "explanation": "47+38=85..."   ◄── For providing feedback        │    │
│  │  }                                                                   │    │
│  │                          │                                           │    │
│  │                          ▼                                           │    │
│  │  Agent calls present_choices(prompt=stem, options=options)          │    │
│  │  → SSE: client_action → Frontend renders widget                     │    │
│  │  → SSE closes (waiting for user)                                    │    │
│  │                                                                      │    │
│  │  NOTE: Frontend NEVER receives correct_answer in either mode!       │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  3. RESPONSE SUBMISSION                                                      │
│  ──────────────────────                                                      │
│                                                                              │
│  POST /session/{id}/respond {tool_call_id, response: {index: 1}}            │
│                                   │                                          │
│                                   ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Session Manager                                                     │    │
│  │  1. Record response                                                  │    │
│  │  2. Retrieve stored generated item (has correct_answer)             │    │
│  │  3. Compare user response to stored correct_answer                  │    │
│  │  4. Update session metrics                                          │    │
│  │  5. Return result to Proactive Agent:                               │    │
│  │                                                                      │    │
│  │     EVALUATION: {"recorded": true, "has_more": true}                │    │
│  │     LEARNING:   {"correct": true, "explanation": "...", ...}        │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  4. SESSION COMPLETION                                                       │
│  ─────────────────────                                                       │
│                                                                              │
│  After last item:                                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Session Manager                                                     │    │
│  │  1. Compute final score                                              │    │
│  │  2. Generate performance summary                                     │    │
│  │  3. Transition session to COMPLETED                                  │    │
│  │  4. Agent presents summary to user                                   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Domain Models

### 3.1 Skill Blueprint (YAML)

```yaml
# blueprints/skills/math/arithmetic/add_2digit.yaml

skill_id: "MATH.ARITH.ADD.2DIGIT"
version: "1.0"

metadata:
  domain: "Mathematics"
  subdomain: "Arithmetic"
  topic: "Addition"
  skill_statement: "Accurately add two 2-digit positive integers"
  cognitive_level: "Apply"  # Bloom's taxonomy

generation:
  item_type: "multiple_choice"

  parameters:
    operand_1:
      type: integer
      min: 10
      max: 99
    operand_2:
      type: integer
      min: 10
      max: 99

  # Correct answer computation (Python expression)
  answer_formula: "operand_1 + operand_2"
  answer_type: integer

  # Difficulty is determined by constraint selection
  difficulty_levels:
    easy:
      value: 0.3
      constraints:
        # No carrying: both ones digits sum < 10, both tens sum < 10
        - "operand_1 % 10 + operand_2 % 10 < 10"
        - "operand_1 // 10 + operand_2 // 10 < 10"

    medium:
      value: 0.5
      constraints:
        # Single carry in ones place
        - "operand_1 % 10 + operand_2 % 10 >= 10"
        - "operand_1 // 10 + operand_2 // 10 < 10"

    hard:
      value: 0.7
      constraints:
        # Carry in ones place leads to carry in tens
        - "operand_1 % 10 + operand_2 % 10 >= 10"
        - "(operand_1 // 10 + operand_2 // 10 + 1) >= 10"

presentation:
  stem_templates:
    - "What is {operand_1} + {operand_2}?"
    - "Calculate: {operand_1} + {operand_2} = ?"
    - "Find the sum of {operand_1} and {operand_2}."

  option_count: 4

  distractor_strategies:
    - type: "off_by_10"
      description: "Common place value error"
      formula: "answer + 10"
    - type: "off_by_10_negative"
      formula: "answer - 10"
    - type: "off_by_1"
      description: "Careless error"
      formula: "answer + 1"
    - type: "off_by_1_negative"
      formula: "answer - 1"
    - type: "wrong_operation"
      description: "Subtraction instead of addition"
      formula: "abs(operand_1 - operand_2)"
      condition: "operand_1 != operand_2"

  # Ensure distractors are valid
  distractor_validation:
    - "distractor > 0"
    - "distractor != answer"
    - "distractor not in other_distractors"

evaluation:
  method: "exact_match"
  partial_credit: false

performance_benchmarks:
  novice:
    expected_accuracy: 0.60
    expected_time_seconds: 30
  competent:
    expected_accuracy: 0.85
    expected_time_seconds: 15
  expert:
    expected_accuracy: 0.98
    expected_time_seconds: 5
```

### 3.2 Networking Blueprint Example

```yaml
# blueprints/skills/networking/ip/subnet_network_address.yaml

skill_id: "NET.IP.SUBNET.NETWORK"
version: "1.0"

metadata:
  domain: "Networking"
  subdomain: "IP Addressing"
  topic: "Subnetting"
  skill_statement: "Calculate network address from IP address and CIDR notation"
  cognitive_level: "Apply"

generation:
  item_type: "multiple_choice"

  parameters:
    ip_octet_1:
      type: integer
      min: 1
      max: 223
      exclude: [127]  # Loopback
    ip_octet_2:
      type: integer
      min: 0
      max: 255
    ip_octet_3:
      type: integer
      min: 0
      max: 255
    ip_octet_4:
      type: integer
      min: 1
      max: 254
    cidr:
      type: integer
      min: 8
      max: 30

  # Helper computed values (available in formulas)
  computed_values:
    ip_address: "f'{ip_octet_1}.{ip_octet_2}.{ip_octet_3}.{ip_octet_4}'"
    subnet_mask: "cidr_to_mask(cidr)"
    network_address: "compute_network_address(ip_octet_1, ip_octet_2, ip_octet_3, ip_octet_4, cidr)"
    broadcast_address: "compute_broadcast_address(ip_octet_1, ip_octet_2, ip_octet_3, ip_octet_4, cidr)"

  answer_formula: "network_address"
  answer_type: string

  difficulty_levels:
    easy:
      value: 0.3
      constraints:
        # CIDR on byte boundary
        - "cidr in [8, 16, 24]"

    medium:
      value: 0.5
      constraints:
        # CIDR not on byte boundary but in last octet
        - "cidr >= 24"
        - "cidr not in [8, 16, 24]"

    hard:
      value: 0.7
      constraints:
        # CIDR affects multiple octets
        - "cidr < 24"
        - "cidr not in [8, 16]"

presentation:
  stem_templates:
    - "What is the network address for {ip_address}/{cidr}?"
    - "Given IP {ip_address} with CIDR /{cidr}, calculate the network address."
    - "Find the network address: {ip_address}/{cidr}"

  option_count: 4

  distractor_strategies:
    - type: "broadcast_address"
      description: "Broadcast instead of network"
      formula: "broadcast_address"
    - type: "original_ip"
      description: "Original IP (no calculation)"
      formula: "ip_address"
    - type: "first_host"
      description: "First usable host"
      formula: "compute_first_host(ip_octet_1, ip_octet_2, ip_octet_3, ip_octet_4, cidr)"
    - type: "off_by_one_octet"
      description: "Error in one octet"
      formula: "network_with_error(network_address, 'increment_octet_3')"

evaluation:
  method: "exact_match"
  partial_credit: false
```

### 3.3 Assessment Blueprint (YAML)

```yaml
# blueprints/assessments/math-fundamentals-l1.yaml

assessment_id: "MATH-FUNDAMENTALS-L1"
version: "1.0"

metadata:
  title: "Mathematics Fundamentals - Level 1"
  description: "Basic arithmetic operations assessment"
  target_audience: "Elementary level"
  estimated_duration_minutes: 30

configuration:
  total_items: 20
  time_limit_minutes: 30
  passing_score_percent: 70
  shuffle_items: true
  shuffle_options: true
  show_progress: true
  allow_review: false
  allow_skip: false

sections:
  - section_id: "addition"
    title: "Addition"
    item_count: 5
    skill_blueprints:
      - skill_id: "MATH.ARITH.ADD.1DIGIT"
        weight: 1
      - skill_id: "MATH.ARITH.ADD.2DIGIT"
        weight: 2
      - skill_id: "MATH.ARITH.ADD.3DIGIT"
        weight: 1
    difficulty_distribution:
      easy: 2
      medium: 2
      hard: 1

  - section_id: "subtraction"
    title: "Subtraction"
    item_count: 5
    skill_blueprints:
      - skill_id: "MATH.ARITH.SUB.1DIGIT"
        weight: 1
      - skill_id: "MATH.ARITH.SUB.2DIGIT"
        weight: 2
      - skill_id: "MATH.ARITH.SUB.BORROW"
        weight: 1
    difficulty_distribution:
      easy: 2
      medium: 2
      hard: 1

  - section_id: "multiplication"
    title: "Multiplication"
    item_count: 5
    skill_blueprints:
      - skill_id: "MATH.ARITH.MUL.SINGLE"
        weight: 2
      - skill_id: "MATH.ARITH.MUL.BY10"
        weight: 1
      - skill_id: "MATH.ARITH.MUL.2BY1"
        weight: 1
    difficulty_distribution:
      easy: 2
      medium: 2
      hard: 1

  - section_id: "division"
    title: "Division"
    item_count: 5
    skill_blueprints:
      - skill_id: "MATH.ARITH.DIV.SINGLE"
        weight: 2
      - skill_id: "MATH.ARITH.DIV.BY10"
        weight: 1
      - skill_id: "MATH.ARITH.DIV.2BY1"
        weight: 1
    difficulty_distribution:
      easy: 2
      medium: 2
      hard: 1

scoring:
  method: "percent_correct"
  section_weights:
    addition: 0.25
    subtraction: 0.25
    multiplication: 0.25
    division: 0.25

  grade_bands:
    - label: "Expert"
      min_percent: 90
    - label: "Proficient"
      min_percent: 80
    - label: "Competent"
      min_percent: 70
    - label: "Developing"
      min_percent: 60
    - label: "Novice"
      min_percent: 0
```

### 3.4 Generated Item (Stored for Audit)

```python
@dataclass
class GeneratedItem:
    """A generated item instance stored for audit and scoring."""

    # Identity
    id: str  # UUID
    session_id: str
    blueprint_id: str  # e.g., "MATH.ARITH.ADD.2DIGIT"

    # Generation details
    generated_at: datetime
    generation_params: dict  # {"operand_1": 47, "operand_2": 38, ...}
    difficulty_level: str  # "easy", "medium", "hard"
    difficulty_value: float  # 0.5

    # Item content
    stem: str  # "What is 47 + 38?"
    item_type: str  # "multiple_choice"
    options: list[str]  # ["75", "85", "86", "95"]
    options_shuffled: bool

    # Answer (NEVER sent to LLM)
    correct_answer: str  # "85"
    correct_index: int  # Index in shuffled options

    # Presentation order
    sequence_number: int  # Item 3 of 20
    section_id: str  # "addition"

    # Response (filled after user responds)
    user_response: str | None  # "85"
    user_response_index: int | None  # 1
    is_correct: bool | None
    response_time_ms: int | None
    responded_at: datetime | None
```

### 3.5 Session State

```python
@dataclass
class EvaluationSessionState:
    """State for an evaluation session."""

    # Identity
    id: str
    user_id: str
    assessment_id: str  # "MATH-FUNDAMENTALS-L1"
    conversation_id: str

    # Status
    status: SessionStatus  # PENDING, ACTIVE, AWAITING_RESPONSE, COMPLETED, TERMINATED

    # Plan (built at session creation)
    item_plan: list[ItemPlanEntry]  # [{blueprint_id, difficulty_level, section_id}, ...]
    total_items: int

    # Progress
    current_item_index: int  # 0-based
    current_item_id: str | None  # Generated item ID
    items_completed: int

    # Timing
    time_limit_seconds: int | None
    started_at: datetime | None
    completed_at: datetime | None
    time_remaining_seconds: int | None

    # Pending action (for widget state)
    pending_action: ClientAction | None

    # Results (populated as session progresses)
    section_results: dict[str, SectionResult]

    # Configuration
    config: dict  # From assessment blueprint


@dataclass
class ItemPlanEntry:
    """An entry in the session's item plan."""
    blueprint_id: str
    difficulty_level: str
    section_id: str


@dataclass
class SectionResult:
    """Results for a section."""
    section_id: str
    items_attempted: int
    items_correct: int
    accuracy: float
    avg_response_time_ms: float
```

---

## 4. Component Design

### 4.1 Blueprint Store

**Responsibility:** Load and validate YAML blueprints

**Location:** `domain/services/blueprint_store.py`

```python
class BlueprintStore:
    """Manages skill and assessment blueprints."""

    def __init__(self, blueprints_path: Path):
        self._blueprints_path = blueprints_path
        self._skill_cache: dict[str, SkillBlueprint] = {}
        self._assessment_cache: dict[str, AssessmentBlueprint] = {}

    async def get_skill_blueprint(self, skill_id: str) -> SkillBlueprint:
        """Load a skill blueprint by ID."""
        ...

    async def get_assessment_blueprint(self, assessment_id: str) -> AssessmentBlueprint:
        """Load an assessment blueprint by ID."""
        ...

    async def list_assessments(self) -> list[AssessmentSummary]:
        """List available assessments."""
        ...

    def validate_blueprint(self, blueprint: dict) -> ValidationResult:
        """Validate blueprint schema and constraints."""
        ...
```

### 4.2 Item Generator Service

**Responsibility:** Orchestrate LLM-based item generation from blueprints

**Location:** `application/services/item_generator.py`

**Key Insight:** The Item Generator Service does NOT compute answers itself. It:

1. Loads the blueprint
2. Calls an LLM (Item Generator Agent) with a specialized prompt
3. Validates the LLM's output
4. Stores the complete item (with answer) for audit

```python
class ItemGeneratorService:
    """Generates assessment items by calling LLM with blueprint constraints."""

    def __init__(
        self,
        blueprint_store: BlueprintStore,
        llm_provider: LlmProvider,
        item_repository: Repository[GeneratedItem, str],
    ):
        self._blueprint_store = blueprint_store
        self._llm = llm_provider
        self._item_repository = item_repository

    async def generate_item(
        self,
        blueprint_id: str,
        difficulty_level: str,
        session_id: str,
        sequence_number: int,
        section_id: str,
    ) -> GeneratedItem:
        """Generate a single item from a blueprint using LLM."""

        # 1. Load blueprint
        blueprint = await self._blueprint_store.get_skill_blueprint(blueprint_id)

        # 2. Build the generation prompt for LLM
        prompt = self._build_generation_prompt(blueprint, difficulty_level)

        # 3. Call LLM to generate item content + answer + distractors
        llm_response = await self._llm.generate_structured(
            system_prompt=ITEM_GENERATOR_SYSTEM_PROMPT,
            user_prompt=prompt,
            response_schema=GeneratedItemSchema,  # JSON schema for validation
        )

        # 4. Validate LLM output against blueprint constraints
        validated = self._validate_llm_output(llm_response, blueprint)

        # 5. Create GeneratedItem with ALL data (including correct answer)
        item = GeneratedItem(
            id=str(uuid4()),
            session_id=session_id,
            blueprint_id=blueprint_id,
            generated_at=datetime.now(UTC),
            difficulty_level=difficulty_level,
            stem=validated["stem"],
            item_type=blueprint.item_type,
            options=validated["options"],
            correct_answer=validated["correct_answer"],
            correct_index=validated["correct_index"],
            explanation=validated.get("explanation"),  # For learning feedback
            sequence_number=sequence_number,
            section_id=section_id,
        )

        # 6. Store for audit trail
        await self._item_repository.add_async(item)

        return item

    def _build_generation_prompt(
        self,
        blueprint: SkillBlueprint,
        difficulty_level: str
    ) -> str:
        """Build prompt that instructs LLM how to generate the item."""
        return f"""
Generate an assessment item for this skill:

SKILL: {blueprint.skill_statement}
DOMAIN: {blueprint.domain}
DIFFICULTY: {difficulty_level}
ITEM TYPE: {blueprint.item_type}

CONSTRAINTS:
{yaml.dump(blueprint.generation_constraints)}

DIFFICULTY FACTORS FOR {difficulty_level}:
{yaml.dump(blueprint.difficulty_levels[difficulty_level])}

DISTRACTOR GUIDELINES:
{yaml.dump(blueprint.distractor_strategies)}

Generate a complete item with:
1. A clear, unambiguous stem (question)
2. The correct answer (computed/determined by you)
3. {blueprint.option_count - 1} plausible but incorrect distractors
4. A brief explanation of WHY the answer is correct

Return as JSON matching this schema:
{{
  "stem": "...",
  "options": ["...", "...", "...", "..."],  // Shuffled, correct mixed in
  "correct_answer": "...",
  "correct_index": 0-3,  // Index of correct answer in options
  "explanation": "..."
}}
"""

    def _validate_llm_output(
        self,
        response: dict,
        blueprint: SkillBlueprint
    ) -> dict:
        """Validate LLM output meets blueprint requirements."""
        # Check option count
        # Check correct_index is valid
        # Check correct_answer matches options[correct_index]
        # Check no duplicate options
        # etc.
        ...
```

### 4.3 Item Generator Agent System Prompt

The Item Generator Agent is a **separate LLM call** with a specialized prompt for generating items. It's different from the Proactive Agent that presents items to users.

```python
ITEM_GENERATOR_SYSTEM_PROMPT = """You are an expert assessment item writer.

Your job is to generate high-quality assessment items from skill blueprints.

## Requirements

1. ACCURACY: The correct answer you provide MUST be mathematically/factually correct.
   - For math: compute the actual result
   - For networking: apply the actual rules (subnetting, etc.)
   - For code: ensure the solution actually works

2. CLARITY: The stem should be unambiguous. One and only one answer is correct.

3. DISTRACTORS: Wrong options should be:
   - Plausible (represent common errors)
   - Clearly distinguishable from each other
   - Not "trick" questions

4. DIFFICULTY: Follow the difficulty constraints provided:
   - Easy: Straightforward application
   - Medium: Requires multi-step thinking
   - Hard: Edge cases or complex scenarios

5. EXPLANATION: Provide a clear explanation that could be shown to a learner
   after they answer (whether correct or not).

## Output Format

Always return valid JSON with this structure:
{
  "stem": "The question text",
  "options": ["A", "B", "C", "D"],  // 4 options, shuffled
  "correct_answer": "B",  // The actual correct value
  "correct_index": 1,  // 0-based index in options array
  "explanation": "Why B is correct..."
}
"""
```

### 4.4 Session Manager

**Responsibility:** Orchestrate evaluation sessions

**Location:** `application/services/evaluation_session_manager.py`

```python
class EvaluationSessionManager:
    """Manages evaluation session lifecycle."""

    def __init__(
        self,
        blueprint_store: BlueprintStore,
        item_generator: ItemGenerator,
        session_repository: Repository[Session, str],
        generated_item_repository: Repository[GeneratedItem, str],
    ):
        ...

    async def create_session(
        self,
        user_id: str,
        assessment_id: str,
    ) -> Session:
        """Create a new evaluation session."""

        # 1. Load assessment blueprint
        assessment = await self._blueprint_store.get_assessment_blueprint(assessment_id)

        # 2. Build item plan
        item_plan = self._build_item_plan(assessment)

        # 3. Create session aggregate
        session = Session.create_evaluation(
            user_id=user_id,
            assessment_id=assessment_id,
            item_plan=item_plan,
            config=assessment.configuration,
        )

        # 4. Persist
        await self._session_repository.add_async(session)

        return session

    async def get_next_item(self, session_id: str) -> dict | None:
        """Get the next item for the session (called by agent tool)."""

        # 1. Load session
        session = await self._session_repository.get_async(session_id)

        # 2. Check if more items
        if session.state.current_item_index >= session.state.total_items:
            return None  # No more items

        # 3. Get plan entry
        plan_entry = session.state.item_plan[session.state.current_item_index]

        # 4. Generate item
        item = await self._item_generator.generate_item(
            blueprint_id=plan_entry.blueprint_id,
            difficulty_level=plan_entry.difficulty_level,
            session_id=session_id,
            sequence_number=session.state.current_item_index + 1,
            section_id=plan_entry.section_id,
        )

        # 5. Store generated item for audit
        await self._generated_item_repository.add_async(item)

        # 6. Update session state
        session.set_current_item(item.id)
        await self._session_repository.update_async(session)

        # 7. Return item WITHOUT correct answer
        return {
            "item_id": item.id,
            "item_number": item.sequence_number,
            "total_items": session.state.total_items,
            "stem": item.stem,
            "item_type": item.item_type,
            "options": item.options,
            "section": plan_entry.section_id,
            "time_limit_seconds": session.state.config.get("item_time_limit_seconds"),
        }

    async def record_response(
        self,
        session_id: str,
        item_id: str,
        response_index: int,
        response_time_ms: int,
    ) -> dict:
        """Record a user's response and compute correctness."""

        # 1. Load session and generated item
        session = await self._session_repository.get_async(session_id)
        item = await self._generated_item_repository.get_async(item_id)

        # 2. Compute correctness (BACKEND, NOT LLM)
        is_correct = response_index == item.correct_index

        # 3. Update generated item
        item.user_response = item.options[response_index]
        item.user_response_index = response_index
        item.is_correct = is_correct
        item.response_time_ms = response_time_ms
        item.responded_at = datetime.now(UTC)
        await self._generated_item_repository.update_async(item)

        # 4. Update session metrics
        session.record_response(
            item_id=item_id,
            is_correct=is_correct,
            response_time_ms=response_time_ms,
            section_id=item.section_id,
        )

        # 5. Advance to next item
        session.advance_to_next_item()
        await self._session_repository.update_async(session)

        # 6. Return result
        has_more = session.state.current_item_index < session.state.total_items

        return {
            "recorded": True,
            "has_more_items": has_more,
            "items_completed": session.state.items_completed,
            "total_items": session.state.total_items,
        }

    async def complete_session(self, session_id: str) -> dict:
        """Complete the session and compute final score."""

        session = await self._session_repository.get_async(session_id)

        # Compute final results
        results = self._compute_results(session)

        # Transition to completed
        session.complete(results)
        await self._session_repository.update_async(session)

        return results
```

### 4.5 Backend Tools for Agent

**Responsibility:** Tools the agent calls to drive the evaluation

**Location:** `application/agents/evaluation_tools.py`

```python
# These are BACKEND tools, not client tools
# They execute on the server and return data to the agent

EVALUATION_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_next_item",
            "description": """Get the next assessment item to present to the user.
            Returns the item content including stem and options.
            Returns null if no more items (session complete).
            IMPORTANT: Never modify the item content - present it exactly as provided.""",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "record_response",
            "description": """Record the user's response to the current item.
            Call this AFTER the user has submitted their answer via the widget.
            Returns whether there are more items or if session is complete.""",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "string",
                        "description": "The item ID from get_next_item",
                    },
                    "response_index": {
                        "type": "integer",
                        "description": "The index of the selected option (0-based)",
                    },
                    "response_time_ms": {
                        "type": "integer",
                        "description": "Time taken to respond in milliseconds",
                    },
                },
                "required": ["item_id", "response_index", "response_time_ms"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "complete_session",
            "description": """Complete the evaluation session and get final results.
            Call this when get_next_item returns null (no more items).
            Returns the final score and performance summary.""",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]
```

### 4.6 System Prompt for Evaluation Agent

```python
EVALUATION_SESSION_PROMPT = """You are an assessment proctor administering a timed evaluation.

## Your Role
- Present assessment items to the user exactly as provided
- Maintain a professional, neutral tone
- Track time and progress
- Do NOT provide hints, feedback, or evaluate answers
- Do NOT modify item content in any way

## Available Tools

### Backend Tools (execute on server):
- get_next_item(): Get the next assessment item. Returns item content or null if complete.
- record_response(item_id, response_index, response_time_ms): Record the user's answer.
- complete_session(): Finalize the session and get results.

### Client Tools (render UI widgets):
- present_choices(prompt, options): Display multiple choice question.

## Session Flow

1. Call get_next_item() to get the first item
2. Use present_choices() to display it to the user
3. When user responds, call record_response() with their answer
4. If has_more_items is true, call get_next_item() for the next item
5. If has_more_items is false, call complete_session() and present results

## Important Rules

- NEVER reveal correct answers
- NEVER provide hints or feedback during the assessment
- NEVER skip items or change the order
- Present items EXACTLY as provided (do not rephrase)
- Keep track of time remaining and warn user if running low

## Session Info
Assessment: {assessment_title}
Total Items: {total_items}
Time Limit: {time_limit_minutes} minutes

Begin by calling get_next_item() to start the assessment.
"""
```

---

## 5. API Endpoints

### 5.1 Session Controller Updates

```python
# New/modified endpoints in SessionController

@post("/")
async def create_session(
    self,
    body: CreateSessionRequest,
    user: dict = Depends(get_current_user),
) -> CreateSessionResponse:
    """Create a new evaluation session."""
    # body.assessment_id required for evaluation type
    ...

@get("/{session_id}/stream")
async def stream_session(
    self,
    session_id: str,
    user: dict = Depends(get_current_user),
) -> StreamingResponse:
    """Stream session events (SSE)."""
    # On reconnect after response, continues from where left off
    ...

@post("/{session_id}/respond")
async def submit_response(
    self,
    session_id: str,
    body: SubmitResponseRequest,
    user: dict = Depends(get_current_user),
) -> SubmitResponseResponse:
    """Submit response to current item."""
    # Records response, computes correctness
    # Returns signal to reconnect to stream
    ...

@get("/{session_id}/results")
async def get_results(
    self,
    session_id: str,
    user: dict = Depends(get_current_user),
) -> SessionResultsResponse:
    """Get session results (after completion)."""
    ...
```

### 5.2 Request/Response Models

```python
class CreateSessionRequest(BaseModel):
    session_type: Literal["evaluation"]
    assessment_id: str  # e.g., "MATH-FUNDAMENTALS-L1"


class CreateSessionResponse(BaseModel):
    session_id: str
    assessment_title: str
    total_items: int
    time_limit_minutes: int | None
    stream_url: str


class SubmitResponseRequest(BaseModel):
    tool_call_id: str
    response: dict  # {"index": 1, "selection": "85"}


class SubmitResponseResponse(BaseModel):
    recorded: bool
    items_completed: int
    total_items: int
    continue_url: str  # Stream URL to reconnect


class SessionResultsResponse(BaseModel):
    session_id: str
    assessment_id: str
    completed_at: str
    duration_seconds: int

    total_items: int
    items_correct: int
    score_percent: float
    grade: str  # "Proficient", "Competent", etc.

    section_results: list[SectionResultResponse]


class SectionResultResponse(BaseModel):
    section_id: str
    section_title: str
    items_attempted: int
    items_correct: int
    accuracy_percent: float
```

---

## 6. File Structure

```
src/agent-host/
├── domain/
│   ├── entities/
│   │   └── session.py                 # Updated with evaluation state
│   ├── models/
│   │   ├── blueprint_models.py        # NEW: SkillBlueprint, AssessmentBlueprint
│   │   ├── generated_item.py          # NEW: GeneratedItem
│   │   └── session_models.py          # Updated: ItemPlanEntry, SectionResult
│   ├── services/
│   │   ├── blueprint_store.py         # NEW: Load YAML blueprints
│   │   ├── item_generator.py          # NEW: Generate items
│   │   └── formula_evaluator.py       # NEW: Safe expression evaluation
│   └── events/
│       └── session.py                 # Add evaluation-specific events
│
├── application/
│   ├── services/
│   │   └── evaluation_session_manager.py  # NEW: Orchestration
│   ├── agents/
│   │   ├── evaluation_tools.py        # NEW: Backend tools
│   │   └── proactive_agent.py         # Updated: Tool execution
│   └── commands/
│       ├── create_session_command.py  # Updated: Support evaluation
│       └── record_response_command.py # NEW: Record & score
│
├── api/
│   └── controllers/
│       └── session_controller.py      # Updated endpoints
│
├── integration/
│   ├── repositories/
│   │   └── generated_item_repository.py  # NEW: Store generated items
│   └── models/
│       └── generated_item_dto.py      # NEW: DTO for persistence
│
├── blueprints/                        # NEW: YAML blueprint files
│   ├── skills/
│   │   ├── math/
│   │   │   └── arithmetic/
│   │   │       ├── add_1digit.yaml
│   │   │       ├── add_2digit.yaml
│   │   │       ├── add_3digit.yaml
│   │   │       ├── sub_1digit.yaml
│   │   │       ├── sub_2digit.yaml
│   │   │       ├── sub_borrow.yaml
│   │   │       ├── mul_single.yaml
│   │   │       ├── mul_by10.yaml
│   │   │       ├── mul_2by1.yaml
│   │   │       ├── div_single.yaml
│   │   │       ├── div_by10.yaml
│   │   │       └── div_2by1.yaml
│   │   └── networking/
│   │       └── ip/
│   │           ├── subnet_network_address.yaml
│   │           ├── subnet_broadcast.yaml
│   │           ├── subnet_host_count.yaml
│   │           └── cidr_to_mask.yaml
│   └── assessments/
│       ├── math-fundamentals-l1.yaml
│       └── networking-basics-l1.yaml
│
└── tests/
    ├── domain/
    │   ├── test_blueprint_store.py
    │   ├── test_item_generator.py
    │   └── test_formula_evaluator.py
    └── application/
        └── test_evaluation_session_manager.py
```

---

## 7. Implementation Plan

### Phase 1A: Foundation (Week 1)

**Goal:** Core infrastructure without LLM integration

| Task | Description | Files | Priority |
|------|-------------|-------|----------|
| 1.1 | Blueprint models | `domain/models/blueprint_models.py` | P0 |
| 1.2 | GeneratedItem model | `domain/models/generated_item.py` | P0 |
| 1.3 | Blueprint store | `domain/services/blueprint_store.py` | P0 |
| 1.4 | Formula evaluator | `domain/services/formula_evaluator.py` | P0 |
| 1.5 | Item generator | `domain/services/item_generator.py` | P0 |
| 1.6 | Math blueprints (3) | `blueprints/skills/math/arithmetic/*.yaml` | P0 |
| 1.7 | Unit tests | `tests/domain/test_*.py` | P0 |

**Deliverable:** Can generate math items from blueprints with correct answers

### Phase 1B: Session Flow (Week 2)

**Goal:** Complete evaluation session without frontend

| Task | Description | Files | Priority |
|------|-------------|-------|----------|
| 2.1 | Session state updates | `domain/entities/session.py` | P0 |
| 2.2 | Evaluation session manager | `application/services/evaluation_session_manager.py` | P0 |
| 2.3 | Generated item repository | `integration/repositories/generated_item_repository.py` | P0 |
| 2.4 | Backend tools definition | `application/agents/evaluation_tools.py` | P0 |
| 2.5 | Assessment blueprint | `blueprints/assessments/math-fundamentals-l1.yaml` | P0 |
| 2.6 | Tool executor integration | `application/agents/proactive_agent.py` | P1 |
| 2.7 | Integration tests | `tests/application/test_evaluation_session_manager.py` | P0 |

**Deliverable:** Can run complete evaluation session via API (no UI)

### Phase 1C: Agent Integration (Week 3)

**Goal:** LLM-driven evaluation flow

| Task | Description | Files | Priority |
|------|-------------|-------|----------|
| 3.1 | Evaluation system prompt | `application/agents/proactive_agent.py` | P0 |
| 3.2 | Tool execution for backend tools | `application/agents/proactive_agent.py` | P0 |
| 3.3 | Session controller updates | `api/controllers/session_controller.py` | P0 |
| 3.4 | SSE reconnection flow | `api/controllers/session_controller.py` | P1 |
| 3.5 | End-to-end tests | `tests/e2e/test_evaluation_flow.py` | P0 |

**Deliverable:** Complete evaluation flow via SSE with LLM

### Phase 1D: Frontend & Polish (Week 4)

**Goal:** Full user experience

| Task | Description | Files | Priority |
|------|-------------|-------|----------|
| 4.1 | Evaluation session UI | `ui/src/components/evaluation-session.js` | P0 |
| 4.2 | Results display | `ui/src/components/evaluation-results.js` | P1 |
| 4.3 | Timer component | `ui/src/components/session-timer.js` | P1 |
| 4.4 | Additional math blueprints | `blueprints/skills/math/arithmetic/*.yaml` | P1 |
| 4.5 | Networking blueprints | `blueprints/skills/networking/ip/*.yaml` | P2 |
| 4.6 | Documentation | `docs/evaluation-system.md` | P2 |

**Deliverable:** Fully functional evaluation system for math + networking

---

## 8. Testing Strategy

### 8.1 Unit Tests

```python
# tests/domain/test_item_generator.py

class TestItemGenerator:
    """Tests for item generation."""

    def test_generate_math_addition_easy(self):
        """Should generate valid easy addition item."""
        item = generator.generate_item(
            blueprint_id="MATH.ARITH.ADD.2DIGIT",
            difficulty_level="easy",
            session_id="test",
            sequence_number=1,
            section_id="addition",
        )

        # Verify no carrying (easy constraint)
        params = item.generation_params
        ones_sum = params["operand_1"] % 10 + params["operand_2"] % 10
        tens_sum = params["operand_1"] // 10 + params["operand_2"] // 10
        assert ones_sum < 10
        assert tens_sum < 10

        # Verify correct answer
        expected = params["operand_1"] + params["operand_2"]
        assert item.correct_answer == str(expected)

        # Verify distractors are valid
        assert len(item.options) == 4
        assert str(expected) in item.options
        assert item.correct_index == item.options.index(str(expected))

    def test_generate_unique_items(self):
        """Should generate different items each time."""
        items = [
            generator.generate_item("MATH.ARITH.ADD.2DIGIT", "medium", "s1", i, "add")
            for i in range(10)
        ]

        stems = [item.stem for item in items]
        assert len(set(stems)) == 10  # All unique
```

### 8.2 Integration Tests

```python
# tests/application/test_evaluation_session_manager.py

class TestEvaluationSessionManager:
    """Integration tests for session flow."""

    async def test_complete_session_flow(self):
        """Should complete a full evaluation session."""
        # Create session
        session = await manager.create_session(
            user_id="user1",
            assessment_id="MATH-FUNDAMENTALS-L1",
        )
        assert session.state.total_items == 20

        # Process all items
        for i in range(20):
            item = await manager.get_next_item(session.id())
            assert item is not None

            # Simulate response (always correct for test)
            result = await manager.record_response(
                session_id=session.id(),
                item_id=item["item_id"],
                response_index=...,  # Would need to look up correct
                response_time_ms=5000,
            )

            if i < 19:
                assert result["has_more_items"] is True
            else:
                assert result["has_more_items"] is False

        # Complete session
        results = await manager.complete_session(session.id())
        assert results["total_items"] == 20
        assert results["score_percent"] == 100.0
```

---

## 9. Security Considerations

### 9.1 Correct Answer Protection

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CORRECT ANSWER NEVER EXPOSED                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ✅ Stored in GeneratedItem (backend only)                                   │
│  ✅ NEVER included in get_next_item() response                               │
│  ✅ NEVER in LLM context or system prompt                                    │
│  ✅ NEVER in SSE events to frontend                                          │
│  ✅ Correctness computed by backend on record_response()                     │
│                                                                              │
│  The LLM literally cannot know the answer - it's not in its context.        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 9.2 Formula Evaluation Safety

```python
# Only allow safe operations
SAFE_BUILTINS = {"abs", "min", "max", "round", "int", "str", "len"}

# No access to:
# - file system
# - network
# - imports
# - eval/exec
# - __builtins__
```

### 9.3 Rate Limiting

- Limit session creation per user
- Limit items per session (from blueprint)
- Limit concurrent sessions

---

## 10. Future Enhancements

### 10.1 Adaptive Item Selection (Phase 2)

Based on IRT-lite:

- Track ability estimate per domain
- Select next item difficulty based on ability
- Implement CAT (Computerized Adaptive Testing)

### 10.2 Programming Challenges (Phase 2)

- Code execution sandbox
- Test case generation
- Partial credit based on tests passed

### 10.3 Analytics Service (Phase 3)

- Difficulty calibration from response data
- Item discrimination analysis
- Blueprint effectiveness metrics

---

## 11. Success Criteria

### Phase 1 Complete When

- [ ] Can create evaluation session from assessment blueprint
- [ ] Can generate unique math items from skill blueprints
- [ ] Correct answers computed deterministically by backend
- [ ] Session flows through all items via SSE
- [ ] Responses recorded with correctness computed
- [ ] Final score calculated correctly
- [ ] Generated items stored for audit
- [ ] Networking blueprints functional
- [ ] All tests passing

### Key Metrics

| Metric | Target |
|--------|--------|
| Item generation time | < 100ms |
| Correct answer accuracy | 100% (deterministic) |
| Session completion rate | > 95% |
| Test coverage | > 80% |

---

_Document finalized: December 12, 2025_
_Ready for implementation_
