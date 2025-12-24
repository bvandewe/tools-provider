# Copilot Instructions for tools-provider

## Project Overview

A Python microservice built with **Neuroglia Framework** on FastAPI, implementing **CQRS** (Command Query Responsibility Segregation) with **Hybrid Persistence** (State-Based or Event-Sourced). The service manages MCP tools from OpenAPI services, featuring dual OAuth2/JWT authentication via Keycloak.

## Repository Structure

This repository contains **three applications** under the `src/` directory:

```
src/
├── tools-provider/   # Main MCP Tools Provider (CQRS/Event Sourcing)
│   ├── tests/        # All tests for tools-provider
│   ├── pyproject.toml
│   ├── pytest.ini
│   └── Makefile
├── agent-host/       # Chat interface for AI agents
│   ├── pyproject.toml
│   └── Makefile
└── upstream-sample/  # Sample Pizzeria backend (OpenAPI service)
    └── pyproject.toml
```

### Multi-App Python Setup

Each app is **self-contained** with its own virtual environment, dependencies, and Makefile:

| App | Location | Python | .venv | Tests |
|-----|----------|--------|-------|-------|
| tools-provider | `src/tools-provider/` | 3.12 | `src/tools-provider/.venv` | `src/tools-provider/tests/` |
| agent-host | `src/agent-host/` | 3.12 | `src/agent-host/.venv` | N/A |
| upstream-sample | `src/upstream-sample/` | 3.12 | (uses pip) | N/A |

**Root Makefile** delegates to app-specific Makefiles for most commands.

## Architecture

### Layer Separation (Clean Architecture) - tools-provider

```
src/tools-provider/
├── domain/          # Pure domain model (entities, events, repository interfaces)
├── application/     # CQRS handlers (commands/, queries/), settings, mapping
├── api/             # REST controllers, FastAPI dependencies, auth services
├── integration/     # DTOs and concrete repository implementations
├── infrastructure/  # Session stores, external service adapters
├── ui/              # Frontend source (Parcel-built)
└── static/          # Built frontend assets
```

### Key Patterns

1. **Aggregate + AggregateState Pattern**: Domain entities use `AggregateRoot[TState, TKey]` with state encapsulated in `AggregateState`. See `src/tools-provider/domain/entities/task.py`:
   - State changes emit `DomainEvent` instances via `@dispatch` handlers
   - Events are decorated with `@cloudevent("event.type.v1")` for CloudEvent publishing

2. **CQRS with Mediator**: Commands/Queries flow through `Mediator`. Handlers extend `CommandHandler[TCommand, TResult]` or `QueryHandler[TQuery, TResult]`:

   ```python
   # src/tools-provider/application/commands/create_task_command.py
   class CreateTaskCommandHandler(CommandHandlerBase, CommandHandler[CreateTaskCommand, OperationResult[TaskDto]]):
   ```

3. **Hybrid Persistence Strategy**: Choose based on audit/compliance requirements:

   | Pattern | Repository | When to Use |
   |---------|------------|-------------|
   | **Event-Sourced** | `EventSourcingRepository` | Audit-critical (ExamBlueprint, Certification) |
   | **State-Based** | `MotorRepository` | Frequent updates, no audit trail needed |

   - **State-Based (MotorRepository)**: Persists `AggregateRoot.state` to MongoDB, uses `state_version` for optimistic concurrency
   - **Event-Sourced**: Persists events to EventStoreDB, rebuilds state on load
   - **Both patterns emit CloudEvents**: DomainEvents are published for external observability but NOT persisted for State-Based aggregates

   ```python
   # State-Based: MotorRepository persists state only
   # Events are published as CloudEvents but NOT stored in EventStoreDB
   MotorRepository.configure(
       builder,
       entity_type=Conversation,
       key_type=str,
       database_name="agent_host",
       collection_name="conversations"
   )
   ```

4. **Dual Authentication**: Both session cookies (OAuth2 BFF) and JWT Bearer tokens. See `src/tools-provider/api/dependencies.py` for `get_current_user()` resolution.

## Critical Developer Workflows

### Setup & Run

```bash
# From root - orchestration commands
make setup              # Setup all apps (tools-provider + agent-host)
make up                 # Start Docker services (Keycloak, EventStoreDB, MongoDB, Redis)
make run                # Run tools-provider locally (port 8000)
make run-agent          # Run agent-host locally (port 8001)

# From app directory - app-specific commands
cd src/tools-provider
make setup              # Install Poetry deps + Node deps, build UI
make run                # Run with hot-reload
make run-debug          # Run with LOG_LEVEL=DEBUG
```

### Testing

```bash
# From root (delegates to tools-provider)
make test               # Run all tests
make test-domain        # Domain layer only
make test-application   # CQRS handlers
make test-cov           # With coverage report

# From tools-provider directory
cd src/tools-provider
make test               # Run all tests
make test-unit          # Unit tests only
```

Tests use markers: `@pytest.mark.unit`, `@pytest.mark.command`, `@pytest.mark.query`, `@pytest.mark.asyncio`

### Infrastructure URLs (Docker)

| Service | URL | Credentials |
|---------|-----|-------------|
| App | http://localhost:8040 | - |
| API Docs | http://localhost:8040/api/docs | - |
| Keycloak | http://localhost:8041 | admin/admin |
| EventStoreDB | http://localhost:2113 | admin/changeit |
| Mongo Express | http://localhost:8043 | admin@admin.com/admin |

## Project Conventions

### File Naming & Structure

- **Commands**: `src/tools-provider/application/commands/{action}_{entity}_command.py` (e.g., `create_task_command.py`)
- **Queries**: `src/tools-provider/application/queries/get_{entity}_query.py`
- **Domain Events**: `src/tools-provider/domain/events/{entity}.py` with classes like `{Entity}{Action}DomainEvent`
- **DTOs**: `src/tools-provider/integration/models/{entity}_dto.py` decorated with `@queryable`

### Adding New Entities

1. Create aggregate in `src/tools-provider/domain/entities/` following `Task` pattern (AggregateRoot + AggregateState)
2. Add domain events in `src/tools-provider/domain/events/` with `@cloudevent` decorator
3. Create DTO in `src/tools-provider/integration/models/` with `@queryable` decorator
4. Add command/query handlers in `src/tools-provider/application/`
5. Register in `src/tools-provider/main.py` DataAccessLayer configuration
6. **Choose persistence strategy**:
   - State-Based: Use `MotorRepository.configure()` for MongoDB state persistence
   - Event-Sourced: Use `EventSourcingRepository.configure()` for EventStoreDB

### Persistence Decision Guide

| Question | If Yes → | If No → |
|----------|----------|---------|
| Need full audit trail for compliance? | Event-Sourced | State-Based |
| High-frequency updates (>10/sec)? | State-Based | Either |
| Need to replay/debug historical state? | Event-Sourced | State-Based |
| External systems consume events? | Either (both emit CloudEvents) | Either |

### State-Based Aggregate Pattern (MotorRepository)

```python
class MyEntityState(AggregateState[str]):
    id: str
    # ... your fields ...
    state_version: int  # Required for optimistic concurrency
    created_at: datetime
    last_modified: datetime

class MyEntity(AggregateRoot[MyEntityState, str]):
    def do_something(self, value: str) -> None:
        # Mutate state directly
        self.state.some_field = value
        self.state.last_modified = datetime.now(timezone.utc)
        # Register event (published as CloudEvent, NOT persisted)
        self.register_event(SomethingDoneDomainEvent(
            aggregate_id=self.id(),
            value=value
        ))
```

### Controller Pattern

Controllers use `classy-fastapi` decorators and inherit `ControllerBase`:

```python
# src/tools-provider/api/controllers/tasks_controller.py
class TasksController(ControllerBase):
    @get("/")
    async def get_tasks(self, user: dict = Depends(get_current_user)):
        query = GetTasksQuery(user_info=user)
        result = await self.mediator.execute_async(query)
        return self.process(result)
```

### Mapping

Use `@map_to(TargetClass)` decorator on source classes. Mapper auto-discovers from packages configured in `main.py`.

## Important Notes

### Settings

All config via environment variables in `src/tools-provider/application/settings.py`. Key prefixes:

- `KEYCLOAK_*` - OAuth2 config
- `OTEL_*` - OpenTelemetry tracing/metrics
- `CONNECTION_STRINGS` - JSON dict for eventstore/mongo URLs

### Code Style

- **Black** formatting (line-length: 200)
- **Ruff** linting
- Run `make format && make lint` before commits

## Architecture Documentation

See `docs/architecture/knowledge/` for the knowledge-manager microservice design:

- [00-overview.md](docs/architecture/knowledge/00-overview.md) - Executive summary, four runtime aspects
- Domain: **Learning & Certification** with role-based views (ExamOwner, Author, Tester, Proctor, Candidate, Analyst)
- Four Aspects: Temporal ("The Archive"), Semantic ("The Map"), Intentional ("The Compass"), Observational ("The Pulse")
- Persistence: State-Based (MongoDB) for most aggregates, Event-Sourced (EventStoreDB) for audit-critical only

### Key Architectural Concepts

| Concept | Description |
|---------|-------------|
| **Namespace Dual Structure** | Internal (semantic groups, DomainEvent hierarchy) + External (inter-namespace topology in Neo4j) |
| **Bounded Graph Complexity** | Edges scoped to semantic groups by default; cross-group/cross-namespace edges are explicit opt-in |
| **Business Rules** | Use `neuroglia.validation.business_rules` for constraints, incentives, logical procedures |
| **Seed → Evolve Pattern** | Hardcode initial rules, agents refine over time, humans approve promotions |
| **Workflow Orchestration** | Delegated to Synapse (ServerlessWorkflow), triggered by CloudEvents |
| **Agent Trust Levels** | UNKNOWN → DISCOVERED → ENGAGED → TRUSTED → DELEGATED |
| **Agent as AggregateRoot** | Agents are entities with public API (Tasks), capabilities, goals, and skills |
| **A2A Communication** | Async agent-to-agent messaging; RPC for sync, A2A for negotiations, CloudEvents for observability |
| **Vector Abstraction Layer** | Swappable backends (Qdrant, MongoDB Atlas, Neo4j) via `VectorStore` and `EmbeddingProvider` protocols |
| **Temporal Versioning** | Graphs, vectors, and edges include revision tracking (like versioned DomainEvents) |
| **Reconciliation Loop** | Autonomous per-aggregate reconcilers subscribe to DomainEvent streams, converge toward Goals |
| **Intent Expression** | Users express Intent via supportive agent with specialized MCP tools for goal elicitation |
