# Copilot Instructions for tools-provider

## Project Overview

A Python microservice built with **Neuroglia Framework** on FastAPI, implementing **CQRS** (Command Query Responsibility Segregation) with **Event Sourcing**. The service manages MCP tools from OpenAPI services, featuring dual OAuth2/JWT authentication via Keycloak.

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

3. **Write/Read Model Separation**:
   - **Write Model**: EventStoreDB via `EventSourcingRepository`
   - **Read Model**: MongoDB via `MongoRepository`
   - Configured in `src/tools-provider/main.py` using `DataAccessLayer.WriteModel()` / `DataAccessLayer.ReadModel()`

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
