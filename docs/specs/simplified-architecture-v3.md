# Simplified Agent-Host Architecture

!!! info "Reference Document"
    **Status:** `IMPLEMENTED` - December 2025

    This specification (v3.0.0) describes the **implemented architecture**. It serves as a historical design document.

    **Current Documentation:**

    - [Agent Host Architecture](../architecture/agent-host-architecture.md) - Detailed current architecture
    - [Conversation Flows](../architecture/conversation-flows.md) - Flow diagrams and implementation details
    - [Implementation Guide](../development/agent-host-implementation-guide.md) - Developer walkthrough

---

**Version:** 3.0.0
**Status:** `IMPLEMENTED`
**Date:** December 16, 2025

---

## 1. Executive Summary

This document defined a **drastically simplified architecture** for agent-host:

- **One AggregateRoot**: `Conversation` (not Agent, not Session)
- **AgentDefinition**: State-based entity (MongoDB) for behavior templates
- **Stateless Agent Service**: Executes conversations using definitions
- **LLM-Generated Items**: Skill templates drive dynamic content generation

### Key Simplifications (Implemented)

| Old (Complex) | New (Simple) |
|---------------|--------------|
| Agent as AggregateRoot with nested Session | Conversation as AggregateRoot |
| Session as separate AggregateRoot (legacy) | Removed entirely |
| 6+ SessionTypes | AgentDefinition with `agent_starts_first` flag |
| Separate ExecutionState | Implicit in Conversation state |
| Stateful Agent entity | Stateless AgentService |

---

## 2. Core Entities

### 2.1 Entity Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     ENTITY RELATIONSHIPS                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  AgentDefinition (MongoDB)         Conversation (EventStoreDB)  │
│  ────────────────────────         ───────────────────────────   │
│  │                                │                              │
│  │ id: "evaluator"                │ id: UUID                    │
│  │ name: "Knowledge Evaluator"    │ owner_user_id               │
│  │ agent_starts_first: true       │ definition_id ─────────────┼──┐
│  │ system_prompt: "..."           │                              │  │
│  │ conversation_template: ────────┼─► template_progress         │  │
│  │   └── item_templates[]         │     └── current_index       │  │
│  │                                │ messages[]                   │  │
│  │ access_control:                │ pending_action              │  │
│  │   └── required_roles[]         │ shared_with[]               │  │
│  │                                │ status                       │  │
│  └────────────────────────────────┘                              │  │
│           ▲                                                      │  │
│           │                                                      │  │
│           └──────────────────────────────────────────────────────┘  │
│                         references                                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Conversation (AggregateRoot)

The **only aggregate root**. Represents a complete interaction between user and agent.

```python
class ConversationStatus(str, Enum):
    """Lifecycle status of a conversation."""
    PENDING = "pending"              # Created but not started
    ACTIVE = "active"                # In progress
    AWAITING_USER = "awaiting_user"  # Waiting for text input
    AWAITING_WIDGET = "awaiting_widget"  # Waiting for widget response
    PAUSED = "paused"                # User paused
    COMPLETED = "completed"          # Successfully finished
    TERMINATED = "terminated"        # Ended early by user
    ARCHIVED = "archived"            # Soft-deleted


class ConversationState(AggregateState[str]):
    """Persisted state for Conversation aggregate."""

    # Identity
    id: str
    owner_user_id: str
    definition_id: str               # References AgentDefinition
    title: str | None                # User-editable title

    # Status
    status: str                      # ConversationStatus value

    # Content
    messages: list[dict]             # LlmMessage[] as dicts
    pending_action: dict | None      # ClientAction awaiting response

    # Template progress (for proactive conversations)
    template_progress: dict | None   # { current_index, items_generated[] }

    # Sharing
    shared_with: list[dict]          # [{ user_id, role, shared_at, shared_by }]

    # Timestamps
    created_at: datetime
    started_at: datetime | None
    paused_at: datetime | None
    completed_at: datetime | None
    archived_at: datetime | None


class Conversation(AggregateRoot[ConversationState, str]):
    """Conversation aggregate - the single aggregate root.

    Domain Events:
    - ConversationCreatedDomainEvent
    - ConversationStartedDomainEvent
    - MessageAddedDomainEvent
    - ClientActionRequestedDomainEvent
    - ClientResponseReceivedDomainEvent
    - TemplateItemGeneratedDomainEvent  # For assessment grading
    - ConversationPausedDomainEvent
    - ConversationResumedDomainEvent
    - ConversationCompletedDomainEvent
    - ConversationTerminatedDomainEvent
    - ConversationArchivedDomainEvent
    - ConversationSharedDomainEvent
    - ConversationShareRevokedDomainEvent
    - ConversationRenamedDomainEvent
    """

    # Factory
    @classmethod
    def create(
        cls,
        owner_user_id: str,
        definition_id: str,
        title: str | None = None
    ) -> "Conversation": ...

    # Lifecycle
    def start(self) -> None: ...
    def pause(self) -> None: ...
    def resume(self) -> None: ...
    def complete(self) -> None: ...
    def terminate(self, reason: str) -> None: ...
    def archive(self) -> None: ...

    # Messages
    def add_message(self, message: LlmMessage) -> None: ...
    def request_user_action(self, action: ClientAction) -> None: ...
    def receive_user_response(self, response: ClientResponse) -> None: ...

    # Template progress (for proactive/assessment)
    def record_generated_item(self, item: GeneratedItem) -> None: ...
    def advance_template(self) -> None: ...

    # Sharing
    def share_with(self, user_id: str, role: str, shared_by: str) -> None: ...
    def revoke_share(self, user_id: str) -> None: ...

    # Metadata
    def rename(self, title: str) -> None: ...
```

### 2.3 AgentDefinition (State-Based Entity)

**Not an aggregate**. Configuration entity stored in MongoDB. Defines agent behavior.

```python
@dataclass
class AgentDefinition:
    """Template that defines agent behavior.

    Created by admins (or users for personal definitions).
    Referenced by Conversations via definition_id.
    """

    # Identity
    id: str                          # Slug (e.g., "evaluator") or UUID
    owner_user_id: str | None        # None = system-defined

    # Display
    name: str                        # "Knowledge Evaluator"
    description: str                 # "Assess knowledge through..."
    icon: str | None                 # Bootstrap icon class

    # Behavior
    system_prompt: str               # LLM system prompt
    agent_starts_first: bool         # True = proactive, False = reactive
    tools: list[str]                 # Available MCP tool IDs

    # Conversation Template (optional - for proactive agents)
    conversation_template: ConversationTemplate | None

    # Access Control
    is_public: bool                  # Available to all authenticated users
    required_roles: list[str]        # JWT roles (e.g., ["student"])
    required_scopes: list[str]       # OAuth scopes
    allowed_users: list[str] | None  # Explicit allow list (None = use roles)

    # Audit
    created_by: str
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict: ...

    @classmethod
    def from_dict(cls, data: dict) -> "AgentDefinition": ...
```

### 2.4 ConversationTemplate (Value Object)

For proactive agents, defines the **structure** of the conversation.

```python
@dataclass
class ConversationTemplate:
    """Template defining conversation structure for proactive agents.

    Contains ItemTemplates that the LLM uses to generate actual content.
    """

    id: str
    name: str
    description: str | None

    # Sequence of items to present
    item_templates: list[ItemTemplate]

    # Completion criteria
    completion_message: str | None   # Message shown on completion

    def to_dict(self) -> dict: ...

    @classmethod
    def from_dict(cls, data: dict) -> "ConversationTemplate": ...


@dataclass
class ItemTemplate:
    """Template for a single item in a proactive conversation.

    The LLM uses the skill_template to generate actual content at runtime.
    Generated content is persisted in the conversation for grading.
    """

    id: str
    order: int                       # Position in sequence

    # Content generation
    skill_template_id: str           # Reference to SkillTemplate
    generation_prompt: str | None    # Additional prompt for LLM

    # UI presentation
    widget_type: str                 # "multiple_choice", "free_text", "code_editor", etc.
    widget_config: dict | None       # Widget-specific configuration

    # Constraints
    time_limit_seconds: int | None   # Per-item time limit
    required: bool                   # Must be answered

    def to_dict(self) -> dict: ...

    @classmethod
    def from_dict(cls, data: dict) -> "ItemTemplate": ...


@dataclass
class SkillTemplate:
    """Skill definition used by LLM to generate assessment items.

    Stored separately and referenced by ItemTemplate.skill_template_id.
    """

    id: str
    name: str                        # "Two-digit Addition"
    domain: str                      # "mathematics"
    subdomain: str | None            # "arithmetic"

    # Generation parameters
    difficulty_range: tuple[int, int]  # (1, 5)
    prompt_template: str             # Template for LLM to generate item
    answer_format: str               # "single_choice", "numeric", "text"

    # Evaluation
    evaluation_criteria: dict | None # Rubric for grading

    def to_dict(self) -> dict: ...

    @classmethod
    def from_dict(cls, data: dict) -> "SkillTemplate": ...
```

### 2.5 GeneratedItem (Value Object)

When LLM generates content from a skill template, it's persisted for grading.

```python
@dataclass
class GeneratedItem:
    """An item generated by LLM from a skill template.

    Persisted in the conversation for:
    - Audit trail (what was presented)
    - Grading (comparing user response to correct answer)
    - Analytics (item difficulty calibration)
    """

    id: str
    item_template_id: str            # Which template was used
    skill_template_id: str           # Which skill was assessed

    # Generated content
    stem: str                        # The question text
    options: list[str] | None        # For multiple choice
    correct_answer: str              # For grading (NOT sent to browser)
    explanation: str | None          # For learning feedback

    # User response
    user_response: str | None        # What user answered
    is_correct: bool | None          # Grading result
    response_time_ms: int | None     # How long user took

    # Metadata
    generated_at: datetime
    answered_at: datetime | None

    def to_dict(self) -> dict: ...

    @classmethod
    def from_dict(cls, data: dict) -> "GeneratedItem": ...
```

---

## 3. Stateless Agent Service

The "agent" is **not a domain entity** - it's a stateless application service.

```python
class AgentService:
    """Stateless service that executes conversations.

    Loads Conversation + AgentDefinition, runs LLM loop, yields events.
    All state is persisted in the Conversation aggregate.
    """

    def __init__(
        self,
        llm_provider: LlmProvider,
        tool_registry: ToolRegistry,
        skill_template_store: SkillTemplateStore,
    ): ...

    async def run(
        self,
        conversation: Conversation,
        definition: AgentDefinition,
    ) -> AsyncIterator[AgentEvent]:
        """Execute the agent loop for a conversation.

        Flow:
        1. Build LLM context from conversation.messages
        2. If template exists and not complete:
           a. Get next ItemTemplate
           b. Load SkillTemplate
           c. Generate item content via LLM
           d. Yield TemplateItemGenerated event
           e. Present widget, yield ClientAction event
           f. Suspend, wait for response
        3. Else (reactive or template complete):
           a. Call LLM with context
           b. Handle tool calls
           c. Yield content/widget events
        4. Update conversation state
        5. Return when suspended or complete
        """
        ...

    async def handle_response(
        self,
        conversation: Conversation,
        definition: AgentDefinition,
        response: ClientResponse,
    ) -> AsyncIterator[AgentEvent]:
        """Handle user's response and continue.

        1. Record response in conversation
        2. If proactive: grade response, record result
        3. Continue run() loop
        """
        ...
```

---

## 4. UI Flow

### 4.1 Available Agents (Home Page)

Users see tiles for AgentDefinitions they have access to:

```
┌─────────────────────────────────────────────────────────────────┐
│                      WELCOME, USER                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Select an Agent to start:                                      │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │    Chat     │  │  Evaluator  │  │   Survey    │             │
│  │     💬      │  │     📝      │  │     📋      │             │
│  │             │  │             │  │             │             │
│  │  General    │  │  Knowledge  │  │  Feedback   │             │
│  │  assistant  │  │  assessment │  │  collection │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Agent Selected (Chat View)

```
┌─────────────────────────────────────────────────────────────────┐
│  HEADER                                                          │
│  ┌──────────────────┐                              [User Menu]  │
│  │ Evaluator ▼      │  ← Agent selector dropdown               │
│  └──────────────────┘                                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  SIDEBAR                    CHAT AREA                           │
│  ─────────────────         ─────────────────────────────────    │
│                                                                  │
│  [+ New Conversation]       Messages...                         │
│  ─────────────────                                              │
│  • Math Quiz (Active)       ┌─────────────────────────────┐    │
│  • History Test             │ Question 3 of 10            │    │
│  • Science Review           │                             │    │
│                             │ What is 47 + 38?            │    │
│                             │                             │    │
│                             │ ○ 75                        │    │
│                             │ ○ 85  ← Widget              │    │
│                             │ ○ 86                        │    │
│                             │ ○ 95                        │    │
│                             │                             │    │
│                             │ [Submit]                    │    │
│                             └─────────────────────────────┘    │
│                                                                  │
│                            [Input disabled during assessment]   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 4.3 Per-Message UI Instructions

Each agent message can include UI instructions:

```python
@dataclass
class UiInstruction:
    """UI control sent with agent messages."""

    # Input control
    disable_text_input: bool = False
    input_placeholder: str | None = None

    # Widget (if any)
    widget: ClientAction | None = None

    # Conversation controls
    show_pause_button: bool = True
    show_terminate_button: bool = True

    # Progress (for templates)
    progress: dict | None = None     # { current: 3, total: 10 }
```

SSE event example:

```json
{
  "event": "message_complete",
  "data": {
    "content": "Question 3 of 10:\n\nWhat is 47 + 38?",
    "ui": {
      "disable_text_input": true,
      "widget": {
        "type": "multiple_choice",
        "tool_call_id": "call_123",
        "prompt": "Select your answer:",
        "options": ["75", "85", "86", "95"]
      },
      "progress": { "current": 3, "total": 10 }
    }
  }
}
```

---

## 5. API Design

### 5.1 AgentDefinition Endpoints (Admin)

```
GET    /api/admin/definitions           List all definitions
POST   /api/admin/definitions           Create definition
GET    /api/admin/definitions/{id}      Get definition
PUT    /api/admin/definitions/{id}      Update definition
DELETE /api/admin/definitions/{id}      Delete definition

GET    /api/admin/skill-templates       List skill templates
POST   /api/admin/skill-templates       Create skill template
...
```

### 5.2 User Endpoints

```
# Available definitions for current user
GET    /api/definitions                 List accessible definitions

# Conversations
GET    /api/conversations               List user's conversations
POST   /api/conversations               Create new conversation
GET    /api/conversations/{id}          Get conversation
DELETE /api/conversations/{id}          Archive conversation

# Conversation actions
POST   /api/conversations/{id}/start    Start conversation
POST   /api/conversations/{id}/pause    Pause conversation
POST   /api/conversations/{id}/resume   Resume conversation
POST   /api/conversations/{id}/respond  Submit response to widget
DELETE /api/conversations/{id}/current  Terminate conversation

# SSE stream
GET    /api/conversations/{id}/stream   Event stream

# Sharing
POST   /api/conversations/{id}/share    Share with user
DELETE /api/conversations/{id}/share/{user_id}  Revoke share
```

---

## 6. Files to Delete

### Domain Layer

| File | Reason |
|------|--------|
| `domain/entities/agent.py` | Agent is now a stateless service |
| `domain/entities/session.py` | Sessions are gone |
| `domain/models/session.py` | Replaced by Conversation |
| `domain/models/session_models.py` | Merged into new models |
| `domain/models/session_item.py` | Replaced by GeneratedItem |
| `domain/enums/agent_type.py` | Replaced by AgentDefinition |
| `domain/events/agent.py` | Replaced by conversation events |
| `domain/events/session.py` | Sessions are gone |

### Application Layer

| File/Folder | Reason |
|-------------|--------|
| `application/commands/` - session commands | Sessions gone |
| `application/commands/` - agent aggregate commands | Agent is service |
| `application/queries/` - session queries | Sessions gone |
| `application/queries/` - agent aggregate queries | Agent is service |
| `application/agents/proactive_agent.py` | Replaced by AgentService |
| `application/agents/react_agent.py` | Replaced by AgentService |

### API Layer

| File | Reason |
|------|--------|
| `api/controllers/session_controller.py` | Sessions gone |
| `api/controllers/agents_controller.py` | Replaced by conversations |

### Frontend

| File | Reason |
|------|--------|
| `ui/src/scripts/core/session-mode-manager.js` | Modes are gone |
| `ui/src/scripts/core/agent-manager.js` | Simplified → conversation-manager |

---

## 7. Files to Create

### Domain Layer

| File | Description |
|------|-------------|
| `domain/entities/conversation.py` | Conversation AggregateRoot |
| `domain/models/agent_definition.py` | AgentDefinition dataclass |
| `domain/models/conversation_template.py` | Template + ItemTemplate |
| `domain/models/skill_template.py` | SkillTemplate for item generation |
| `domain/models/generated_item.py` | LLM-generated item |
| `domain/models/ui_instruction.py` | Per-message UI control |
| `domain/enums/conversation_status.py` | Status enum |
| `domain/events/conversation.py` | All conversation events |

### Application Layer

| File | Description |
|------|-------------|
| `application/services/agent_service.py` | Stateless agent executor |
| `application/services/item_generator.py` | LLM item generation |
| `application/commands/conversation_commands.py` | Conversation commands |
| `application/queries/conversation_queries.py` | Conversation queries |
| `application/commands/definition_commands.py` | Admin CRUD |
| `application/queries/definition_queries.py` | Definition queries |

### API Layer

| File | Description |
|------|-------------|
| `api/controllers/conversations_controller.py` | Main user API |
| `api/controllers/definitions_controller.py` | User: list accessible |
| `api/controllers/admin_controller.py` | Admin: CRUD definitions |

### Integration Layer

| File | Description |
|------|-------------|
| `integration/repositories/conversation_repository.py` | EventStoreDB |
| `integration/repositories/definition_repository.py` | MongoDB |
| `integration/repositories/skill_template_repository.py` | MongoDB |
| `integration/models/conversation_dto.py` | DTO for read model |
| `integration/models/definition_dto.py` | DTO |

---

## 8. Default AgentDefinition

Seeded on startup:

```python
DEFAULT_CHAT_DEFINITION = AgentDefinition(
    id="chat",
    owner_user_id=None,  # System-owned
    name="Chat",
    description="General-purpose AI assistant",
    icon="bi-chat-dots",
    system_prompt="You are a helpful AI assistant...",
    agent_starts_first=False,  # Reactive
    tools=[],  # All available tools
    conversation_template=None,  # No template
    is_public=True,  # Available to all
    required_roles=[],
    required_scopes=[],
    allowed_users=None,
    created_by="system",
    created_at=datetime.now(UTC),
    updated_at=datetime.now(UTC),
)
```

---

## 9. Migration Notes

- **Fresh start**: No data migration needed
- **EventStoreDB**: Clear all streams (new Conversation streams)
- **MongoDB**: Drop old collections, create new ones

---

## 10. Summary

| Concept | Old | New |
|---------|-----|-----|
| AggregateRoot | Agent, Session | Conversation (only one) |
| Agent | Stateful entity | Stateless service |
| Session | Aggregate/value object | Gone (merged into Conversation) |
| SessionType | Enum (6+ types) | Gone |
| AgentType | Enum | Gone (use AgentDefinition) |
| Proactive behavior | SessionType + ControlMode | `agent_starts_first` + ConversationTemplate |
| Item generation | Blueprint + runtime | SkillTemplate → LLM → GeneratedItem |
| UI control | Hardcoded per session type | Per-message |
| Sharing | Not supported | First-class on Conversation |

This architecture is:

- **Simpler**: One aggregate, stateless agent
- **Intuitive**: Users think in conversations
- **Flexible**: Any behavior via AgentDefinition
- **Shareable**: Conversations can be shared
- **Auditable**: Generated items persisted for grading

---

_Approved for implementation. Proceed with cleanup and new implementation._
