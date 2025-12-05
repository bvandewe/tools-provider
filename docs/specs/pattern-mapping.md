# MCP Tools Provider - Task to New Aggregates Pattern Mapping

This document maps the existing `Task` implementation patterns to the new aggregates
required for the MCP Tools Provider: `UpstreamSource`, `ToolGroup`, and `AccessPolicy`.

## 1. Pattern Overview

### Task Implementation Structure

```
src/domain/
├── entities/
│   └── task.py              # Task + TaskState classes
├── events/
│   └── task.py              # Domain events with @cloudevent
├── enums.py                 # TaskStatus, TaskPriority
└── repositories/
    └── task_dto_repository.py  # Abstract query repository

src/integration/
├── models/
│   └── task_dto.py          # @queryable TaskDto
└── repositories/
    └── motor_task_dto_repository.py  # MongoDB implementation

src/application/
├── commands/
│   ├── create_task_command.py
│   └── update_task_command.py
├── queries/
│   ├── get_tasks_query.py
│   └── get_task_by_id_query.py
└── events/domain/
    └── task_projection_handlers.py
```

## 2. Aggregate Pattern Mapping

### 2.1. Task → UpstreamSource

| Task Component | UpstreamSource Equivalent |
|----------------|---------------------------|
| `TaskState.id` | `UpstreamSourceState.id` |
| `TaskState.title` | `UpstreamSourceState.name` |
| `TaskState.description` | `UpstreamSourceState.url` |
| `TaskState.status` | `UpstreamSourceState.health_status` |
| `TaskState.priority` | `UpstreamSourceState.source_type` |
| `TaskState.assignee_id` | `UpstreamSourceState.auth_config` |
| `TaskState.created_at/updated_at` | Same pattern |

**Key Differences:**

- UpstreamSource has complex nested state (inventory_hash, sync tracking)
- UpstreamSource needs `@dispatch` handlers for more event types
- UpstreamSource has health lifecycle (HEALTHY → DEGRADED → UNHEALTHY)

### 2.2. TaskDto → SourceDto + ToolDefinitionDto

| TaskDto Field | SourceDto Equivalent | ToolDefinitionDto Equivalent |
|---------------|---------------------|------------------------------|
| `id` | `id` | `id` |
| `title` | `name` | `name` |
| `description` | `url` | `description` |
| `status` | `health_status` | N/A |
| `priority` | `source_type` | N/A |
| N/A | `inventory_count` | `source_id` (FK) |
| N/A | N/A | `input_schema` |
| N/A | N/A | `execution_profile` |

## 3. Event Pattern Mapping

### 3.1. Task Events → UpstreamSource Events

| Task Event | UpstreamSource Event | Notes |
|------------|---------------------|-------|
| `TaskCreatedDomainEvent` | `SourceRegisteredDomainEvent` | Similar structure |
| `TaskStatusUpdatedDomainEvent` | `SourceHealthChangedDomainEvent` | Health lifecycle |
| `TaskUpdatedDomainEvent` | `InventoryIngestedDomainEvent` | Complex payload |
| `TaskDeletedDomainEvent` | `SourceDeregisteredDomainEvent` | Soft delete |
| N/A | `SourceSyncFailedDomainEvent` | New: error tracking |
| N/A | `SourceEnabledDomainEvent` | New: enable/disable |
| N/A | `SourceDisabledDomainEvent` | New: enable/disable |

### 3.2. CloudEvent Type Naming Convention

Following the existing pattern: `{entity}.{action}.v{version}`

```python
# Task patterns (existing)
@cloudevent("task.created.v1")
@cloudevent("task.status.updated.v1")
@cloudevent("task.deleted.v1")

# UpstreamSource patterns (new)
@cloudevent("source.registered.v1")
@cloudevent("source.inventory.ingested.v1")
@cloudevent("source.sync.failed.v1")
@cloudevent("source.health.changed.v1")
@cloudevent("source.enabled.v1")
@cloudevent("source.disabled.v1")
@cloudevent("source.deregistered.v1")

# ToolGroup patterns (new)
@cloudevent("toolgroup.created.v1")
@cloudevent("toolgroup.selector.added.v1")
@cloudevent("toolgroup.selector.removed.v1")
@cloudevent("toolgroup.activated.v1")
@cloudevent("toolgroup.deactivated.v1")

# AccessPolicy patterns (new)
@cloudevent("accesspolicy.defined.v1")
@cloudevent("accesspolicy.groups.updated.v1")
@cloudevent("accesspolicy.matcher.updated.v1")
@cloudevent("accesspolicy.activated.v1")
@cloudevent("accesspolicy.deactivated.v1")
```

## 4. Command Handler Pattern Mapping

### 4.1. CreateTaskCommandHandler → RegisterSourceCommandHandler

```python
# Task pattern (existing)
class CreateTaskCommandHandler(
    CommandHandlerBase,
    CommandHandler[CreateTaskCommand, OperationResult[TaskDto]],
):
    def __init__(
        self,
        mediator: Mediator,
        mapper: Mapper,
        cloud_event_bus: CloudEventBus,
        cloud_event_publishing_options: CloudEventPublishingOptions,
        task_repository: Repository[Task, str],  # Write model
    ):
        ...

# UpstreamSource pattern (new) - SAME STRUCTURE
class RegisterSourceCommandHandler(
    CommandHandlerBase,
    CommandHandler[RegisterSourceCommand, OperationResult[SourceDto]],
):
    def __init__(
        self,
        mediator: Mediator,
        mapper: Mapper,
        cloud_event_bus: CloudEventBus,
        cloud_event_publishing_options: CloudEventPublishingOptions,
        source_repository: Repository[UpstreamSource, str],  # Write model
    ):
        ...
```

## 5. Query Handler Pattern Mapping

### 5.1. GetTasksQueryHandler → GetSourcesQueryHandler

```python
# Task pattern (existing)
class GetTasksQueryHandler(QueryHandler[GetTasksQuery, OperationResult[List[TaskDto]]]):
    def __init__(self, repository: TaskDtoRepository):  # Read model
        self._repository = repository

# UpstreamSource pattern (new) - SAME STRUCTURE
class GetSourcesQueryHandler(QueryHandler[GetSourcesQuery, OperationResult[List[SourceDto]]]):
    def __init__(self, repository: SourceDtoRepository):  # Read model
        self._repository = repository
```

## 6. Projection Handler Pattern Mapping

### 6.1. TaskCreatedProjectionHandler → SourceRegisteredProjectionHandler

```python
# Task pattern (existing)
class TaskCreatedProjectionHandler(DomainEventHandler[TaskCreatedDomainEvent]):
    def __init__(self, repository: Repository[TaskDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: TaskCreatedDomainEvent) -> None:
        # Idempotency check
        existing = await self._repository.get_async(event.aggregate_id)
        if existing:
            return

        task_dto = TaskDto(...)
        await self._repository.add_async(task_dto)

# UpstreamSource pattern (new) - SAME STRUCTURE
class SourceRegisteredProjectionHandler(DomainEventHandler[SourceRegisteredDomainEvent]):
    def __init__(self, repository: Repository[SourceDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: SourceRegisteredDomainEvent) -> None:
        # Idempotency check
        existing = await self._repository.get_async(event.aggregate_id)
        if existing:
            return

        source_dto = SourceDto(...)
        await self._repository.add_async(source_dto)
```

## 7. Repository Pattern Mapping

### 7.1. Abstract Repository Interface

```python
# Task pattern (existing)
class TaskDtoRepository(Repository[TaskDto, str], ABC):
    @abstractmethod
    async def get_all_async(self) -> list[TaskDto]: ...

    @abstractmethod
    async def get_by_assignee_async(self, assignee_id: str) -> list[TaskDto]: ...

# UpstreamSource pattern (new) - SAME STRUCTURE
class SourceDtoRepository(Repository[SourceDto, str], ABC):
    @abstractmethod
    async def get_all_async(self) -> list[SourceDto]: ...

    @abstractmethod
    async def get_enabled_async(self) -> list[SourceDto]: ...

    @abstractmethod
    async def get_by_health_status_async(self, status: HealthStatus) -> list[SourceDto]: ...
```

### 7.2. Motor Repository Implementation

```python
# Task pattern (existing)
class MotorTaskDtoRepository(MotorRepository[TaskDto, str], TaskDtoRepository):
    async def get_by_assignee_async(self, assignee_id: str) -> list[TaskDto]:
        queryable = await self.query_async()
        return await queryable \
            .where(lambda task: task.assignee_id == assignee_id) \
            .order_by(lambda task: task.created_at) \
            .to_list_async()

# UpstreamSource pattern (new) - SAME STRUCTURE
class MotorSourceDtoRepository(MotorRepository[SourceDto, str], SourceDtoRepository):
    async def get_enabled_async(self) -> list[SourceDto]:
        queryable = await self.query_async()
        return await queryable \
            .where(lambda source: source.is_enabled == True) \
            .order_by(lambda source: source.name) \
            .to_list_async()
```

## 8. main.py Registration Pattern

### 8.1. DataAccessLayer Configuration

```python
# Existing Task configuration
DataAccessLayer.WriteModel(
    options=EventSourcingRepositoryOptions(delete_mode=DeleteMode.HARD),
).configure(builder, ["domain.entities"])  # Scans for AggregateRoot classes

DataAccessLayer.ReadModel(
    database_name="tools_provider",
    repository_type="motor",
    repository_mappings={
        TaskDtoRepository: MotorTaskDtoRepository,
        # ADD NEW MAPPINGS:
        SourceDtoRepository: MotorSourceDtoRepository,
        ToolDefinitionRepository: MotorToolDefinitionRepository,
        ToolGroupDtoRepository: MotorToolGroupDtoRepository,
        AccessPolicyDtoRepository: MotorAccessPolicyDtoRepository,
    },
).configure(builder, ["integration.models", "application.events.domain"])
```

## 9. Key Implementation Notes

### 9.1. Aggregate State Initialization

The `TaskState.__init__()` pattern MUST be followed:

```python
class UpstreamSourceState(AggregateState[str]):
    def __init__(self) -> None:
        super().__init__()
        # Initialize ALL fields with defaults
        self.id = ""
        self.name = ""
        self.url = ""
        self.source_type = SourceType.OPENAPI
        self.health_status = HealthStatus.UNKNOWN
        self.is_enabled = True
        self.inventory_hash = ""
        self.inventory_count = 0
        self.last_sync_at = None
        self.last_sync_error = None
        self.consecutive_failures = 0

        now = datetime.now(timezone.utc)
        self.created_at = now
        self.updated_at = now
```

### 9.2. Event Application Pattern

Each domain event needs a `@dispatch` handler in the State class:

```python
@dispatch(SourceRegisteredDomainEvent)
def on(self, event: SourceRegisteredDomainEvent) -> None:
    self.id = event.aggregate_id
    self.name = event.name
    self.url = event.url
    self.source_type = event.source_type
    self.created_at = event.created_at
    self.updated_at = event.created_at
```

### 9.3. Aggregate Method Pattern

Methods should check for no-op conditions and return bool:

```python
def update_health_status(self, new_status: HealthStatus) -> bool:
    if self.state.health_status == new_status:
        return False
    self.state.on(
        self.register_event(
            SourceHealthChangedDomainEvent(
                aggregate_id=self.id(),
                old_status=self.state.health_status,
                new_status=new_status,
            )
        )
    )
    return True
```

## 10. Conclusion

The existing Task implementation provides a complete, tested blueprint for implementing
the new MCP Tools Provider aggregates. Key points:

1. **Follow the exact class hierarchy**: `AggregateRoot[TState, str]` + `AggregateState[str]`
2. **Use `@dispatch` for event handlers** in State classes
3. **Apply `@cloudevent` decorator** to all domain events
4. **Separate repositories**: Write model via `Repository[Aggregate, str]`, Read model via custom `DtoRepository`
5. **Register in main.py**: Both WriteModel and ReadModel DataAccessLayer configurations
6. **Projection handlers** listen to events from ReadModelReconciliator

Following these patterns ensures consistency and leverages the Neuroglia framework's
automatic event publishing, persistence, and read model reconciliation.
