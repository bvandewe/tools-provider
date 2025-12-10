# Proactive Agent Architecture Specification

**Version:** 1.0.0
**Status:** `DRAFT`
**Date:** December 10, 2025
**Confidence:** 0.82

---

## 1. Executive Summary

This specification defines the **Proactive Agent** architecture for the agent-host application. Unlike the existing **Reactive Agent** (where users drive conversations), the Proactive Agent **drives the conversation**, presenting structured UI widgets to collect user responses.

### Core Concept: Inverted Conversation Flow

| Aspect | Reactive Agent | Proactive Agent |
|--------|---------------|-----------------|
| **Initiator** | User prompts first | Agent prompts first |
| **Control** | User drives | Agent drives |
| **Input Mode** | Free text always | Agent-controlled widgets |
| **Loop** | User → Agent → Response | Agent → Widget → User Response → Agent |
| **Termination** | User ends | Agent/criteria ends |

### Use Cases

| Session Type | Control Mode | Description |
|--------------|--------------|-------------|
| **ThoughtSession** | Reactive | Reflective exploration, user-driven |
| **LearningSession** | Proactive | Skill development with guided + free input |
| **ValidationSession** | Proactive | Competency certification, structured input only |
| **SurveySession** | Proactive | Data collection via forms |
| **WorkflowSession** | Proactive | Guided multi-step processes |
| **ApprovalSession** | Proactive | Decision workflows with confirmation |

---

## 2. Architecture Overview

### 2.1 System Context

```
┌─────────────────────────────────────────────────────────────────┐
│                        AGENT-HOST                               │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────┐                     │
│  │    Session      │    │  Conversation   │                     │
│  │   (Aggregate)   │───▶│   (Aggregate)   │                     │
│  │                 │    │                 │                     │
│  │ - session_type  │    │ - messages[]    │                     │
│  │ - control_mode  │    │ - tool_calls    │                     │
│  │ - state         │    │ - tool_results  │                     │
│  │ - current_item  │    │                 │                     │
│  │ - items[]       │    │                 │                     │
│  │ - ui_state      │    │                 │                     │
│  │ - config        │    │                 │                     │
│  └─────────────────┘    └─────────────────┘                     │
│           │                                                     │
│           ▼                                                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Agent Abstraction                     │   │
│  │  ┌──────────────┐              ┌──────────────────────┐  │   │
│  │  │ ReActAgent   │              │ ProactiveAgent       │  │   │
│  │  │ (reactive)   │              │ (proactive)          │  │   │
│  │  └──────────────┘              └──────────────────────┘  │   │
│  │                                         │                │   │
│  │                    ┌────────────────────┘                │   │
│  │                    ▼                                     │   │
│  │  ┌─────────────────────────────────────────────────┐     │   │
│  │  │           Client Tool Interceptor               │     │   │
│  │  │  - present_choices()                            │     │   │
│  │  │  - request_free_text()                          │     │   │
│  │  │  - present_drag_drop()                          │     │   │
│  │  │  - present_iframe()                             │     │   │
│  │  │  - ...                                          │     │   │
│  │  └─────────────────────────────────────────────────┘     │   │
│  └──────────────────────────────────────────────────────────┘   │
│           │                                                     │
│           ▼ SSE: client_action                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                      FRONTEND                            │   │
│  │  ax-client-action-renderer                               │   │
│  │  ├── ax-multiple-choice                                  │   │
│  │  ├── ax-free-text-prompt                                 │   │
│  │  ├── ax-drag-drop-simple                                 │   │
│  │  ├── ax-drag-drop-category                               │   │
│  │  ├── ax-hot-spot                                         │   │
│  │  ├── ax-graphical-builder                                │   │
│  │  ├── ax-rating-scale                                     │   │
│  │  ├── ax-confirmation                                     │   │
│  │  ├── ax-code-editor                                      │   │
│  │  ├── ax-iframe-form                                      │   │
│  │  ├── ax-file-upload                                      │   │
│  │  └── ...                                                 │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Session-Conversation Relationship

The **Session** aggregate wraps a **Conversation** using composition (not inheritance):

- **Conversation**: Raw message log for LLM context and audit trail
- **Session**: Structured interaction metadata, UI state, and control flow

This separation allows:

1. Independent event streams for each aggregate
2. Conversation reuse across different session types
3. Clear separation of concerns

---

## 3. Domain Model

### 3.1 Session Aggregate

```python
class SessionType(str, Enum):
    """Types of sessions with different behaviors."""
    THOUGHT = "thought"           # Reactive, reflective exploration
    LEARNING = "learning"         # Proactive, hybrid input
    VALIDATION = "validation"     # Proactive, structured only
    SURVEY = "survey"             # Proactive, data collection
    WORKFLOW = "workflow"         # Proactive, guided process
    APPROVAL = "approval"         # Proactive, decision flow


class ControlMode(str, Enum):
    """Who drives the conversation."""
    REACTIVE = "reactive"         # User prompts first
    PROACTIVE = "proactive"       # Agent prompts first


class SessionStatus(str, Enum):
    """Session lifecycle states."""
    PENDING = "pending"                       # Created but not started
    ACTIVE = "active"                         # Agent loop running
    AWAITING_CLIENT_ACTION = "awaiting_client_action"  # Waiting for user widget response
    COMPLETED = "completed"                   # Successfully finished
    EXPIRED = "expired"                       # Timed out
    TERMINATED = "terminated"                 # Manually stopped


class SessionState(AggregateState[str]):
    """Encapsulates the persisted state for the Session aggregate."""

    # Identity
    id: str
    user_id: str
    conversation_id: str  # Links to Conversation aggregate

    # Configuration
    session_type: SessionType
    control_mode: ControlMode
    system_prompt: str
    config: SessionConfig

    # State
    status: SessionStatus
    current_item_id: str | None
    items: list[SessionItem]

    # UI State (for restoration)
    ui_state: UiState
    pending_action: ClientAction | None

    # Audit
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    terminated_reason: str | None


class Session(AggregateRoot[SessionState, str]):
    """Session aggregate managing proactive/reactive interactions."""

    # Factory methods
    @classmethod
    def create(
        cls,
        user_id: str,
        session_type: SessionType,
        conversation_id: str,
        config: SessionConfig | None = None,
    ) -> "Session": ...

    # Commands
    def start(self) -> None: ...
    def set_pending_action(self, action: ClientAction) -> None: ...
    def submit_response(self, response: ClientResponse) -> SessionItem: ...
    def complete(self) -> None: ...
    def terminate(self, reason: str) -> None: ...
    def expire(self) -> None: ...

    # Queries
    def get_pending_action(self) -> ClientAction | None: ...
    def get_current_item(self) -> SessionItem | None: ...
    def get_ui_state(self) -> UiState: ...
```

### 3.2 Value Objects

```python
@dataclass
class SessionConfig:
    """Type-specific session configuration."""

    # Time constraints
    time_limit_seconds: int | None = None
    item_time_limit_seconds: int | None = None

    # Termination criteria
    max_items: int | None = None
    completion_criteria: dict | None = None  # Type-specific

    # Input constraints
    allow_skip: bool = False
    allow_back: bool = False

    # Concurrency
    allow_concurrent_sessions: bool = True


@dataclass
class SessionItem:
    """A single interaction loop within a session."""

    id: str
    sequence: int
    started_at: datetime
    completed_at: datetime | None

    # What agent presented
    agent_prompt: str
    client_action: ClientAction | None

    # What user provided
    user_response: ClientResponse | None
    response_time_ms: float | None

    # Evaluation (optional)
    evaluation: dict | None = None


@dataclass
class ClientAction:
    """An action requiring client-side rendering."""

    tool_call_id: str
    tool_name: str
    widget_type: str
    props: dict[str, Any]
    lock_input: bool = True

    def to_sse_payload(self) -> dict:
        return {
            "tool_call_id": self.tool_call_id,
            "component": self.widget_type,
            "props": self.props,
            "lock_input": self.lock_input,
        }


@dataclass
class ClientResponse:
    """User's response to a client action."""

    tool_call_id: str
    response: Any
    timestamp: datetime
    validation_status: ValidationStatus = ValidationStatus.VALID
    validation_errors: list[str] | None = None


@dataclass
class UiState:
    """Current UI state for restoration on reconnect/refresh."""

    chat_input_locked: bool = False
    active_widget: ClientAction | None = None
    widget_partial_state: dict | None = None  # e.g., partially filled form
```

### 3.3 Domain Events

```python
# Session lifecycle events
@cloudevent("session.created.v1")
class SessionCreatedDomainEvent: ...

@cloudevent("session.started.v1")
class SessionStartedDomainEvent: ...

@cloudevent("session.completed.v1")
class SessionCompletedDomainEvent: ...

@cloudevent("session.terminated.v1")
class SessionTerminatedDomainEvent: ...

@cloudevent("session.expired.v1")
class SessionExpiredDomainEvent: ...

# Interaction events
@cloudevent("session.item.started.v1")
class SessionItemStartedDomainEvent: ...

@cloudevent("session.item.completed.v1")
class SessionItemCompletedDomainEvent: ...

@cloudevent("session.pending_action.set.v1")
class PendingActionSetDomainEvent: ...

@cloudevent("session.pending_action.cleared.v1")
class PendingActionClearedDomainEvent: ...

@cloudevent("session.response.submitted.v1")
class ResponseSubmittedDomainEvent: ...
```

---

## 4. Client Tool System

### 4.1 Client Tool Registry

Client tools are **hardcoded in agent-host** (not from tools-provider). They represent UI widgets the agent can invoke.

```python
@dataclass
class ClientToolDefinition:
    """Definition of a client-side tool."""

    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema
    response_schema: dict[str, Any]
    widget_type: str
    default_lock_input: bool = True


CLIENT_TOOLS: dict[str, ClientToolDefinition] = {
    # === Single Selection ===
    "present_choices": ClientToolDefinition(
        name="present_choices",
        description="Present multiple choice options. User selects one.",
        parameters={
            "question": {"type": "string", "description": "The question to ask"},
            "options": {"type": "array", "items": {"type": "string"}, "description": "Available choices"},
            "lock_input": {"type": "boolean", "default": True},
        },
        response_schema={"selection": "string", "index": "integer"},
        widget_type="multiple_choice",
    ),

    # === Multiple Selection ===
    "present_multi_select": ClientToolDefinition(
        name="present_multi_select",
        description="Present options where user can select multiple.",
        parameters={
            "question": {"type": "string"},
            "options": {"type": "array", "items": {"type": "string"}},
            "min_selections": {"type": "integer", "default": 1},
            "max_selections": {"type": "integer"},
            "lock_input": {"type": "boolean", "default": True},
        },
        response_schema={"selections": "array[string]", "indices": "array[integer]"},
        widget_type="multi_select",
    ),

    # === Free Text ===
    "request_free_text": ClientToolDefinition(
        name="request_free_text",
        description="Request free-form text input from user.",
        parameters={
            "prompt": {"type": "string"},
            "placeholder": {"type": "string"},
            "min_length": {"type": "integer", "default": 0},
            "max_length": {"type": "integer"},
            "lock_input": {"type": "boolean", "default": False},
        },
        response_schema={"text": "string"},
        widget_type="free_text",
        default_lock_input=False,
    ),

    # === Rating Scale ===
    "present_rating_scale": ClientToolDefinition(
        name="present_rating_scale",
        description="Collect rating on a numeric scale.",
        parameters={
            "question": {"type": "string"},
            "min": {"type": "integer", "default": 1},
            "max": {"type": "integer", "default": 5},
            "labels": {"type": "object", "description": "Optional labels for values"},
            "lock_input": {"type": "boolean", "default": True},
        },
        response_schema={"rating": "integer"},
        widget_type="rating_scale",
    ),

    # === Confirmation ===
    "present_confirmation": ClientToolDefinition(
        name="present_confirmation",
        description="Yes/No confirmation dialog.",
        parameters={
            "message": {"type": "string"},
            "confirm_label": {"type": "string", "default": "Yes"},
            "cancel_label": {"type": "string", "default": "No"},
            "lock_input": {"type": "boolean", "default": True},
        },
        response_schema={"confirmed": "boolean"},
        widget_type="confirmation",
    ),

    # === Simple Drag & Drop ===
    "present_drag_drop_simple": ClientToolDefinition(
        name="present_drag_drop_simple",
        description="Drag items to predefined drop zones (1:1 mapping).",
        parameters={
            "instruction": {"type": "string"},
            "items": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "string"}, "label": {"type": "string"}}}},
            "dropzones": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "string"}, "label": {"type": "string"}}}},
            "lock_input": {"type": "boolean", "default": True},
        },
        response_schema={"placements": "object"},  # {zone_id: item_id}
        widget_type="drag_drop_simple",
    ),

    # === Category Drag & Drop ===
    "present_drag_drop_category": ClientToolDefinition(
        name="present_drag_drop_category",
        description="Categorize items by dragging into groups.",
        parameters={
            "instruction": {"type": "string"},
            "items": {"type": "array", "items": {"type": "object"}},
            "categories": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "string"}, "label": {"type": "string"}}}},
            "ordered": {"type": "boolean", "default": False, "description": "Whether order within category matters"},
            "lock_input": {"type": "boolean", "default": True},
        },
        response_schema={"categorizations": "object"},  # {category_id: [item_ids]}
        widget_type="drag_drop_category",
    ),

    # === Hot Spot ===
    "present_hot_spot": ClientToolDefinition(
        name="present_hot_spot",
        description="User clicks on regions of an image.",
        parameters={
            "instruction": {"type": "string"},
            "image_url": {"type": "string"},
            "regions": {"type": "array", "description": "Optional predefined clickable regions"},
            "multi_select": {"type": "boolean", "default": False},
            "lock_input": {"type": "boolean", "default": True},
        },
        response_schema={"clicks": "array"},  # [{x, y}] or [region_id]
        widget_type="hot_spot",
    ),

    # === Graphical Builder ===
    "present_graphical_builder": ClientToolDefinition(
        name="present_graphical_builder",
        description="Build diagrams by placing and connecting components.",
        parameters={
            "instruction": {"type": "string"},
            "palette": {"type": "array", "description": "Available components to place"},
            "canvas_config": {"type": "object", "description": "Canvas size, grid, etc."},
            "allow_connections": {"type": "boolean", "default": True},
            "lock_input": {"type": "boolean", "default": True},
        },
        response_schema={"diagram": "object"},  # {nodes: [], connections: []}
        widget_type="graphical_builder",
    ),

    # === Code Editor ===
    "present_code_editor": ClientToolDefinition(
        name="present_code_editor",
        description="Syntax-highlighted code input.",
        parameters={
            "prompt": {"type": "string"},
            "language": {"type": "string", "default": "python"},
            "initial_code": {"type": "string"},
            "lock_input": {"type": "boolean", "default": True},
        },
        response_schema={"code": "string"},
        widget_type="code_editor",
    ),

    # === Iframe Form ===
    "present_iframe_form": ClientToolDefinition(
        name="present_iframe_form",
        description="Embed external form and await submission via postMessage.",
        parameters={
            "instruction": {"type": "string"},
            "url": {"type": "string"},
            "expected_origin": {"type": "string", "description": "Origin to accept postMessage from"},
            "lock_input": {"type": "boolean", "default": True},
        },
        response_schema={"form_data": "object"},
        widget_type="iframe_form",
    ),

    # === File Upload ===
    "present_file_upload": ClientToolDefinition(
        name="present_file_upload",
        description="Request file upload from user.",
        parameters={
            "prompt": {"type": "string"},
            "accept": {"type": "string", "description": "MIME types (e.g., 'image/*,.pdf')"},
            "max_size_mb": {"type": "integer", "default": 10},
            "multiple": {"type": "boolean", "default": False},
            "lock_input": {"type": "boolean", "default": True},
        },
        response_schema={"files": "array"},  # [{filename, url, size, mime}]
        widget_type="file_upload",
    ),
}
```

### 4.2 Tool Interception Logic

```python
def is_client_tool(tool_name: str) -> bool:
    """Check if a tool should be executed client-side."""
    return tool_name in CLIENT_TOOLS


def get_client_tool_manifest() -> list[LlmToolDefinition]:
    """Generate LLM-compatible tool definitions for client tools."""
    return [
        LlmToolDefinition(
            name=tool.name,
            description=tool.description,
            parameters=tool.parameters,
        )
        for tool in CLIENT_TOOLS.values()
    ]
```

---

## 5. Proactive Agent Implementation

### 5.1 Agent Class

```python
class ProactiveAgent(Agent):
    """Agent that drives the conversation, presenting widgets to users."""

    def __init__(
        self,
        llm_provider: LlmProvider,
        config: AgentConfig | None = None,
    ) -> None:
        super().__init__(llm_provider, config)

    async def start_session(
        self,
        session: Session,
        server_tools: list[LlmToolDefinition],
        tool_executor: ToolExecutor,
    ) -> AsyncIterator[AgentEvent]:
        """Start a proactive session - agent takes initiative."""

        yield AgentEvent(
            type=AgentEventType.RUN_STARTED,
            data={"session_id": session.id(), "mode": "proactive"},
        )

        # Combine client + server tools
        all_tools = get_client_tool_manifest() + server_tools

        context = AgentRunContext(
            user_message="",  # No initial user message
            conversation_history=[],
            tools=all_tools,
            tool_executor=tool_executor,
            metadata={"session_id": session.id(), "session_type": session.state.session_type},
        )

        async for event in self._proactive_loop(session, context):
            yield event

    async def resume_with_response(
        self,
        session: Session,
        client_response: ClientResponse,
        server_tools: list[LlmToolDefinition],
        tool_executor: ToolExecutor,
    ) -> AsyncIterator[AgentEvent]:
        """Resume after user responded to a client action."""

        pending = session.get_pending_action()
        if not pending:
            yield AgentEvent(
                type=AgentEventType.RUN_FAILED,
                data={"error": "No pending action to resume"},
            )
            return

        # Validate response
        validation = self._validate_response(pending, client_response)
        if not validation.is_valid:
            # Include validation status but continue gracefully
            client_response.validation_status = ValidationStatus.INVALID
            client_response.validation_errors = validation.errors

        # Build tool result
        tool_result = ToolExecutionResult(
            call_id=pending.tool_call_id,
            tool_name=pending.tool_name,
            success=True,
            result={
                "user_response": client_response.response,
                "validation_status": client_response.validation_status.value,
                "validation_errors": client_response.validation_errors,
            },
        )

        # Clear pending action
        session.submit_response(client_response)

        # Combine tools
        all_tools = get_client_tool_manifest() + server_tools

        context = AgentRunContext(
            user_message="",
            conversation_history=[tool_result.to_llm_message()],
            tools=all_tools,
            tool_executor=tool_executor,
            metadata={"session_id": session.id()},
        )

        async for event in self._proactive_loop(session, context):
            yield event

    async def _proactive_loop(
        self,
        session: Session,
        context: AgentRunContext,
    ) -> AsyncIterator[AgentEvent]:
        """Core loop - continues until client action or completion."""

        messages = self._build_messages(context)

        for iteration in range(self._config.max_iterations):
            yield AgentEvent(
                type=AgentEventType.ITERATION_STARTED,
                data={"iteration": iteration + 1},
            )

            # Call LLM
            response = await self._llm.chat(messages, tools=context.tools)

            # Add assistant response to history
            messages.append(LlmMessage.assistant(
                content=response.content,
                tool_calls=response.tool_calls,
            ))

            # Emit content if any
            if response.content:
                yield AgentEvent(
                    type=AgentEventType.LLM_RESPONSE_CHUNK,
                    data={"content": response.content},
                )

            # No tool calls = agent finished
            if not response.tool_calls:
                yield AgentEvent(
                    type=AgentEventType.RUN_COMPLETED,
                    data={"response": response.content, "finished": True},
                )
                return

            # Process tool calls
            for tool_call in response.tool_calls:
                if is_client_tool(tool_call.name):
                    # === CLIENT TOOL: Suspend loop ===
                    tool_def = CLIENT_TOOLS[tool_call.name]

                    client_action = ClientAction(
                        tool_call_id=tool_call.id,
                        tool_name=tool_call.name,
                        widget_type=tool_def.widget_type,
                        props=tool_call.arguments,
                        lock_input=tool_call.arguments.get("lock_input", tool_def.default_lock_input),
                    )

                    # Persist for resumption
                    session.set_pending_action(client_action)

                    # Emit to frontend
                    yield AgentEvent(
                        type=AgentEventType.CLIENT_ACTION,
                        data=client_action.to_sse_payload(),
                    )

                    # === SUSPEND: Exit loop ===
                    yield AgentEvent(
                        type=AgentEventType.RUN_SUSPENDED,
                        data={"awaiting": "client_action", "tool_call_id": tool_call.id},
                    )
                    return

                else:
                    # === SERVER TOOL: Execute via tools-provider ===
                    yield AgentEvent(
                        type=AgentEventType.TOOL_EXECUTION_STARTED,
                        data={"tool_name": tool_call.name, "call_id": tool_call.id},
                    )

                    request = ToolExecutionRequest(
                        call_id=tool_call.id,
                        tool_name=tool_call.name,
                        arguments=tool_call.arguments,
                    )

                    async for result in context.tool_executor(request):
                        messages.append(result.to_llm_message())

                        yield AgentEvent(
                            type=AgentEventType.TOOL_EXECUTION_COMPLETED,
                            data={
                                "call_id": result.call_id,
                                "tool_name": result.tool_name,
                                "success": result.success,
                            },
                        )

        # Max iterations
        yield AgentEvent(
            type=AgentEventType.RUN_FAILED,
            data={"error": "Max iterations reached"},
        )

    def _validate_response(
        self,
        action: ClientAction,
        response: ClientResponse,
    ) -> ValidationResult:
        """Validate user response against expected schema."""
        tool_def = CLIENT_TOOLS.get(action.tool_name)
        if not tool_def:
            return ValidationResult(is_valid=False, errors=["Unknown tool"])

        # Schema validation logic here
        # For MVP, accept all responses and let LLM handle unexpected input
        return ValidationResult(is_valid=True)

    def _build_system_message(self) -> LlmMessage:
        """Build proactive-specific system prompt."""
        # Override with session-type-specific prompts
        return LlmMessage.system(self._config.system_prompt)
```

### 5.2 New Agent Event Types

```python
class AgentEventType(str, Enum):
    # ... existing events ...

    # New events for proactive flow
    CLIENT_ACTION = "client_action"      # Widget to render
    RUN_SUSPENDED = "run_suspended"      # Loop paused, awaiting response
    RUN_RESUMED = "run_resumed"          # Loop continuing after response
```

---

## 6. API Endpoints

### 6.1 Session Endpoints (Agent-Host)

```yaml
# Session Management
POST   /api/sessions                    # Create and start session (atomic)
GET    /api/sessions                    # List user's sessions
GET    /api/sessions/{id}               # Get session details
DELETE /api/sessions/{id}               # Terminate session

# Interaction
POST   /api/sessions/{id}/respond       # Submit client action response
GET    /api/sessions/{id}/stream        # SSE stream for session events

# State
GET    /api/sessions/{id}/state         # Get current state (for reconnect)
```

### 6.2 Request/Response Models

```python
class CreateSessionRequest(BaseModel):
    """Request to create and start a new session."""
    session_type: SessionType
    config: SessionConfig | None = None


class CreateSessionResponse(BaseModel):
    """Response after session creation."""
    session_id: str
    conversation_id: str
    status: SessionStatus
    stream_url: str  # SSE endpoint


class SubmitResponseRequest(BaseModel):
    """Request to submit response to pending client action."""
    tool_call_id: str
    response: Any


class SessionStateResponse(BaseModel):
    """Current session state for UI restoration."""
    session_id: str
    status: SessionStatus
    ui_state: UiState
    pending_action: ClientAction | None
    items_completed: int
    time_remaining_seconds: int | None
```

### 6.3 Controller Implementation

```python
class SessionController(ControllerBase):
    """Session management endpoints."""

    @post("/")
    async def create_session(
        self,
        body: CreateSessionRequest,
        user: dict = Depends(get_current_user),
        access_token: str = Depends(get_access_token),
    ) -> CreateSessionResponse:
        """Create and start a new session."""

        # Create session command
        command = CreateSessionCommand(
            user_id=user["sub"],
            session_type=body.session_type,
            config=body.config,
        )
        result = await self.mediator.execute_async(command)

        if not result.is_success:
            raise HTTPException(status_code=400, detail=result.error)

        session = result.data

        # Start proactive agent stream
        return CreateSessionResponse(
            session_id=session.id(),
            conversation_id=session.state.conversation_id,
            status=session.state.status,
            stream_url=f"/api/sessions/{session.id()}/stream",
        )

    @post("/{session_id}/respond")
    async def submit_response(
        self,
        session_id: str,
        body: SubmitResponseRequest,
        user: dict = Depends(get_current_user),
        access_token: str = Depends(get_access_token),
    ) -> StreamingResponse:
        """Submit response and continue agent loop."""

        # Load session
        session = await self._get_user_session(session_id, user["sub"])

        if session.state.status != SessionStatus.AWAITING_CLIENT_ACTION:
            raise HTTPException(
                status_code=400,
                detail=f"Session not awaiting response (status: {session.state.status})",
            )

        # Validate tool_call_id matches
        if session.state.pending_action.tool_call_id != body.tool_call_id:
            raise HTTPException(status_code=400, detail="tool_call_id mismatch")

        # Build response
        client_response = ClientResponse(
            tool_call_id=body.tool_call_id,
            response=body.response,
            timestamp=datetime.now(UTC),
        )

        # Resume agent and stream
        async def event_generator():
            async for event in self._session_service.resume_session(
                session=session,
                client_response=client_response,
                access_token=access_token,
            ):
                yield f"event: {event.type.value}\ndata: {json.dumps(event.data)}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
        )

    @get("/{session_id}/state")
    async def get_session_state(
        self,
        session_id: str,
        user: dict = Depends(get_current_user),
    ) -> SessionStateResponse:
        """Get current session state for UI restoration."""

        session = await self._get_user_session(session_id, user["sub"])

        return SessionStateResponse(
            session_id=session.id(),
            status=session.state.status,
            ui_state=session.state.ui_state,
            pending_action=session.state.pending_action,
            items_completed=len(session.state.items),
            time_remaining_seconds=self._calculate_time_remaining(session),
        )
```

---

## 7. SSE Protocol

### 7.1 Event Types

```yaml
# Content streaming (same as reactive)
event: content_chunk
data: {"content": "Let me ask you a question..."}

event: content_complete
data: {"content": "Full message here"}

# Client action (new for proactive)
event: client_action
data:
  tool_call_id: "call_abc123"
  component: "multiple_choice"
  props:
    question: "What is 2 + 2?"
    options: ["3", "4", "5"]
  lock_input: true

# Tool execution (same as reactive)
event: tool_executing
data: {"tool_name": "get_exam_item", "call_id": "call_xyz"}

event: tool_result
data: {"call_id": "call_xyz", "success": true, "result": {...}}

# State changes (new for proactive)
event: state_change
data: {"status": "awaiting_client_action", "pending_action": {...}}

event: session_completed
data: {"reason": "criteria_met", "summary": {...}}

event: session_expired
data: {"reason": "time_limit"}
```

### 7.2 Reconnection Protocol

When client reconnects (refresh, network recovery):

1. Client calls `GET /api/sessions/{id}/state`
2. Server returns `SessionStateResponse` with `pending_action` if any
3. Client renders `pending_action` widget if present
4. SSE stream reconnects and resumes

---

## 8. Session Type Configurations

### 8.1 ThoughtSession (Reactive)

```python
THOUGHT_SESSION_CONFIG = SessionTypeConfig(
    session_type=SessionType.THOUGHT,
    control_mode=ControlMode.REACTIVE,
    system_prompt="""You are a reflective thinking partner. Help the user explore their thoughts,
    clarify ideas, and gain new perspectives. Ask thoughtful questions but let the user
    drive the conversation. Never lecture or provide unsolicited advice.""",
    default_config=SessionConfig(
        time_limit_seconds=None,
        allow_skip=True,
        allow_back=True,
        allow_concurrent_sessions=True,
    ),
)
```

### 8.2 LearningSession (Proactive)

```python
LEARNING_SESSION_CONFIG = SessionTypeConfig(
    session_type=SessionType.LEARNING,
    control_mode=ControlMode.PROACTIVE,
    system_prompt="""You are an adaptive tutor. Guide the learner through concepts using a mix of:
    - Explanations (free text from you)
    - Questions (use present_choices or request_free_text)
    - Practice exercises (use appropriate widgets)

    Start by assessing their current knowledge, then adapt difficulty based on responses.
    Provide encouragement and constructive feedback. Allow free-text discussion when beneficial.""",
    default_config=SessionConfig(
        time_limit_seconds=3600,  # 1 hour
        allow_skip=True,
        allow_back=False,
        allow_concurrent_sessions=True,
    ),
)
```

### 8.3 ValidationSession (Proactive)

```python
VALIDATION_SESSION_CONFIG = SessionTypeConfig(
    session_type=SessionType.VALIDATION,
    control_mode=ControlMode.PROACTIVE,
    system_prompt="""You are an assessment proctor. Administer the assessment strictly:
    - Present questions using ONLY structured widgets (present_choices, present_drag_drop, etc.)
    - NEVER accept free-text answers during assessment items
    - Do not provide hints or feedback until assessment is complete
    - Track time limits strictly
    - Record all responses for scoring

    If user attempts to bypass structured input, politely redirect to the current question.""",
    default_config=SessionConfig(
        time_limit_seconds=1800,  # 30 minutes
        item_time_limit_seconds=120,  # 2 minutes per item
        allow_skip=False,
        allow_back=False,
        allow_concurrent_sessions=False,  # One assessment at a time
    ),
)
```

---

## 9. Frontend Integration

### 9.1 Stream Handler Updates

```javascript
// stream-manager.js additions

#setupEventListeners() {
    // ... existing handlers ...

    // New: Client action handling
    this.#eventSource.addEventListener('client_action', (e) => {
        const data = JSON.parse(e.data);
        this.#emit('client_action', data);
    });

    // New: State change
    this.#eventSource.addEventListener('state_change', (e) => {
        const data = JSON.parse(e.data);
        this.#emit('state_change', data);
    });

    // New: Session events
    this.#eventSource.addEventListener('session_completed', (e) => {
        const data = JSON.parse(e.data);
        this.#emit('session_completed', data);
    });
}
```

### 9.2 Client Action Renderer

```javascript
// components/client-action-renderer.js

class ClientActionRenderer extends AXComponent {
    static WIDGET_MAP = {
        'multiple_choice': 'ax-multiple-choice',
        'multi_select': 'ax-multi-select',
        'free_text': 'ax-free-text-prompt',
        'rating_scale': 'ax-rating-scale',
        'confirmation': 'ax-confirmation',
        'drag_drop_simple': 'ax-drag-drop-simple',
        'drag_drop_category': 'ax-drag-drop-category',
        'hot_spot': 'ax-hot-spot',
        'graphical_builder': 'ax-graphical-builder',
        'code_editor': 'ax-code-editor',
        'iframe_form': 'ax-iframe-form',
        'file_upload': 'ax-file-upload',
    };

    renderAction(actionPayload) {
        const { tool_call_id, component, props, lock_input } = actionPayload;
        const tagName = ClientActionRenderer.WIDGET_MAP[component];

        if (!tagName) {
            console.error(`Unknown widget: ${component}`);
            return;
        }

        // Clear previous
        this.shadowRoot.innerHTML = '';

        // Create widget
        const widget = document.createElement(tagName);
        widget.dataset.toolCallId = tool_call_id;

        // Apply props
        for (const [key, value] of Object.entries(props)) {
            if (typeof value === 'object') {
                widget.setAttribute(key, JSON.stringify(value));
            } else {
                widget.setAttribute(key, value);
            }
        }

        // Listen for response
        widget.addEventListener('ax-response', (e) => {
            this.#submitResponse(tool_call_id, e.detail);
        });

        this.shadowRoot.appendChild(widget);

        // Lock input if requested
        if (lock_input) {
            this.emit('lock-chat-input', { locked: true, reason: 'awaiting_widget' });
        }
    }

    async #submitResponse(toolCallId, response) {
        try {
            const result = await api.submitSessionResponse(
                this.dataset.sessionId,
                toolCallId,
                response
            );
            this.clear();
        } catch (error) {
            this.emit('response-error', { error: error.message });
        }
    }

    clear() {
        this.shadowRoot.innerHTML = '';
        this.emit('lock-chat-input', { locked: false });
    }
}
```

---

## 10. Implementation Phases

### Phase 1: Core Infrastructure (2-3 weeks)

**Domain:**

- [ ] Create `Session` aggregate with events
- [ ] Create value objects: `SessionItem`, `ClientAction`, `UiState`, `ClientResponse`
- [ ] Create enums: `SessionType`, `ControlMode`, `SessionStatus`
- [ ] Session repository interface and Motor implementation

**Application:**

- [ ] `CreateSessionCommand` + handler
- [ ] `SubmitClientResponseCommand` + handler
- [ ] `GetSessionQuery`, `GetUserSessionsQuery` + handlers
- [ ] `SessionService` for orchestration

**Infrastructure:**

- [ ] Session state persistence (MongoDB)
- [ ] Session event stream (separate from Conversation)

### Phase 2: Client Tool System (2 weeks)

**Agent-Host:**

- [ ] `ClientToolDefinition` dataclass
- [ ] `CLIENT_TOOLS` registry with all widget definitions
- [ ] `is_client_tool()` and `get_client_tool_manifest()` helpers
- [ ] Response validation logic

**Integration:**

- [ ] Tool interception in agent execution flow
- [ ] `CLIENT_ACTION` SSE event emission
- [ ] Session state transitions on client tool call

### Phase 3: Proactive Agent (2 weeks)

**Agent:**

- [ ] `ProactiveAgent` class extending `Agent`
- [ ] `start_session()` method
- [ ] `resume_with_response()` method
- [ ] Proactive loop with suspension/resumption
- [ ] New `AgentEventType` values

**API:**

- [ ] `SessionController` with all endpoints
- [ ] SSE streaming for sessions
- [ ] State restoration endpoint

### Phase 4: Frontend Widgets (3-4 weeks)

**Core:**

- [ ] Update `stream-handler.js` for new events
- [ ] `ax-client-action-renderer` component
- [ ] Chat input lock/unlock mechanism
- [ ] State restoration on reconnect

**Widgets (prioritized):**

1. [ ] `ax-multiple-choice` (single select)
2. [ ] `ax-multi-select`
3. [ ] `ax-free-text-prompt`
4. [ ] `ax-confirmation`
5. [ ] `ax-rating-scale`
6. [ ] `ax-drag-drop-simple`
7. [ ] `ax-drag-drop-category`
8. [ ] `ax-hot-spot`
9. [ ] `ax-code-editor`
10. [ ] `ax-graphical-builder`
11. [ ] `ax-iframe-form`
12. [ ] `ax-file-upload`

### Phase 5: Session Types & Polish (1-2 weeks)

**Configuration:**

- [ ] `ThoughtSession` config (reactive)
- [ ] `LearningSession` config (proactive)
- [ ] `ValidationSession` config (proactive)
- [ ] System prompt templates

**Testing:**

- [ ] Unit tests for Session aggregate
- [ ] Integration tests for proactive flow
- [ ] E2E tests for widget interactions

---

## 11. Risks & Mitigations

| Risk | Severity | Probability | Mitigation |
|------|----------|-------------|------------|
| State restoration edge cases | Medium | Medium | Comprehensive test coverage, graceful degradation |
| Long-running sessions expiring | Medium | Low | Configurable TTL, "resume" capability, warnings |
| Widget response validation failures | Low | Low | Graceful handling, let LLM interpret invalid responses |
| LLM calling wrong tool type | Low | Low | Clear system prompts, tool descriptions |
| SSE disconnection mid-action | Medium | Medium | Reconnect protocol, state endpoint |
| Complex widget state serialization | Medium | Medium | JSON-serializable state, partial state restoration |

---

## 12. Success Criteria

1. **Functional:** Proactive agent can drive a multi-turn interaction using widgets
2. **Resilient:** User can refresh browser and resume exactly where they left off
3. **Extensible:** New widgets can be added without modifying core agent logic
4. **Observable:** All interactions are logged in Session event stream
5. **Performant:** Widget rendering < 100ms, state restoration < 500ms

---

## Appendix A: Comparison with Original Draft

| Original Draft | This Spec | Rationale |
|----------------|-----------|-----------|
| `ToolDefinition.execution_context` in tools-provider | `CLIENT_TOOLS` hardcoded in agent-host | Client tools are agent-host's domain, not tools-provider's |
| `Conversation.state` for pending action | Separate `Session` aggregate | Clean separation, own event stream |
| `ask_multiple_choice` tool name | `present_choices` | Clearer intent, consistent naming |
| Question Bank in tools-provider | Upstream service via tools-provider | Separation of concerns |
| Single "Proctor" use case | Generalized `SessionType` enum | Extensible to surveys, workflows, etc. |

---

## Appendix B: Widget Response Schemas

```typescript
// TypeScript interfaces for documentation

interface MultipleChoiceResponse {
    selection: string;
    index: number;
}

interface MultiSelectResponse {
    selections: string[];
    indices: number[];
}

interface FreeTextResponse {
    text: string;
}

interface RatingScaleResponse {
    rating: number;
}

interface ConfirmationResponse {
    confirmed: boolean;
}

interface DragDropSimpleResponse {
    placements: Record<string, string>;  // zone_id -> item_id
}

interface DragDropCategoryResponse {
    categorizations: Record<string, string[]>;  // category_id -> item_ids
}

interface HotSpotResponse {
    clicks: Array<{x: number, y: number}> | string[];  // coordinates or region_ids
}

interface GraphicalBuilderResponse {
    diagram: {
        nodes: Array<{id: string, type: string, x: number, y: number, data?: any}>;
        connections: Array<{from: string, to: string, type?: string}>;
    };
}

interface CodeEditorResponse {
    code: string;
}

interface IframeFormResponse {
    form_data: Record<string, any>;
}

interface FileUploadResponse {
    files: Array<{
        filename: string;
        url: string;
        size: number;
        mime: string;
    }>;
}
```

---

_End of Specification_
