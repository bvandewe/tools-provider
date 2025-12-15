# Agent Aggregate Implementation Plan

**Version:** 1.1.0
**Status:** `APPROVED`
**Date:** December 15, 2025
**Primary Reference:** [Agent Aggregate Design](../architecture/agent-aggregate-design.md)

---

## 1. Executive Summary

This document provides the detailed implementation plan for refactoring the agent-host application to use **Agent as a first-class Domain Aggregate** with **Session demoted to a value object**.

### Scope

- **In Scope**: Mono-dimensional Agent aggregate with event sourcing
- **Out of Scope**: Polyglot multi-dimensional aspects (Phase 2+)

### Timeline Estimate

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1: Foundation | 3-4 days | None |
| Phase 2: Domain Model | 4-5 days | Phase 1 |
| Phase 3: Application Layer | 3-4 days | Phase 2 |
| Phase 4: API Layer | 2-3 days | Phase 3 |
| Phase 5: Migration | 2-3 days | Phase 4 |
| Phase 6: Testing & Cleanup | 2-3 days | Phase 5 |
| **Total** | **16-22 days** | |

---

## 2. Phase 1: Foundation (Days 1-4)

### 2.1 Objectives

- Create new domain models (value objects)
- Define domain events
- Set up new file structure

### 2.2 Tasks

#### Task 1.1: Create Agent Enumerations

**File:** `src/agent-host/domain/enums/__init__.py` (new)
**File:** `src/agent-host/domain/enums/agent_type.py` (new)
**File:** `src/agent-host/domain/enums/agent_status.py` (new)
**File:** `src/agent-host/domain/enums/assignment_role.py` (new)
**File:** `src/agent-host/domain/enums/session_status.py` (move from models)

```python
# domain/enums/agent_type.py
from enum import Enum

class AgentType(str, Enum):
    TUTOR = "tutor"
    THOUGHT = "thought"
    EVALUATOR = "evaluator"
    COACH = "coach"           # Future
    CONNECTOR = "connector"   # Future
    WELLNESS = "wellness"     # Future
    PLANNER = "planner"       # Future
    RESEARCHER = "researcher" # Future


# domain/enums/agent_status.py
class AgentStatus(str, Enum):
    ACTIVE = "active"       # Normal operating state
    ARCHIVED = "archived"   # Soft-deleted, preserved for audit


# domain/enums/assignment_role.py
class AssignmentRole(str, Enum):
    PRIMARY = "primary"     # Owner - full control
    SHARED = "shared"       # Team member - can interact
    MENTEE = "mentee"       # Being mentored - limited write
    OBSERVER = "observer"   # Read-only access
```

**Acceptance Criteria:**

- [ ] AgentType enum created with core types
- [ ] AgentStatus enum created (active/archived)
- [ ] AssignmentRole enum created for multi-user (Phase 2+)
- [ ] SessionStatus moved to enums directory
- [ ] All existing imports updated

---

#### Task 1.2: Create ExecutionState Value Object

**File:** `src/agent-host/domain/models/execution_state.py` (new)

**Implementation:**

```python
@dataclass
class LlmMessageSnapshot:
    role: str
    content: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    tool_call_id: str | None = None
    name: str | None = None

    def to_dict(self) -> dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: dict) -> "LlmMessageSnapshot": ...


@dataclass
class PendingToolCall:
    call_id: str
    tool_name: str
    arguments: dict[str, Any]

    def to_dict(self) -> dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: dict) -> "PendingToolCall": ...


@dataclass
class ExecutionState:
    conversation_snapshot: list[LlmMessageSnapshot]
    iteration: int = 0
    tool_calls_made: int = 0
    pending_tool_call: PendingToolCall | None = None
    started_at_ms: float = 0.0
    suspended_at_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: dict) -> "ExecutionState": ...
```

**Acceptance Criteria:**

- [ ] ExecutionState serializes/deserializes correctly
- [ ] Unit tests for round-trip serialization
- [ ] LlmMessageSnapshot handles all LLM message types

---

#### Task 1.3: Refactor Session to Value Object

**File:** `src/agent-host/domain/models/session.py` (new - move from entities)

**Changes:**

- Remove AggregateRoot inheritance
- Remove event registration
- Add `to_dict()` / `from_dict()` methods
- Keep all session-related logic (items, pending_action, status)

**Acceptance Criteria:**

- [ ] Session is a plain dataclass
- [ ] All session functionality preserved
- [ ] No aggregate-related code

---

#### Task 1.4: Create Agent Domain Events

**File:** `src/agent-host/domain/events/agent.py` (new)

**Events to Create:**

```python
@cloudevent("agent.created.v1")
class AgentCreatedDomainEvent(DomainEvent[str]):
    owner_user_id: str  # UUID-based identity uses owner mapping
    agent_type: str
    name: str
    created_at: datetime

@cloudevent("agent.archived.v1")
class AgentArchivedDomainEvent(DomainEvent[str]):
    reason: str
    archived_at: datetime

@cloudevent("agent.user.assigned.v1")
class UserAssignedToAgentDomainEvent(DomainEvent[str]):
    user_id: str
    role: str  # AssignmentRole value
    assigned_by: str
    assigned_at: datetime

@cloudevent("agent.preferences.updated.v1")
class AgentPreferencesUpdatedDomainEvent(DomainEvent[str]): ...

@cloudevent("agent.session.started.v1")
class SessionStartedDomainEvent(DomainEvent[str]): ...

@cloudevent("agent.execution.suspended.v1")
class ExecutionSuspendedDomainEvent(DomainEvent[str]): ...

@cloudevent("agent.execution.resumed.v1")
class ExecutionResumedDomainEvent(DomainEvent[str]): ...

@cloudevent("agent.client.action.requested.v1")
class ClientActionRequestedDomainEvent(DomainEvent[str]): ...

@cloudevent("agent.client.response.received.v1")
class ClientResponseReceivedDomainEvent(DomainEvent[str]): ...

@cloudevent("agent.session.completed.v1")
class SessionCompletedDomainEvent(DomainEvent[str]): ...

@cloudevent("agent.session.terminated.v1")
class SessionTerminatedDomainEvent(DomainEvent[str]): ...
```

**Acceptance Criteria:**

- [ ] All 11 events defined with correct types
- [ ] CloudEvent decorators applied
- [ ] Events match design document v1.1.0
- [ ] AgentCreatedEvent uses owner_user_id (not user_id)
- [ ] AgentArchivedEvent included for reset flow
- [ ] UserAssignedToAgentEvent included for multi-user

---

### 2.3 Phase 1 Deliverables

| Artifact | Location |
|----------|----------|
| AgentType enum | `domain/enums/agent_type.py` |
| AgentStatus enum | `domain/enums/agent_status.py` |
| AssignmentRole enum | `domain/enums/assignment_role.py` |
| SessionStatus enum | `domain/enums/session_status.py` |
| ExecutionState VO | `domain/models/execution_state.py` |
| AgentAssignment VO | `domain/models/agent_assignment.py` |
| Session VO | `domain/models/session.py` |
| Agent events (11) | `domain/events/agent.py` |
| Unit tests | `tests/unit/domain/` |

---

## 3. Phase 2: Domain Model (Days 5-9)

### 3.1 Objectives

- Implement Agent aggregate root with UUID-based identity
- Create AgentState with event handlers
- Implement all domain commands including archive() and assign_user()

### 3.2 Tasks

#### Task 2.1: Create AgentState Class

**File:** `src/agent-host/domain/entities/agent.py` (new)

**Implementation:**

```python
@map_to(AgentDto)
class AgentState(AggregateState[str]):
    # Identity (UUID-based)
    id: str                    # UUID, not deterministic
    owner_user_id: str         # User who created this agent
    agent_type: str
    status: str                # AgentStatus value (active/archived)

    # User Assignments (for multi-user access)
    assignments: list[dict[str, Any]]  # List of AgentAssignment

    # Configuration
    name: str
    system_prompt_override: str | None
    preferences: dict[str, Any]

    # Metrics
    total_sessions: int
    total_interactions: int
    successful_completions: int

    # Active Session (value object as dict)
    active_session: dict[str, Any] | None

    # Execution State (for suspend/resume)
    execution_state: dict[str, Any] | None

    # Session History
    session_history: list[dict[str, Any]]
    max_history_size: int

    # Archive info
    archived_at: datetime | None
    archive_reason: str | None

    # Audit
    created_at: datetime
    updated_at: datetime
    last_interaction_at: datetime | None

    # Event handlers for all 11 events
    @dispatch(AgentCreatedDomainEvent)
    def on(self, event: AgentCreatedDomainEvent) -> None: ...

    @dispatch(AgentArchivedDomainEvent)
    def on(self, event: AgentArchivedDomainEvent) -> None: ...

    @dispatch(UserAssignedToAgentDomainEvent)
    def on(self, event: UserAssignedToAgentDomainEvent) -> None: ...
    # ... (11 handlers total)
```

**Acceptance Criteria:**

- [ ] All 11 event handlers implemented
- [ ] State transitions match design v1.1.0
- [ ] UUID-based identity (not deterministic)
- [ ] owner_user_id field for user mapping
- [ ] assignments array for multi-user support
- [ ] Session history archival works correctly

---

#### Task 2.2: Create Agent Aggregate Root

**File:** `src/agent-host/domain/entities/agent.py` (continued)

**Implementation:**

```python
class Agent(AggregateRoot[AgentState, str]):
    def __init__(self, owner_user_id: str, agent_type: AgentType, ...):
        # Generate UUID-based ID (not deterministic)
        aggregate_id = agent_id or str(uuid4())
        ...

    # Queries
    def has_active_session(self) -> bool: ...
    def get_active_session(self) -> Session | None: ...
    def get_execution_state(self) -> ExecutionState | None: ...
    def is_suspended(self) -> bool: ...
    def is_archived(self) -> bool: ...
    def is_user_assigned(self, user_id: str) -> bool: ...
    def get_user_role(self, user_id: str) -> str | None: ...

    # Commands
    def update_preferences(self, preferences: dict): ...
    def start_session(self, conversation_id: str, session_type: str) -> Session: ...
    def suspend_execution(self, state: ExecutionState, action: ClientAction): ...
    def resume_execution(self, response: ClientResponse) -> ExecutionState: ...
    def request_client_action(self, action: ClientAction): ...
    def receive_client_response(self, response: ClientResponse, item: dict | None): ...
    def complete_session(self, summary: dict | None): ...
    def terminate_session(self, reason: str): ...
    def archive(self, reason: str): ...           # NEW: For reset flow
    def assign_user(self, user_id: str, role: str, assigned_by: str): ...  # NEW: Multi-user
```

**Acceptance Criteria:**

- [ ] All domain invariants enforced
- [ ] DomainError raised for violations
- [ ] ID generation uses UUID (not deterministic)
- [ ] archive() terminates active session first or raises error
- [ ] assign_user() validates role and checks duplicates

---

#### Task 2.3: Create Agent DTO

**File:** `src/agent-host/integration/models/agent_dto.py` (new)

**Implementation:**

```python
@queryable
@dataclass
class AgentDto:
    id: str
    owner_user_id: str          # Changed from user_id
    agent_type: str
    status: str                 # NEW: active/archived
    name: str
    preferences: dict[str, Any]
    assignments: list[dict]     # NEW: User assignments
    total_sessions: int
    total_interactions: int
    successful_completions: int
    has_active_session: bool
    active_session_id: str | None
    created_at: datetime
    updated_at: datetime
    last_interaction_at: datetime | None
```

**Acceptance Criteria:**

- [ ] DTO decorated with @queryable
- [ ] @map_to decorator on AgentState references this DTO
- [ ] All fields needed for API response

---

#### Task 2.4: Write Domain Unit Tests

**File:** `src/agent-host/tests/unit/domain/test_agent_aggregate.py` (new)

**Test Cases:**

```python
class TestAgentAggregate:
    def test_create_agent_generates_deterministic_id(self): ...
    def test_start_session_when_idle_succeeds(self): ...
    def test_start_session_when_active_raises_error(self): ...
    def test_suspend_execution_persists_state(self): ...
    def test_resume_execution_returns_saved_state(self): ...
    def test_resume_with_wrong_tool_call_id_raises_error(self): ...
    def test_complete_session_archives_to_history(self): ...
    def test_session_history_maintains_max_size(self): ...
    def test_terminate_session_clears_execution_state(self): ...
```

**Acceptance Criteria:**

- [ ] 100% coverage of Agent aggregate commands
- [ ] Invariant violations tested
- [ ] Event emission verified

---

### 3.3 Phase 2 Deliverables

| Artifact | Location |
|----------|----------|
| Agent aggregate | `domain/entities/agent.py` |
| AgentDto | `integration/models/agent_dto.py` |
| Domain tests | `tests/unit/domain/test_agent_aggregate.py` |

---

## 4. Phase 3: Application Layer (Days 10-13)

### 4.1 Objectives

- Create CQRS commands for Agent operations
- Refactor AgentExecutor to be stateless
- Create projection handlers

### 4.2 Tasks

#### Task 3.1: Create Agent Commands

**Directory:** `src/agent-host/application/commands/`

| File | Command | Handler |
|------|---------|---------|
| `get_or_create_agent_command.py` | GetOrCreateAgentCommand | Returns existing or creates new |
| `start_agent_session_command.py` | StartAgentSessionCommand | Creates conversation, starts session |
| `suspend_agent_execution_command.py` | SuspendAgentExecutionCommand | Persists execution state |
| `resume_agent_execution_command.py` | ResumeAgentExecutionCommand | Loads state, validates response |
| `submit_agent_response_command.py` | SubmitAgentResponseCommand | Records client response |
| `complete_agent_session_command.py` | CompleteAgentSessionCommand | Finalizes session |
| `terminate_agent_session_command.py` | TerminateAgentSessionCommand | Ends session early |

**Example: StartAgentSessionCommand**

```python
@dataclass
class StartAgentSessionCommand(Command[OperationResult[SessionDto]]):
    user_id: str
    agent_type: AgentType
    system_prompt: str | None = None
    config: dict[str, Any] | None = None
    model_id: str | None = None


class StartAgentSessionCommandHandler(
    CommandHandlerBase,
    CommandHandler[StartAgentSessionCommand, OperationResult[SessionDto]],
):
    def __init__(
        self,
        mediator: Mediator,
        mapper: Mapper,
        cloud_event_bus: CloudEventBus,
        cloud_event_publishing_options: CloudEventPublishingOptions,
        agent_repository: Repository[Agent, str],
        conversation_repository: Repository[Conversation, str],
    ):
        ...

    async def handle_async(self, command: StartAgentSessionCommand) -> OperationResult[SessionDto]:
        # 1. Get or create agent
        agent_id = f"{command.agent_type.value}-{command.user_id}"
        agent = await self.agent_repository.get_async(agent_id)

        if agent is None:
            agent = Agent(
                user_id=command.user_id,
                agent_type=command.agent_type,
            )

        # 2. Create conversation
        conversation = Conversation(
            user_id=command.user_id,
            title=f"{command.agent_type.value.title()} Session",
            system_prompt=command.system_prompt,
        )
        await self.conversation_repository.add_async(conversation)

        # 3. Start session
        session = agent.start_session(
            conversation_id=conversation.id(),
            session_type=command.agent_type.value,
        )

        # 4. Persist
        if agent.state.total_sessions == 1:
            await self.agent_repository.add_async(agent)
        else:
            await self.agent_repository.update_async(agent)

        return self.ok(SessionDto.from_session(session))
```

**Acceptance Criteria:**

- [ ] All 7 commands implemented
- [ ] Commands use agent repository
- [ ] Error handling with OperationResult

---

#### Task 3.2: Refactor AgentExecutor to Stateless

**File:** `src/agent-host/application/agents/proactive_agent.py` (modify)

**Changes:**

1. Remove `_suspended_state` instance variable
2. Remove `_session_context` instance variable
3. Accept Agent aggregate as parameter
4. Read/write state through aggregate methods

**Before:**

```python
class ProactiveAgent(Agent):
    def __init__(self, llm_provider, config):
        self._suspended_state: SuspendedState | None = None
        self._session_context: ProactiveSessionContext | None = None
```

**After:**

```python
class ProactiveAgentExecutor:
    """Stateless executor for proactive agent logic."""

    def __init__(self, llm_provider: LlmProvider, config: AgentConfig):
        self._llm = llm_provider
        self._config = config
        # NO instance state

    async def start_session(
        self,
        agent: AgentAggregate,
        context: ProactiveSessionContext,
    ) -> AsyncIterator[AgentEvent]:
        """Execute session, reading/writing state from agent aggregate."""
        ...

    async def resume_with_response(
        self,
        agent: AgentAggregate,
        response: ClientResponse,
    ) -> AsyncIterator[AgentEvent]:
        """Resume from agent's persisted execution state."""
        execution_state = agent.get_execution_state()
        if execution_state is None:
            raise AgentError("No execution state to resume from")
        ...
```

**Acceptance Criteria:**

- [ ] No instance variables for state
- [ ] All state read from Agent aggregate
- [ ] Suspension writes to Agent aggregate

---

#### Task 3.3: Create Agent Projection Handlers

**File:** `src/agent-host/application/events/agent_projection_handlers.py` (new)

**Handlers:**

```python
class AgentCreatedProjectionHandler(DomainEventHandler[AgentCreatedDomainEvent]):
    """Projects agent creation to MongoDB."""

    async def handle_async(self, event: AgentCreatedDomainEvent) -> None:
        dto = AgentDto(
            id=event.aggregate_id,
            user_id=event.user_id,
            agent_type=event.agent_type,
            name=event.name,
            # ... defaults
        )
        await self._repository.add_async(dto)


class SessionStartedProjectionHandler(DomainEventHandler[SessionStartedDomainEvent]):
    """Updates agent read model when session starts."""

    async def handle_async(self, event: SessionStartedDomainEvent) -> None:
        agent = await self._repository.get_async(event.aggregate_id)
        if agent:
            agent.has_active_session = True
            agent.active_session_id = event.session_id
            await self._repository.update_async(agent)


# Similar handlers for other events...
```

**Acceptance Criteria:**

- [ ] Handlers for all 9 events
- [ ] Read model stays consistent
- [ ] Idempotent handling

---

#### Task 3.4: Create Agent Queries

**Directory:** `src/agent-host/application/queries/`

| File | Query | Purpose |
|------|-------|---------|
| `get_agent_query.py` | GetAgentQuery | Get agent by ID |
| `get_user_agents_query.py` | GetUserAgentsQuery | List user's agents |
| `get_agent_session_query.py` | GetAgentSessionQuery | Get active session |
| `get_agent_history_query.py` | GetAgentHistoryQuery | Get session history |

**Acceptance Criteria:**

- [ ] All queries implemented
- [ ] Read from MongoDB (read model)
- [ ] Proper authorization checks

---

### 4.3 Phase 3 Deliverables

| Artifact | Location |
|----------|----------|
| Agent commands (7) | `application/commands/` |
| Agent queries (4) | `application/queries/` |
| Projection handlers | `application/events/agent_projection_handlers.py` |
| Refactored executor | `application/agents/proactive_agent.py` |
| Unit tests | `tests/unit/application/` |

---

## 5. Phase 4: API Layer (Days 14-16)

### 5.1 Objectives

- Create new AgentController
- Implement SSE streaming for agent
- Add backward-compatible session endpoints

### 5.2 Tasks

#### Task 4.1: Create AgentController

**File:** `src/agent-host/api/controllers/agent_controller.py` (new)

**Endpoints:**

```python
class AgentController(ControllerBase):

    @get("/")
    async def list_agents(self, user: dict = Depends(get_current_user)) -> list[AgentSummaryResponse]:
        """List all agents for current user."""
        ...

    @get("/{agent_id}")
    async def get_agent(self, agent_id: str, user: dict = Depends(get_current_user)) -> AgentDetailResponse:
        """Get agent details."""
        ...

    @post("/{agent_id}/sessions")
    async def start_session(
        self,
        agent_id: str,
        body: StartSessionRequest,
        user: dict = Depends(get_current_user),
    ) -> CreateSessionResponse:
        """Start a new session with the agent."""
        ...

    @get("/{agent_id}/sessions/current")
    async def get_current_session(self, agent_id: str, user: dict = Depends(get_current_user)) -> SessionDetailResponse:
        """Get the agent's current active session."""
        ...

    @post("/{agent_id}/respond")
    async def submit_response(
        self,
        agent_id: str,
        body: SubmitResponseRequest,
        user: dict = Depends(get_current_user),
    ) -> SessionDetailResponse:
        """Submit response to pending widget."""
        ...

    @delete("/{agent_id}/sessions/current")
    async def terminate_session(self, agent_id: str, user: dict = Depends(get_current_user)) -> SessionDetailResponse:
        """Terminate the current session."""
        ...

    @get("/{agent_id}/stream")
    async def stream_events(self, agent_id: str, user: dict = Depends(get_current_user)) -> StreamingResponse:
        """SSE stream for agent events."""
        ...

    @get("/{agent_id}/history")
    async def get_session_history(self, agent_id: str, user: dict = Depends(get_current_user)) -> list[SessionSummaryResponse]:
        """Get agent's session history."""
        ...
```

**Acceptance Criteria:**

- [ ] All 8 endpoints implemented
- [ ] Proper authentication
- [ ] OpenAPI documentation

---

#### Task 4.2: Update SessionController for Backward Compatibility

**File:** `src/agent-host/api/controllers/session_controller.py` (modify)

**Changes:**

- Route existing `/api/session/*` calls to new agent flow
- Create agent on-demand based on session_type
- Return responses in existing format

```python
@post("/")
async def create_session(self, body: CreateSessionRequest, user: dict = Depends(get_current_user)):
    """Backward-compatible session creation.

    DEPRECATED: Use POST /api/agents/{agent_type}/sessions instead.
    """
    # Map session_type to agent_type
    agent_type = self._map_session_type_to_agent_type(body.session_type)

    # Route to new agent flow
    command = StartAgentSessionCommand(
        user_id=user.get("sub"),
        agent_type=agent_type,
        system_prompt=body.system_prompt,
        config=body.config,
    )
    result = await self.mediator.execute_async(command)

    # Return in old format
    return CreateSessionResponse(
        session_id=result.data.session_id,
        conversation_id=result.data.conversation_id,
        status=result.data.status,
        control_mode=result.data.control_mode,
        stream_url=f"/api/session/{result.data.session_id}/stream",
    )
```

**Acceptance Criteria:**

- [ ] Existing endpoints still work
- [ ] Deprecation warnings logged
- [ ] No breaking changes for frontend

---

#### Task 4.3: Update main.py for DI Registration

**File:** `src/agent-host/main.py` (modify)

**Changes:**

```python
# Add Agent aggregate to DataAccessLayer
DataAccessLayer.WriteModel(
    Agent,
    AgentState,
    str,
    stream_name_resolver=lambda id: f"agent-{id}",
)

DataAccessLayer.ReadModel(
    AgentDto,
    str,
    MongoRepository[AgentDto, str],
)

# Register AgentController
app.register_controller(AgentController)

# Register projection handlers
mediator.register_handler(AgentCreatedProjectionHandler)
mediator.register_handler(SessionStartedProjectionHandler)
# ... etc
```

**Acceptance Criteria:**

- [ ] Agent aggregate registered for event sourcing
- [ ] AgentDto registered for MongoDB
- [ ] Controller registered
- [ ] All handlers registered

---

### 5.3 Phase 4 Deliverables

| Artifact | Location |
|----------|----------|
| AgentController | `api/controllers/agent_controller.py` |
| Updated SessionController | `api/controllers/session_controller.py` |
| Updated main.py | `main.py` |
| API tests | `tests/integration/api/` |

---

## 6. Phase 5: Migration (Days 17-19)

### 6.1 Objectives

- Migrate existing sessions to agent model
- Create migration scripts
- Validate data integrity

### 6.2 Tasks

#### Task 5.1: Create Migration Script

**File:** `scripts/migrate_sessions_to_agents.py` (new)

**Logic:**

```python
async def migrate_sessions_to_agents():
    """Migrate existing Session aggregates to Agent aggregates.

    For each unique (user_id, session_type) pair:
    1. Create Agent aggregate with deterministic ID
    2. Import completed sessions into session_history
    3. If active session exists, set as active_session
    """

    # 1. Read all sessions from EventStoreDB
    sessions = await read_all_session_streams()

    # 2. Group by (user_id, session_type)
    grouped = group_sessions_by_user_and_type(sessions)

    # 3. For each group, create Agent
    for (user_id, session_type), user_sessions in grouped.items():
        agent_type = map_session_type_to_agent_type(session_type)
        agent_id = f"{agent_type.value}-{user_id}"

        # Check if agent already exists
        existing = await agent_repo.get_async(agent_id)
        if existing:
            logger.info(f"Agent {agent_id} already exists, skipping")
            continue

        # Create agent with history
        agent = Agent(user_id=user_id, agent_type=agent_type)

        # Import sessions as history
        for session in sorted(user_sessions, key=lambda s: s.created_at):
            if session.status in [SessionStatus.COMPLETED, SessionStatus.TERMINATED]:
                agent.state.session_history.append(session.to_dict())
            elif session.status == SessionStatus.ACTIVE:
                agent.state.active_session = session.to_dict()

        await agent_repo.add_async(agent)
        logger.info(f"Migrated {len(user_sessions)} sessions to agent {agent_id}")
```

**Acceptance Criteria:**

- [ ] Script handles all edge cases
- [ ] Idempotent (can run multiple times)
- [ ] Progress logging
- [ ] Dry-run mode

---

#### Task 5.2: Create Data Validation Script

**File:** `scripts/validate_agent_migration.py` (new)

**Checks:**

- [ ] All users with sessions have agents
- [ ] Session history counts match
- [ ] Active sessions preserved
- [ ] No data loss

---

#### Task 5.3: Update Frontend

**Files:** `src/agent-host/ui/src/scripts/`

**Changes:**

1. Update API service to use new endpoints
2. Add agent_id to session context
3. Update SSE connection URL

**Priority:** Medium (can use backward-compatible endpoints initially)

---

### 6.3 Phase 5 Deliverables

| Artifact | Location |
|----------|----------|
| Migration script | `scripts/migrate_sessions_to_agents.py` |
| Validation script | `scripts/validate_agent_migration.py` |
| Frontend updates | `ui/src/scripts/services/api.js` |

---

## 7. Phase 6: Testing & Cleanup (Days 20-22)

### 7.1 Objectives

- Comprehensive integration testing
- Performance validation
- Remove deprecated code

### 7.2 Tasks

#### Task 6.1: Integration Tests

**File:** `src/agent-host/tests/integration/test_agent_lifecycle.py` (new)

**Test Scenarios:**

```python
@pytest.mark.integration
class TestAgentLifecycle:

    async def test_full_session_flow(self):
        """Test complete flow: create agent → start session → interact → complete."""
        ...

    async def test_crash_recovery(self):
        """Test that suspended state survives restart."""
        # 1. Start session
        # 2. Suspend (widget)
        # 3. Clear in-memory state (simulate restart)
        # 4. Reload agent from EventStoreDB
        # 5. Resume with response
        # 6. Verify continuation
        ...

    async def test_concurrent_session_rejected(self):
        """Test that starting second session fails."""
        ...

    async def test_cross_session_memory(self):
        """Test that agent remembers across sessions."""
        ...
```

---

#### Task 6.2: Performance Testing

**Metrics to Validate:**

- Agent aggregate load time < 100ms
- Session start time < 200ms
- Resume from suspension < 150ms
- SSE reconnection < 500ms

---

#### Task 6.3: Cleanup Deprecated Code

**Files to Remove (after migration complete):**

- `domain/entities/session.py` (aggregate version)
- Old session commands in `application/commands/`
- Old session queries in `application/queries/`

**Files to Mark Deprecated:**

- `api/controllers/session_controller.py` (keep for 1-2 releases)

---

### 7.3 Phase 6 Deliverables

| Artifact | Location |
|----------|----------|
| Integration tests | `tests/integration/` |
| Performance report | `docs/reports/agent-perf.md` |
| Deprecation notices | Various files |

---

## 8. Risk Mitigation

### 8.1 Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Event stream size growth | Medium | Medium | Max history size, archive old sessions |
| Migration data loss | Low | High | Dry-run mode, validation scripts |
| SSE reconnection issues | Medium | Medium | Client retry logic, state recovery |
| Performance degradation | Low | Medium | Caching, read model optimization |

### 8.2 Rollback Plan

Each phase includes a rollback checkpoint:

1. **Phase 1-2**: Delete new files, no production impact
2. **Phase 3**: Keep old commands, use feature flag
3. **Phase 4**: Keep old endpoints, gradual routing
4. **Phase 5**: Migration is additive, can coexist
5. **Phase 6**: Cleanup only after validation

---

## 9. Success Criteria

### 9.1 Functional

- [ ] Agent persists across sessions for same user
- [ ] Execution state survives server restart
- [ ] Widget interactions resume correctly
- [ ] Session history accessible
- [ ] Specialized agent types can be added

### 9.2 Non-Functional

- [ ] No performance regression (< 10% overhead)
- [ ] All existing tests pass
- [ ] API backward compatible
- [ ] Frontend works unchanged (initially)

---

## 10. Dependencies

### 10.1 External Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| neuroglia | >= 0.2.0 | AggregateRoot, event sourcing |
| EventStoreDB | >= 24.2 | Write model persistence |
| MongoDB | >= 7.0 | Read model projections |

### 10.2 Internal Dependencies

| Component | Dependency |
|-----------|------------|
| Agent aggregate | Conversation aggregate (ID reference) |
| AgentExecutor | Agent aggregate (state source) |
| AgentController | AgentCommands, AgentQueries |

---

## 11. Appendix: File Inventory

### 11.1 New Files

| Path | Type | Phase |
|------|------|-------|
| `domain/enums/__init__.py` | Package | 1 |
| `domain/enums/agent_type.py` | Enum | 1 |
| `domain/models/execution_state.py` | Value Object | 1 |
| `domain/models/session.py` | Value Object | 1 |
| `domain/events/agent.py` | Events | 1 |
| `domain/entities/agent.py` | Aggregate | 2 |
| `integration/models/agent_dto.py` | DTO | 2 |
| `application/commands/get_or_create_agent_command.py` | Command | 3 |
| `application/commands/start_agent_session_command.py` | Command | 3 |
| `application/commands/suspend_agent_execution_command.py` | Command | 3 |
| `application/commands/resume_agent_execution_command.py` | Command | 3 |
| `application/commands/submit_agent_response_command.py` | Command | 3 |
| `application/commands/complete_agent_session_command.py` | Command | 3 |
| `application/commands/terminate_agent_session_command.py` | Command | 3 |
| `application/queries/get_agent_query.py` | Query | 3 |
| `application/queries/get_user_agents_query.py` | Query | 3 |
| `application/queries/get_agent_session_query.py` | Query | 3 |
| `application/queries/get_agent_history_query.py` | Query | 3 |
| `application/events/agent_projection_handlers.py` | Handlers | 3 |
| `api/controllers/agent_controller.py` | Controller | 4 |
| `scripts/migrate_sessions_to_agents.py` | Script | 5 |
| `scripts/validate_agent_migration.py` | Script | 5 |
| `tests/unit/domain/test_agent_aggregate.py` | Test | 2 |
| `tests/integration/test_agent_lifecycle.py` | Test | 6 |

### 11.2 Modified Files

| Path | Changes | Phase |
|------|---------|-------|
| `domain/entities/__init__.py` | Add Agent export | 2 |
| `application/agents/proactive_agent.py` | Stateless refactor | 3 |
| `application/agents/agent_factory.py` | Use Agent aggregate | 3 |
| `api/controllers/session_controller.py` | Backward compat | 4 |
| `main.py` | DI registration | 4 |
| `ui/src/scripts/services/api.js` | New endpoints | 5 |

### 11.3 Deprecated Files (Phase 6)

| Path | Replacement |
|------|-------------|
| `domain/entities/session.py` (aggregate) | `domain/models/session.py` (VO) |
| `application/commands/create_session_command.py` | `start_agent_session_command.py` |
| `application/commands/submit_client_response_command.py` | `submit_agent_response_command.py` |
| `application/commands/terminate_session_command.py` | `terminate_agent_session_command.py` |

---

## 12. References

- [Agent Aggregate Design](../architecture/agent-aggregate-design.md) - Architecture document v1.1.0
- [Polyglot Entity Model](../architecture/polyglot-entity-model.md) - Theoretical framework
- [Event Sourcing Architecture](../architecture/event-sourcing.md) - Implementation patterns
- [Agent Host LLD](./agent-host-lld.md) - Current implementation reference

---

## 13. Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-15 | Initial implementation plan |
| 1.1.0 | 2025-12-15 | Updated for UUID-based identity, AgentStatus, AssignmentRole, archive(), assign_user(), multi-user support |
