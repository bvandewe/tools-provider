# Implementation Plan: ConversationTemplate Full-Stack Implementation

!!! info "Reference Document"
    **Status:** `IMPLEMENTED` - December 2025

    This implementation plan was executed and the ConversationTemplate feature is now part of the codebase.
    
    **Implementation Status:**
    
    | Feature | Status |
    |---------|--------|
    | Domain models | ✅ Implemented |
    | Admin API | ✅ Implemented |
    | Admin UI | ⚠️ Partial |
    | YAML seeding | ⚠️ Planned |
    | YAML export | ⚠️ Planned |
    
    **Current Documentation:**
    
    - [Agent Host Architecture](../architecture/agent-host-architecture.md)
    - [Conversation Flows](../architecture/conversation-flows.md)

---

**Version:** 1.0.0  
**Status:** `IMPLEMENTED`  
**Date:** December 16, 2025  
**Author:** GitHub Copilot (Principal Engineer Mode)

---

## 1. Executive Summary

This document defined the implementation plan for the full-stack `ConversationTemplate` feature in the agent-host application, including:

- Domain model restructuring (AgentDefinition → ConversationTemplate → ConversationItem → ItemContent)
- Database seeding from YAML files
- Admin UI for CRUD operations
- YAML export functionality
- Keycloak role updates

### Key Design Decisions (Implemented)

| Decision | Choice |
|----------|--------|
| `agent_starts_first` location | **Removed from AgentDefinition**, moved to `ConversationTemplate` |
| Agents without templates | Always **reactive** (user speaks first) |
| Proactive agents | **Require** a `ConversationTemplate` (even minimal) |
| Template subclassing | **No subclasses** - single `ConversationTemplate` handles all use cases |
| Hierarchy | `AgentDefinition` → `ConversationTemplate` → `ConversationItem[]` → `ItemContent[]` |
| Skills loading | YAML files scanned at startup, indexed by `skill_id` in memory |
| Seed strategy | **Seed-only** - create if not present, manual updates for changes |
| Export format | YAML (seed-compatible) |
| Keycloak role | `candidate` as **realm role** |

---

## 2. Data Model Hierarchy

```
AgentDefinition (MongoDB)
├── id, name, system_prompt, tools, icon, ...
├── conversation_template_id ────────────────┐
└── (NO agent_starts_first - removed)        │
                                             │
                                             ▼
ConversationTemplate (MongoDB)
├── id, name, description
├── agent_starts_first (moved here)
├── Flow: allow_navigation, allow_backward_navigation, ...
├── Display: shuffle_items, display_progress_indicator, ...
├── Timing: min/max_duration_seconds
├── Scoring: passing_score_percent
└── items: ConversationItem[]
              │
              ▼
    ConversationItem
    ├── id, order, title
    ├── Interaction: enable_chat_input, provide_feedback, ...
    ├── Timing: time_limit_seconds
    └── contents: ItemContent[]
                    │
                    ▼
        ItemContent
        ├── id, order
        ├── is_templated: bool
        ├── source_id: str (skill_id if templated)
        ├── widget_type: str
        ├── widget_config: dict
        ├── Static content: stem, options, correct_answer
        └── Scoring: max_score, skippable, required
```

---

## 3. Detailed Schema Definitions

### 3.1 AgentDefinition (Updated)

**File:** `src/agent-host/domain/models/agent_definition.py`

**Remove:**

- `agent_starts_first: bool` field
- `is_proactive` property
- `is_reactive` property

**Keep:**

- All other fields unchanged
- `conversation_template_id: str | None` (reference to template)

### 3.2 ConversationTemplate (Rewritten)

**File:** `src/agent-host/domain/models/conversation_template.py`

```python
@dataclass
class ConversationTemplate:
    """Template defining conversation structure and flow."""
    
    # Identity
    id: str
    name: str
    description: str | None = None
    
    # Flow Configuration
    agent_starts_first: bool = False
    allow_agent_switching: bool = False
    allow_navigation: bool = False
    allow_backward_navigation: bool = False
    enable_chat_input_initially: bool = True
    
    # Timing
    min_duration_seconds: int | None = None
    max_duration_seconds: int | None = None
    
    # Display Options
    shuffle_items: bool = False
    display_progress_indicator: bool = True
    display_item_score: bool = False
    display_item_title: bool = True
    display_final_score_report: bool = False
    include_feedback: bool = True
    append_items_to_view: bool = True  # False = hide previous items
    
    # Messages
    introduction_message: str | None = None
    completion_message: str | None = None
    
    # Content
    items: list[ConversationItem] = field(default_factory=list)
    
    # Scoring (for assessments)
    passing_score_percent: float | None = None
    
    # Audit
    created_by: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    version: int = 1
```

### 3.3 ConversationItem (New)

**File:** `src/agent-host/domain/models/conversation_item.py`

```python
@dataclass
class ConversationItem:
    """A UX step in the conversation flow."""
    
    # Identity
    id: str
    order: int
    title: str | None = None
    
    # Interaction Configuration
    enable_chat_input: bool = True
    show_expiration_warning: bool = False
    expiration_warning_seconds: int | None = None
    warning_message: str | None = None
    provide_feedback: bool = True
    reveal_correct_answer: bool = False
    
    # Timing
    time_limit_seconds: int | None = None
    
    # Content (rendered top-to-bottom)
    contents: list[ItemContent] = field(default_factory=list)
```

### 3.4 ItemContent (New)

**File:** `src/agent-host/domain/models/item_content.py`

```python
@dataclass
class ItemContent:
    """Content within a ConversationItem."""
    
    # Identity
    id: str
    order: int
    
    # Source
    is_templated: bool = False
    source_id: str | None = None  # Skill ID if templated
    
    # Widget Configuration
    widget_type: str = "message"  # message, multiple_choice, free_text, slider, code_editor
    widget_config: dict[str, Any] = field(default_factory=dict)
    
    # Interaction
    skippable: bool = False
    required: bool = True
    
    # Scoring
    max_score: float = 1.0
    
    # Static Content (if not templated)
    stem: str | None = None
    options: list[str] | None = None
    correct_answer: str | None = None  # Never sent to client
    explanation: str | None = None
    
    # Initial State
    initial_value: Any = None
```

---

## 4. File Inventory

### 4.1 Files to CREATE

| # | Path | Description |
|---|------|-------------|
| 1 | `domain/models/conversation_item.py` | ConversationItem dataclass |
| 2 | `domain/models/item_content.py` | ItemContent dataclass |
| 3 | `domain/repositories/template_repository.py` | Abstract repository interface |
| 4 | `integration/repositories/motor_template_repository.py` | MongoDB implementation |
| 5 | `integration/models/template_dto.py` | DTO for read model |
| 6 | `application/commands/create_template_command.py` | Create template command + handler |
| 7 | `application/commands/update_template_command.py` | Update template command + handler |
| 8 | `application/commands/delete_template_command.py` | Delete template command + handler |
| 9 | `application/queries/get_templates_query.py` | Get/List templates queries + handlers |
| 10 | `infrastructure/skill_loader.py` | YAML skill file scanner/indexer |
| 11 | `infrastructure/database_seeder.py` | Unified seeder for definitions + templates |
| 12 | `infrastructure/yaml_exporter.py` | Export to seed-compatible YAML |
| 13 | `api/controllers/admin_templates_controller.py` | CRUD endpoints for templates |
| 14 | `ui/src/scripts/admin/templates-manager.js` | Frontend template manager |
| 15 | `ui/src/templates/partials/admin/_templates.jinja` | Templates list page |
| 16 | `ui/src/templates/partials/admin/_template_modal.jinja` | Create/edit modal |
| 17 | `data/agents/default-chat.yaml` | Default reactive agent seed |
| 18 | `data/agents/proactive-validator.yaml` | Assessment agent seed |
| 19 | `data/templates/math-assessment.yaml` | Sample assessment template |

### 4.2 Files to MODIFY

| # | Path | Changes |
|---|------|---------|
| 1 | `domain/models/agent_definition.py` | Remove `agent_starts_first`, update defaults |
| 2 | `domain/models/conversation_template.py` | Complete rewrite with new schema |
| 3 | `domain/models/__init__.py` | Export new models |
| 4 | `domain/repositories/__init__.py` | Export TemplateRepository |
| 5 | `integration/repositories/__init__.py` | Export MotorTemplateRepository |
| 6 | `integration/models/__init__.py` | Export TemplateDto |
| 7 | `integration/models/definition_dto.py` | Remove `agent_starts_first` / `is_proactive` |
| 8 | `application/commands/create_definition_command.py` | Remove `agent_starts_first` |
| 9 | `application/commands/update_definition_command.py` | Remove `agent_starts_first` |
| 10 | `application/queries/get_definitions_query.py` | Remove `is_proactive` mapping |
| 11 | `api/controllers/admin_definitions_controller.py` | Add export endpoint, remove `agent_starts_first` |
| 12 | `ui/src/templates/admin.jinja` | Include template partials, remove "Coming Soon" |
| 13 | `ui/src/scripts/admin/main.js` | Initialize TemplatesManager |
| 14 | `main.py` | Register new services/repositories |
| 15 | `deployment/keycloak/realm-export.json` | Add `candidate` realm role |
| 16 | `infrastructure/definition_store_initializer.py` | Replace with DatabaseSeeder |

---

## 5. YAML Seed File Specifications

### 5.1 Agent Definition: `data/agents/default-chat.yaml`

```yaml
id: "default-chat"
name: "Chat Assistant"
description: "A helpful AI assistant for general conversations"
icon: "bi-chat-dots"
system_prompt: |
  You are a helpful AI assistant. Be concise but thorough in your responses.
  Help users with their questions and tasks.
tools: []
conversation_template_id: null
is_public: true
required_roles: []
required_scopes: []
allowed_users: null
```

### 5.2 Agent Definition: `data/agents/proactive-validator.yaml`

```yaml
id: "proactive-validator"
name: "Knowledge Validator"
description: "Assess knowledge through adaptive questioning"
icon: "bi-patch-check"
system_prompt: |
  You are a knowledge assessment agent. Your role is to:
  1. Present questions from the configured assessment template
  2. For templated items, generate contextually appropriate questions using the skill templates
  3. Evaluate user responses and provide constructive feedback
  4. Track progress through the assessment items
  5. Maintain an encouraging but professional tone
  
  When generating items from skill templates:
  - Follow the difficulty constraints specified
  - Use the stem templates as guidance
  - Generate plausible distractors using the specified strategies
  - Never reveal correct answers before the user responds
tools: []
conversation_template_id: "math-assessment"
is_public: true
required_roles:
  - "candidate"
required_scopes: []
allowed_users: null
```

### 5.3 Conversation Template: `data/templates/math-assessment.yaml`

```yaml
id: "math-assessment"
name: "Mathematics Fundamentals Assessment"
description: "Entry-level arithmetic skills evaluation"

# Flow Configuration
agent_starts_first: true
allow_agent_switching: false
allow_navigation: false
allow_backward_navigation: false
enable_chat_input_initially: false

# Timing
min_duration_seconds: null
max_duration_seconds: 900  # 15 minutes

# Display Options
shuffle_items: true
display_progress_indicator: true
display_item_score: false
display_item_title: true
display_final_score_report: true
include_feedback: true
append_items_to_view: true

# Messages
introduction_message: |
  Welcome to the Mathematics Fundamentals Assessment!
  
  You will answer 3 questions covering basic arithmetic.
  Take your time and do your best. Good luck!

completion_message: |
  You have completed the assessment. Thank you for your participation!

# Scoring
passing_score_percent: 70.0

# Items
items:
  - id: "q1"
    order: 1
    title: "Addition"
    enable_chat_input: false
    show_expiration_warning: true
    expiration_warning_seconds: 10
    warning_message: "10 seconds remaining!"
    provide_feedback: true
    reveal_correct_answer: true
    time_limit_seconds: 60
    contents:
      - id: "q1-mc"
        order: 1
        is_templated: true
        source_id: "MATH.ARITH.ADD.2DIGIT"
        widget_type: "multiple_choice"
        widget_config:
          shuffle_options: true
        skippable: false
        required: true
        max_score: 1.0

  - id: "q2"
    order: 2
    title: "Subtraction"
    enable_chat_input: false
    show_expiration_warning: true
    expiration_warning_seconds: 10
    provide_feedback: true
    reveal_correct_answer: true
    time_limit_seconds: 60
    contents:
      - id: "q2-mc"
        order: 1
        is_templated: true
        source_id: "MATH.ARITH.SUB.2DIGIT"
        widget_type: "multiple_choice"
        widget_config:
          shuffle_options: true
        skippable: false
        required: true
        max_score: 1.0

  - id: "q3"
    order: 3
    title: "Multiplication"
    enable_chat_input: false
    show_expiration_warning: true
    expiration_warning_seconds: 10
    provide_feedback: true
    reveal_correct_answer: true
    time_limit_seconds: 60
    contents:
      - id: "q3-mc"
        order: 1
        is_templated: true
        source_id: "MATH.ARITH.MUL.SINGLE"
        widget_type: "multiple_choice"
        widget_config:
          shuffle_options: true
        skippable: false
        required: true
        max_score: 1.0
```

---

## 6. Implementation Phases

### Phase 1: Domain Models (Foundation)

**Priority:** CRITICAL  
**Estimated Files:** 4 modified, 2 created

1. Create `domain/models/item_content.py`
2. Create `domain/models/conversation_item.py`
3. Rewrite `domain/models/conversation_template.py`
4. Update `domain/models/agent_definition.py` (remove `agent_starts_first`)
5. Update `domain/models/__init__.py`

### Phase 2: Repository Layer

**Priority:** HIGH  
**Estimated Files:** 2 modified, 2 created

1. Create `domain/repositories/template_repository.py`
2. Create `integration/repositories/motor_template_repository.py`
3. Update `domain/repositories/__init__.py`
4. Update `integration/repositories/__init__.py`

### Phase 3: Integration Models (DTOs)

**Priority:** HIGH  
**Estimated Files:** 2 modified, 1 created

1. Create `integration/models/template_dto.py`
2. Update `integration/models/definition_dto.py`
3. Update `integration/models/__init__.py`

### Phase 4: Infrastructure Services

**Priority:** HIGH  
**Estimated Files:** 1 modified, 3 created

1. Create `infrastructure/skill_loader.py`
2. Create `infrastructure/database_seeder.py`
3. Create `infrastructure/yaml_exporter.py`
4. Delete/deprecate `infrastructure/definition_store_initializer.py`

### Phase 5: CQRS Commands & Queries

**Priority:** HIGH  
**Estimated Files:** 4 modified, 4 created

1. Create `application/commands/create_template_command.py`
2. Create `application/commands/update_template_command.py`
3. Create `application/commands/delete_template_command.py`
4. Create `application/queries/get_templates_query.py`
5. Update `application/commands/create_definition_command.py`
6. Update `application/commands/update_definition_command.py`
7. Update `application/queries/get_definitions_query.py`
8. Update `application/commands/__init__.py`
9. Update `application/queries/__init__.py`

### Phase 6: API Controllers

**Priority:** MEDIUM  
**Estimated Files:** 1 modified, 1 created

1. Create `api/controllers/admin_templates_controller.py`
2. Update `api/controllers/admin_definitions_controller.py` (add export, remove agent_starts_first)
3. Update `api/controllers/__init__.py`

### Phase 7: YAML Seed Data

**Priority:** MEDIUM  
**Estimated Files:** 3 created

1. Create `data/agents/default-chat.yaml`
2. Create `data/agents/proactive-validator.yaml`
3. Create `data/templates/math-assessment.yaml`

### Phase 8: Admin UI Frontend

**Priority:** MEDIUM  
**Estimated Files:** 2 modified, 3 created

1. Create `ui/src/scripts/admin/templates-manager.js`
2. Create `ui/src/templates/partials/admin/_templates.jinja`
3. Create `ui/src/templates/partials/admin/_template_modal.jinja`
4. Update `ui/src/templates/admin.jinja`
5. Update `ui/src/scripts/admin/main.js`

### Phase 9: Application Wiring

**Priority:** HIGH  
**Estimated Files:** 1 modified

1. Update `main.py`:
   - Register `TemplateRepository` → `MotorTemplateRepository`
   - Configure `DatabaseSeeder` (replaces DefinitionRepositoryInitializer)
   - Configure `SkillLoader`
   - Configure `YamlExporter`

### Phase 10: Keycloak

**Priority:** LOW  
**Estimated Files:** 1 modified

1. Update `deployment/keycloak/realm-export.json`:
   - Add `candidate` to realm roles

---

## 7. API Endpoints

### 7.1 Admin Templates API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/admin/templates` | List all templates |
| GET | `/admin/templates/{id}` | Get template by ID |
| POST | `/admin/templates` | Create template |
| PUT | `/admin/templates/{id}` | Update template |
| DELETE | `/admin/templates/{id}` | Delete template |
| GET | `/admin/templates/{id}/export` | Export as YAML |

### 7.2 Admin Definitions API (Updated)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/admin/definitions/{id}/export` | Export as YAML (NEW) |

---

## 8. Testing Strategy

### Unit Tests

- Domain model serialization (`to_dict` / `from_dict`)
- SkillLoader file scanning and indexing
- YamlExporter output format

### Integration Tests

- Repository CRUD operations
- CQRS command/query handlers
- API endpoint responses

### E2E Tests

- Admin UI template CRUD workflow
- Template export/import cycle

---

## 9. Migration Notes

- **No data migration required** - this is additive
- Existing AgentDefinitions with `agent_starts_first=True` will need manual update to reference a template
- Default agents seeded from YAML will replace hardcoded Python objects

---

## 10. Reference Files

### Existing Patterns to Follow

| Pattern | Reference File |
|---------|----------------|
| Domain model | `domain/models/agent_definition.py` |
| Repository interface | `domain/repositories/definition_repository.py` |
| Motor repository | `integration/repositories/motor_definition_repository.py` |
| DTO | `integration/models/definition_dto.py` |
| Command handler | `application/commands/create_definition_command.py` |
| Query handler | `application/queries/get_definitions_query.py` |
| Admin controller | `api/controllers/admin_definitions_controller.py` |
| JS manager | `ui/src/scripts/admin/definitions-manager.js` |
| Jinja partial | `ui/src/templates/partials/admin/_definitions.jinja` |
| Hosted service | `infrastructure/definition_store_initializer.py` |

---

## 11. Checklist

- [ ] Phase 1: Domain Models
- [ ] Phase 2: Repository Layer  
- [ ] Phase 3: Integration Models (DTOs)
- [ ] Phase 4: Infrastructure Services
- [ ] Phase 5: CQRS Commands & Queries
- [ ] Phase 6: API Controllers
- [ ] Phase 7: YAML Seed Data
- [ ] Phase 8: Admin UI Frontend
- [ ] Phase 9: Application Wiring (`main.py`)
- [ ] Phase 10: Keycloak Role
- [ ] Run tests
- [ ] Manual verification

---

_Document ready for implementation. Proceed phase by phase in a new conversation session._
