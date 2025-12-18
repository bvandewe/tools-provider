# Simplified Agent-Host Architecture

!!! warning "Archived Document"
    **Status:** `SUPERSEDED` by v3.0.0 - December 2025

    This version (2.0.0) proposed an Agent-centric model that was later replaced by version 3.0.0 which uses **Conversation as the single aggregate**.
    
    **Current Documentation:**
    
    - [Agent Host Architecture](../architecture/agent-host-architecture.md)
    - [Conversation Flows](../architecture/conversation-flows.md)

---

**Original Version:** 2.0.0
**Original Status:** `DRAFT`
**Date:** December 16, 2025

---

## 1. Executive Summary (Historical)

This document proposed a **drastically simplified architecture** for agent-host, eliminating the fragmented session types (Thought, Learning, Validation, etc.) in favor of a clean, agent-centric model with two chat modes.

### Key Simplifications (v2 - Superseded)

| Current (Complex) | Proposed (Simple) |
|-------------------|-------------------|
| 6+ SessionTypes (Thought, Learning, Validation, Survey, Workflow, Approval) | 2 Chat Modes (Reactive, Proactive) |
| Session as AggregateRoot (legacy) + Session as value object (new) | Session as lightweight value object only |
| AgentType tied to SessionType | AgentDefinition as admin-provisioned template |
| Hardcoded restrictions per session type | Agent controls UI/UX per message |
| Multiple frontend managers (session-mode-manager, agent-manager) | Single unified agent-manager |

---

## 2. Core Concepts (v2)

### 2.1 Two Chat Modes

The fundamental interaction pattern is determined by **who initiates**:

```
┌─────────────────────────────────────────────────────────────────┐
│                         CHAT MODES                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  REACTIVE CHAT                    PROACTIVE CHAT                │
│  ─────────────                    ──────────────                │
│                                                                  │
│  User starts          ◄────────────────────►  Agent starts      │
│  Free-form text input                         Text + Widgets    │
│  Agent responds with text                     May disable input │
│  No structured widgets                        Structured input  │
│                                                                  │
│  Use Cases:                       Use Cases:                    │
│  • General Q&A                    • Evaluator (exams)           │
│  • Brainstorming                  • Survey (feedback)           │
│  • Research assistance            • Workflow (guided process)   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Agent as the Single Aggregate

The **Agent** is the only domain aggregate. It:

- Is **stateful** and **per-user**
- Controls what UI elements appear and when
- Controls what interactions are allowed and when
- Maintains conversation history and execution state
- Is **defined by an AgentDefinition** (admin-provisioned template)

```
┌─────────────────────────────────────────────────────────────────┐
│                     AGENT AGGREGATE                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Agent                                                           │
│  ├── id: UUID                                                   │
│  ├── owner_user_id: str                                         │
│  ├── definition_id: str  ◄── References AgentDefinition         │
│  ├── status: active | archived                                  │
│  │                                                               │
│  ├── preferences: {}  (user-specific)                           │
│  ├── metrics: { sessions, interactions, completions }           │
│  │                                                               │
│  ├── active_conversation: Conversation | None                   │
│  │   ├── id: UUID                                               │
│  │   ├── messages: LlmMessage[]                                 │
│  │   ├── status: active | completed | terminated                │
│  │   └── pending_action: ClientAction | None                    │
│  │                                                               │
│  └── execution_state: ExecutionState | None  (for resume)       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 AgentDefinition (Admin-Provisioned Template)

AgentDefinitions are **templates** that define agent behavior. They are:

- Created by **admin users** via API or admin UI
- Made available to users based on **JWT claims/roles/scopes**
- Stored in the read model (MongoDB) for fast lookup

```
┌─────────────────────────────────────────────────────────────────┐
│                   AGENT DEFINITION                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  AgentDefinition                                                 │
│  ├── id: str (slug, e.g., "evaluator", "customer-survey")      │
│  ├── name: str                                                  │
│  ├── description: str                                           │
│  │                                                               │
│  ├── chat_mode: "reactive" | "proactive"                        │
│  │                                                               │
│  ├── system_prompt: str                                         │
│  ├── tools: ToolDefinition[]  (available tools)                 │
│  │                                                               │
│  ├── ui_config:                                                 │
│  │   ├── can_user_type: bool (default behavior)                 │
│  │   ├── show_conversation_history: bool                        │
│  │   └── allow_early_termination: bool                          │
│  │                                                               │
│  ├── access_control:                                            │
│  │   ├── required_roles: str[]                                  │
│  │   ├── required_scopes: str[]                                 │
│  │   └── allowed_users: str[] | null (null = all with roles)   │
│  │                                                               │
│  ├── proactive_config: (only for proactive mode)                │
│  │   ├── content_source: "blueprint" | "workflow" | "form"     │
│  │   ├── blueprint_id: str | None                               │
│  │   └── workflow_id: str | None                                │
│  │                                                               │
│  ├── created_by: str                                            │
│  ├── created_at: datetime                                       │
│  └── updated_at: datetime                                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.4 Proactive Agent Examples

| Agent Definition | Description | Content Source |
|------------------|-------------|----------------|
| `evaluator` | Drives conversation to assess knowledge | Blueprint (exam definition → skill templates) |
| `survey` | Drives conversation to collect feedback | Form definition (questions, field types) |
| `workflow` | Drives multi-step guided process | Workflow definition (steps, triggers, choices) |

---

## 3. Simplified Domain Model

### 3.1 Entities to KEEP

| Entity | Role | Notes |
|--------|------|-------|
| **Agent** | AggregateRoot | Owns conversation, controls UX |
| **Conversation** | Value Object (within Agent) | Replaces Session |
| **AgentDefinition** | Read Model Entity | Admin-provisioned template |

### 3.2 Entities to REMOVE or MERGE

| Entity | Action | Reason |
|--------|--------|--------|
| **Session (AggregateRoot)** | REMOVE | Merge into Agent.active_conversation |
| **Session (value object in Agent)** | RENAME → Conversation | Clearer naming |
| **SessionType enum** | REMOVE | Replace with AgentDefinition.chat_mode |
| **ControlMode enum** | SIMPLIFY | Part of AgentDefinition |
| **AgentType enum** | REMOVE | Replace with AgentDefinition reference |

### 3.3 New Enums

```python
class ChatMode(str, Enum):
    """Who initiates and drives the conversation."""
    REACTIVE = "reactive"    # User starts, text-only responses
    PROACTIVE = "proactive"  # Agent starts, may use widgets


class ConversationStatus(str, Enum):
    """Status of an active conversation."""
    ACTIVE = "active"                        # Conversation in progress
    AWAITING_USER = "awaiting_user"          # Waiting for user input
    AWAITING_WIDGET = "awaiting_widget"      # Waiting for widget response
    COMPLETED = "completed"                  # Successfully finished
    TERMINATED = "terminated"                # Ended early
```

---

## 4. Simplified Agent Aggregate

```python
@map_to(AgentDto)
class AgentState(AggregateState[str]):
    """Agent state - simplified."""

    # Identity
    id: str
    owner_user_id: str
    definition_id: str  # References AgentDefinition
    status: str  # "active" | "archived"

    # User preferences (overrides from definition)
    preferences: dict[str, Any]

    # Metrics
    total_conversations: int
    total_interactions: int
    successful_completions: int

    # Active conversation (None when no conversation)
    active_conversation: dict[str, Any] | None

    # Execution state for suspend/resume
    execution_state: dict[str, Any] | None

    # Conversation history (summaries of past conversations)
    conversation_history: list[dict[str, Any]]

    # Timestamps
    created_at: datetime
    updated_at: datetime
    last_interaction_at: datetime | None


class Agent(AggregateRoot[AgentState, str]):
    """Agent aggregate - the only aggregate root."""

    # Factory
    @classmethod
    def create(cls, owner_user_id: str, definition_id: str, name: str) -> "Agent": ...

    # Conversation lifecycle
    def start_conversation(self, conversation_id: str) -> None: ...
    def add_message(self, message: LlmMessage) -> None: ...
    def request_user_action(self, action: ClientAction) -> None: ...
    def receive_user_response(self, response: ClientResponse) -> None: ...
    def complete_conversation(self) -> None: ...
    def terminate_conversation(self, reason: str) -> None: ...

    # Execution state (for crash recovery)
    def suspend_execution(self, state: ExecutionState) -> None: ...
    def resume_execution(self) -> ExecutionState | None: ...

    # Preferences
    def update_preferences(self, preferences: dict[str, Any]) -> None: ...

    # Lifecycle
    def archive(self, reason: str) -> None: ...
```

---

## 5. Per-Message UI Control

A key simplification: **the agent controls UI per message**, not per session type.

When the agent sends a message, it can include UI instructions:

```python
@dataclass
class UiInstruction:
    """Instructions for the UI attached to a message."""

    # Input control
    disable_text_input: bool = False
    input_placeholder: str | None = None

    # Widget to display (if any)
    widget: ClientAction | None = None

    # Conversation control
    show_end_button: bool = True
    show_history: bool = True
```

This is sent as part of the SSE stream:

```json
{
  "event": "message_complete",
  "data": {
    "content": "Please select your answer:",
    "ui": {
      "disable_text_input": true,
      "widget": {
        "type": "multiple_choice",
        "options": ["A", "B", "C", "D"]
      }
    }
  }
}
```

The frontend simply **follows instructions** - no complex mode logic.

---

## 6. Frontend Simplification

### 6.1 Remove

| File/Module | Reason |
|-------------|--------|
| `session-mode-manager.js` | Modes are gone; agent controls everything |
| `SessionMode` enum | No more modes |
| Session type cards in welcome screen | Replace with agent selector |
| Session list in sidebar | Replace with conversation list per agent |

### 6.2 Simplify

| File/Module | Change |
|-------------|--------|
| `agent-manager.js` | Becomes the single source of truth |
| `conversation-manager.js` | Works with agent's conversations |
| Sidebar | Shows: Agent selector + Conversations for selected agent |
| Chat input | Follows `UiInstruction` from agent messages |

### 6.3 New UI Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        NEW UI FLOW                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. User logs in                                                │
│     └── Frontend loads available AgentDefinitions (filtered     │
│         by user's JWT roles/scopes)                             │
│                                                                  │
│  2. User selects an Agent Definition (or uses default)          │
│     └── Frontend calls GET /agents?definition_id=X              │
│         └── Returns existing agent or creates new one           │
│                                                                  │
│  3. Sidebar shows agent's conversations                         │
│     └── User can start new or resume existing                   │
│                                                                  │
│  4. Conversation starts                                         │
│     └── If REACTIVE: Input enabled, user types first           │
│     └── If PROACTIVE: Input disabled, agent sends first        │
│                                                                  │
│  5. During conversation                                         │
│     └── Agent's UiInstruction controls input state per message │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. API Simplification

### 7.1 Remove

| Endpoint | Reason |
|----------|--------|
| `POST /sessions` | Sessions are gone |
| `GET /sessions` | Sessions are gone |
| `POST /sessions/{id}/respond` | Merged into agent endpoint |
| All session-related endpoints | Merged into agent |

### 7.2 Keep/Modify

| Endpoint | Change |
|----------|--------|
| `GET /agents` | List user's agents |
| `POST /agents` | Get-or-create agent by definition |
| `GET /agents/{id}` | Get agent details |
| `GET /agents/{id}/conversations` | List agent's conversations |
| `POST /agents/{id}/conversations` | Start new conversation |
| `GET /agents/{id}/conversations/{conv_id}` | Get conversation |
| `POST /agents/{id}/respond` | Submit response to widget |
| `GET /agents/{id}/stream` | SSE stream for agent events |
| `DELETE /agents/{id}/conversations/current` | End current conversation |

### 7.3 New Admin Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /admin/agent-definitions` | List all definitions |
| `POST /admin/agent-definitions` | Create new definition |
| `GET /admin/agent-definitions/{id}` | Get definition details |
| `PUT /admin/agent-definitions/{id}` | Update definition |
| `DELETE /admin/agent-definitions/{id}` | Delete definition |

---

## 8. Migration Plan

### Phase 1: Backend Cleanup (Domain Layer)

1. **Remove** `domain/entities/session.py` (the AggregateRoot version)
2. **Rename** `domain/models/session.py` → `domain/models/conversation.py`
3. **Simplify** Agent aggregate to use `Conversation` instead of `Session`
4. **Create** `AgentDefinition` entity in read model
5. **Remove** `SessionType`, `AgentType` enums
6. **Create** `ChatMode` enum

### Phase 2: Backend Cleanup (Application Layer)

1. **Remove** session-related commands/queries
2. **Simplify** agent commands/queries
3. **Create** AgentDefinition CRUD for admin
4. **Update** agent factory to use definitions

### Phase 3: API Cleanup

1. **Remove** session controller
2. **Simplify** agents controller
3. **Add** admin controller for definitions
4. **Update** SSE to include `UiInstruction`

### Phase 4: Frontend Cleanup

1. **Remove** `session-mode-manager.js`
2. **Remove** session type cards
3. **Simplify** `agent-manager.js`
4. **Update** sidebar to show agent + conversations
5. **Update** chat input to follow `UiInstruction`

---

## 9. Files to Remove/Modify

### Domain Layer

| Action | File |
|--------|------|
| DELETE | `domain/entities/session.py` |
| RENAME | `domain/models/session.py` → `conversation.py` |
| DELETE | `domain/models/session_models.py` (merge into conversation) |
| MODIFY | `domain/entities/agent.py` |
| DELETE | `domain/enums/agent_type.py` |
| MODIFY | `domain/enums/session_status.py` → `conversation_status.py` |

### Application Layer

| Action | File |
|--------|------|
| DELETE | Commands: `create_session_command.py`, etc. |
| DELETE | Queries: `get_session_query.py`, etc. |
| MODIFY | Agent commands/queries |
| CREATE | `agent_definition_commands.py` |

### API Layer

| Action | File |
|--------|------|
| DELETE | `session_controller.py` |
| MODIFY | `agents_controller.py` |
| CREATE | `admin_controller.py` |

### Frontend

| Action | File |
|--------|------|
| DELETE | `session-mode-manager.js` |
| MODIFY | `agent-manager.js` |
| MODIFY | `conversation-manager.js` |
| DELETE | Session type cards in templates |
| MODIFY | Sidebar template |

---

## 10. Summary

The simplified architecture:

1. **Two chat modes**: Reactive (user-driven) and Proactive (agent-driven)
2. **One aggregate**: Agent owns Conversations (not Sessions)
3. **Admin-provisioned definitions**: AgentDefinition templates with access control
4. **Per-message UI control**: Agent tells frontend what to show/enable
5. **Clean separation**: Agent controls UX, frontend follows instructions

This eliminates:

- 6+ session types → 2 modes (in agent definition)
- Session aggregate complexity → Simple conversation value object
- Hardcoded session restrictions → Dynamic per-message control
- Multiple frontend managers → Single agent manager
- Type-specific logic everywhere → Definition-driven behavior

---

_This document should be reviewed and approved before implementation begins._
