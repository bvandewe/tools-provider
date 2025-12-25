# MVP Implementation Roadmap

> **Status:** Active Implementation Plan
> **Version:** 1.0
> **Last Updated:** December 2025
> **Focus:** Blueprint Authoring → Content Authoring → Exam Delivery

---

## Executive Summary

This roadmap prioritizes the **critical path** to an MVP that demonstrates AI-driven certification workflows. The goal is a working demo of:

1. **Blueprint Authoring**: EPM creates a blueprint with AI assistance
2. **Content Authoring**: SME creates items/SkillTemplates with AI assistance
3. **Exam Delivery**: Candidate experiences SkillTemplate-driven UI widgets in a Conversation

### Dependency Chain

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           MVP CRITICAL PATH                                          │
│                                                                                      │
│  PHASE 0                PHASE 1                PHASE 2               PHASE 3        │
│  Infrastructure         Blueprint Authoring    Content Authoring     Exam Delivery  │
│                                                                                      │
│  ┌─────────────┐        ┌─────────────┐        ┌─────────────┐       ┌───────────┐  │
│  │ knowledge-  │        │ blueprint-  │        │ SkillTemplate│       │Conversation│  │
│  │ manager     │───────►│ manager     │───────►│ + Items      │──────►│ UIWidgets  │  │
│  │ (existing)  │        │ (new)       │        │ (new)        │       │ (new)      │  │
│  └─────────────┘        └─────────────┘        └─────────────┘       └───────────┘  │
│        │                       │                      │                     │        │
│        │                       │                      │                     │        │
│  ┌─────────────┐        ┌─────────────┐        ┌─────────────┐       ┌───────────┐  │
│  │ Vector/Graph│        │ agent-host  │        │ agent-host  │       │ agent-host│  │
│  │ integration │        │ Blueprint   │        │ Content     │       │ Delivery  │  │
│  │ (ASAP)      │        │ Architect   │        │ Author      │       │ Agent     │  │
│  └─────────────┘        └─────────────┘        └─────────────┘       └───────────┘  │
│                                                                                      │
│  Week 1-2               Week 2-3               Week 3-4              Week 4-5       │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 0: Infrastructure Foundation (Week 1-2)

### 0.1 Vector/Graph Integration in knowledge-manager

**Goal**: Enable semantic search and graph traversal for terms/rules.

| Task | Priority | Effort | Owner |
|------|----------|--------|-------|
| Wire `Neo4jClient` in `main.py` lifespan | P0 | 2h | Backend |
| Wire `QdrantVectorClient` in `main.py` lifespan | P0 | 2h | Backend |
| Create `EmbeddingProvider` protocol + OpenAI impl | P0 | 4h | Backend |
| Add `POST /api/sync/reindex` endpoint (one-time backfill) | P0 | 4h | Backend |
| Add event handlers for term/relationship sync | P1 | 8h | Backend |
| Add Redis queue for rate-limited event processing | P1 | 4h | Backend |
| Add `GET /api/search/semantic` endpoint | P0 | 4h | Backend |
| Add `GET /api/graph/related` endpoint | P0 | 4h | Backend |

**Deliverable**: API endpoints that:

- Semantic search: "Find terms similar to 'troubleshooting BGP'" → returns ranked term IDs
- Graph query: "Find rules that apply to term 'ExamBlueprint'" → returns rule list

### 0.2 Validation Service in knowledge-manager

**Goal**: Hybrid validation (BusinessRule + agent delegation).

| Task | Priority | Effort | Owner |
|------|----------|--------|-------|
| Create `ValidationService` in `application/services/` | P0 | 4h | Backend |
| Define `ValidationRequest` / `ValidationResult` DTOs | P0 | 2h | Backend |
| Implement term detection (exact + semantic match) | P0 | 4h | Backend |
| Implement BusinessRule evaluation (programmatic) | P0 | 4h | Backend |
| Add `POST /api/validation/evaluate` endpoint | P0 | 2h | Backend |
| Create `validation-agent` AgentDefinition in agent-host | P1 | 4h | Backend |
| Add internal `/api/internal/evaluate` in agent-host | P1 | 8h | Backend |
| Wire LLM-mediated evaluation to agent-host | P1 | 4h | Backend |

**Deliverable**: POST to `/api/validation/evaluate` with a blueprint JSON returns:

- Programmatic violations (if any)
- LLM-mediated evaluations (if interpretive rules apply)

### 0.3 Semantic Groups in knowledge-manager

**Goal**: User-defined groups for efficient context retrieval.

| Task | Priority | Effort | Owner |
|------|----------|--------|-------|
| Add `SemanticGroup` model in `domain/models/` | P1 | 2h | Backend |
| Add groups CRUD commands/queries | P1 | 8h | Backend |
| Add `/api/groups` endpoints | P1 | 4h | Backend |
| Add `/api/namespaces/{ns}/groups` endpoint | P1 | 2h | Backend |
| Seed initial groups for certification-program namespace | P1 | 2h | Backend |

**Deliverable**: API to create/query semantic groups; pre-seeded groups for MVP demo.

---

## Phase 1: Blueprint Authoring (Week 2-3)

### 1.1 Create blueprint-manager Service

**Goal**: New microservice for ExamBlueprint, SkillTemplate, FormSpec aggregates.

| Task | Priority | Effort | Owner |
|------|----------|--------|-------|
| Scaffold `src/blueprint-manager/` using tools-provider pattern | P0 | 4h | Backend |
| Create `ExamBlueprint` aggregate (Topics → Skills → KSAs) | P0 | 8h | Backend |
| Create CRUD commands/queries for ExamBlueprint | P0 | 8h | Backend |
| Add `/api/blueprints` REST endpoints | P0 | 4h | Backend |
| Configure MotorRepository in `main.py` | P0 | 2h | Backend |
| Add CloudEvent publishing for blueprint events | P0 | 4h | Backend |
| Add integration with knowledge-manager (validation) | P1 | 4h | Backend |

**Aggregate Design Summary** (from [01-exam-blueprint-aggregate.md](01-exam-blueprint-aggregate.md)):

```python
class ExamBlueprintState(AggregateState[str]):
    id: str
    title: str
    certification_level: str  # "Associate", "Professional", "Expert"
    track: str                # "Networking", "Security", etc.
    version: str
    status: str               # "draft", "review", "approved", "published"

    # Hierarchical structure
    topics: list[Topic]       # Topic → Skills → KSAs

    # Constraints from knowledge-manager
    target_bloom_distribution: dict[str, float]
    min_ksa_count: int
    max_ksa_count: int

    # Audit
    created_by: str
    created_at: datetime
    updated_at: datetime
    state_version: int
```

### 1.2 Blueprint Architect Agent

**Goal**: AI agent that assists EPMs in blueprint creation.

| Task | Priority | Effort | Owner |
|------|----------|--------|-------|
| Create `blueprint-architect` AgentDefinition | P0 | 4h | Backend |
| Define system prompt with psychometric best practices | P0 | 2h | Domain |
| Register MCP tools for blueprint CRUD | P0 | 4h | Backend |
| Register MCP tools for knowledge-manager queries | P0 | 4h | Backend |
| Test conversation flow: "Help me create a networking cert" | P0 | 4h | QA |

**Agent Configuration**:

```yaml
agent_id: 'blueprint-architect'
name: 'Blueprint Architect'
description: 'Assists EPMs in creating well-structured exam blueprints'

system_prompt: |
  You are an expert psychometrician and instructional designer.

  Your responsibilities:
  1. Help decompose certification goals into Topics → Skills → KSAs
  2. Ensure KSAs follow Bloom's Taxonomy with measurable action verbs
  3. Validate topic weights align with job task analysis
  4. Check blueprint against program rules via validation endpoint

  Key principles:
  - Every KSA must be testable with objective criteria
  - Prefer action verbs: configure, troubleshoot, analyze, design
  - Balance breadth vs depth based on exam time constraints

tools:
  - blueprint.list_blueprints
  - blueprint.get_blueprint
  - blueprint.create_blueprint
  - blueprint.add_topic
  - blueprint.add_skill
  - blueprint.add_ksa
  - blueprint.validate_blueprint
  - knowledge.search_terms
  - knowledge.get_rules
  - knowledge.validate

access_control:
  allowed_roles: ['certification_owner', 'exam_architect']
```

### 1.3 MCP Tools for Blueprint Operations

**Goal**: Tools-provider exposes blueprint operations to agents.

| Task | Priority | Effort | Owner |
|------|----------|--------|-------|
| Add OpenAPI spec discovery for blueprint-manager | P0 | 2h | Backend |
| Register blueprint tools in tools-provider | P0 | 4h | Backend |
| Add `blueprint.validate_blueprint` tool (calls km validation) | P0 | 4h | Backend |
| Test tool invocation from agent-host | P0 | 2h | QA |

---

## Phase 2: Content Authoring (Week 3-4)

### 2.1 SkillTemplate Aggregate

**Goal**: Reusable templates for item development guidance.

| Task | Priority | Effort | Owner |
|------|----------|--------|-------|
| Create `SkillTemplate` aggregate in blueprint-manager | P0 | 8h | Backend |
| Define `UIWidgetSpec` embedded model | P0 | 4h | Backend |
| Create CRUD commands/queries | P0 | 8h | Backend |
| Add `/api/skill-templates` endpoints | P0 | 4h | Backend |
| Link SkillTemplate to ExamBlueprint.skills | P0 | 4h | Backend |

**SkillTemplate Design**:

```python
class SkillTemplateState(AggregateState[str]):
    id: str
    name: str
    description: str

    # What this template measures
    target_ksa_pattern: str  # Regex or semantic description
    cognitive_level: str     # Bloom's level
    skill_type: str          # "knowledge", "skill", "ability"

    # Item generation guidance
    stem_patterns: list[StemPattern]
    distractor_strategies: list[str]
    parameter_definitions: list[ParameterDef]

    # UI rendering specification
    ui_widget_spec: UIWidgetSpec

    # Scoring
    scoring_rubric: ScoringRubric
    partial_credit: bool

    # Metadata
    linked_skill_ids: list[str]  # Skills this template serves
    created_by: str
    state_version: int


@dataclass
class UIWidgetSpec:
    """Specification for rendering in agent-host Conversation."""

    widget_type: str  # "mcq", "scenario", "log_analysis", "topology", "config_task"

    layout: dict
    """Widget-specific layout configuration."""

    input_schema: dict
    """JSON Schema for candidate response."""

    resources: list[ResourceSpec]
    """Attached resources (diagrams, logs, configs)."""

    validation_rules: list[str]
    """Client-side validation (required fields, format)."""
```

### 2.2 Content Author Assistant Agent

**Goal**: AI agent that helps SMEs write items using SkillTemplates.

| Task | Priority | Effort | Owner |
|------|----------|--------|-------|
| Create `content-author-assistant` AgentDefinition | P0 | 4h | Backend |
| Define system prompt with item-writing best practices | P0 | 2h | Domain |
| Register MCP tools for SkillTemplate queries | P0 | 4h | Backend |
| Register MCP tools for item generation helpers | P0 | 4h | Backend |
| Test conversation flow: "Help me create items for BGP skill" | P0 | 4h | QA |

### 2.3 Item Generation MCP Tools

**Goal**: Tools that help generate item components.

| Tool | Purpose | Input | Output |
|------|---------|-------|--------|
| `generate.stem_variants` | Create stem variations | Base stem + parameters | List of parameterized stems |
| `generate.distractors` | Generate plausible wrong options | Correct answer + context | Distractor set with strategies |
| `generate.exhibit` | Generate diagram/topology | Scenario description | SVG or Mermaid diagram |
| `validate.item_quality` | Check item against rubric | Complete item | Quality report |
| `validate.bloom_level` | Detect cognitive level | Item stem | Bloom's classification |

---

## Phase 3: Exam Delivery (Week 4-5)

### 3.1 ConversationTemplate for SkillTemplate Delivery

**Goal**: Map SkillTemplate.UIWidgetSpec to Conversation widgets.

| Task | Priority | Effort | Owner |
|------|----------|--------|-------|
| Extend ConversationTemplate to support widget definitions | P0 | 8h | Backend |
| Create widget renderer registry in agent-host UI | P0 | 8h | Frontend |
| Implement MCQ widget | P0 | 4h | Frontend |
| Implement Scenario widget (with progressive resources) | P0 | 8h | Frontend |
| Implement LogViewer widget | P1 | 4h | Frontend |
| Implement TopologyViewer widget | P1 | 8h | Frontend |

### 3.2 Delivery Agent

**Goal**: Agent that orchestrates exam item presentation.

| Task | Priority | Effort | Owner |
|------|----------|--------|-------|
| Create `exam-delivery-agent` AgentDefinition | P0 | 4h | Backend |
| Define proactive conversation flow (Design module) | P0 | 8h | Backend |
| Implement widget rendering messages | P0 | 4h | Backend |
| Implement response collection and scoring | P0 | 8h | Backend |
| Test end-to-end: Template → Conversation → Response | P0 | 8h | QA |

### 3.3 Design Module Flow (Proactive Conversation)

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                    DESIGN MODULE - SKILLTEMPLATE → CONVERSATION                      │
│                                                                                      │
│  1. Session Start                                                                   │
│     ├── Load FormSpec (which SkillTemplates in what order)                          │
│     ├── Instantiate ConversationTemplate with widget sequence                       │
│     └── Start Conversation with Delivery Agent                                      │
│                                                                                      │
│  2. Item Presentation (for each SkillTemplate)                                      │
│     ├── Agent sends NarrativeBlock (scenario context)                               │
│     ├── Agent sends ResourceCard (email, diagram, log)                              │
│     ├── Agent sends UIWidget (MCQ, TextInput, etc.)                                 │
│     └── Candidate submits response via widget                                       │
│                                                                                      │
│  3. Response Handling                                                               │
│     ├── Validate response against UIWidgetSpec.input_schema                         │
│     ├── Record response to Conversation                                             │
│     ├── (Optional) Immediate scoring for non-practical items                        │
│     └── Advance to next SkillTemplate                                               │
│                                                                                      │
│  4. Completion                                                                      │
│     ├── All items presented                                                         │
│     ├── Publish conversation.completed.v1 event                                     │
│     └── Trigger scoring workflow (sync or async)                                    │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 4: Integration & Demo (Week 5-6)

### 4.1 End-to-End Demo Flow

1. **EPM creates blueprint** via Blueprint Architect agent
   - Defines Topics → Skills → KSAs
   - Validates against program rules
   - Approves blueprint

2. **SME creates SkillTemplates** via Content Author agent
   - Links to Skills in blueprint
   - Defines UI widget spec
   - Generates sample items

3. **Candidate takes exam** via Delivery agent
   - Experiences SkillTemplate as UI widgets
   - Submits responses
   - Receives completion confirmation

### 4.2 Success Criteria

| Criterion | Metric | Target |
|-----------|--------|--------|
| **Blueprint creation time** | Minutes from start to validated blueprint | < 30 min |
| **SkillTemplate usability** | SME can create template without code | 100% |
| **Widget rendering** | All UIWidgetSpec types render correctly | 100% |
| **Response capture** | All candidate responses persisted | 100% |
| **Conversation coherence** | Agent maintains context throughout exam | Subjective QA |

---

## Technical Debt & Known Gaps

| Gap | Impact | Mitigation |
|-----|--------|------------|
| No Mosaic integration yet | Can't sync to production | Mock APIs in MVP |
| LLM-mediated validation deferred | Only programmatic rules in P0 | Phase 1 adds agent delegation |
| Auto-generated semantic groups | Manual curation only | Defer to post-MVP |
| User profile | No personalization | Keycloak claims sufficient for MVP |
| Offline/resilience | No PWA or offline mode | Network-connected only |

---

## Appendix: File/Folder Structure

### blueprint-manager (new service)

```
src/blueprint-manager/
├── __init__.py
├── main.py
├── pyproject.toml
├── pytest.ini
├── Makefile
├── api/
│   ├── __init__.py
│   ├── dependencies.py
│   └── controllers/
│       ├── blueprints_controller.py
│       ├── skill_templates_controller.py
│       └── form_specs_controller.py
├── application/
│   ├── __init__.py
│   ├── settings.py
│   ├── commands/
│   │   ├── create_blueprint_command.py
│   │   ├── add_topic_command.py
│   │   ├── add_skill_command.py
│   │   ├── add_ksa_command.py
│   │   ├── create_skill_template_command.py
│   │   └── ...
│   └── queries/
│       ├── get_blueprint_query.py
│       ├── get_skill_template_query.py
│       └── ...
├── domain/
│   ├── __init__.py
│   ├── entities/
│   │   ├── exam_blueprint.py
│   │   ├── skill_template.py
│   │   └── form_spec.py
│   ├── events/
│   │   ├── exam_blueprint.py
│   │   └── skill_template.py
│   └── models/
│       ├── topic.py
│       ├── skill.py
│       ├── ksa.py
│       ├── ui_widget_spec.py
│       └── parameter_def.py
└── integration/
    └── models/
        ├── blueprint_dto.py
        └── skill_template_dto.py
```

---

## Next Steps

1. **Immediate**: Start Phase 0.1 (Vector/Graph integration)
2. **This week**: Scaffold blueprint-manager service
3. **Review checkpoint**: End of Week 2 — demo semantic search + blueprint creation

---

_This roadmap will be updated as implementation progresses. Estimates are approximate and should be refined during sprint planning._

_Last updated: December 2025_
