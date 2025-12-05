# Read Model Reconciliation Guide

This document explains how to properly reconcile the Write Model (EventStoreDB) with the Read Model (MongoDB) in the tools-provider application using Neuroglia's `ReadModelReconciliator`.

## Architecture Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Command       │────▶│  EventStoreDB    │────▶│  ReadModel      │
│   (Create Task) │     │  (Write Model)   │     │  Reconciliator  │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
                                                          ▼
                                                 ┌─────────────────┐
                                                 │   Mediator      │
                                                 │   (publish)     │
                                                 └────────┬────────┘
                                                          │
                                                          ▼
                                                 ┌─────────────────┐
                                                 │ DomainEvent     │
                                                 │ Handler         │
                                                 └────────┬────────┘
                                                          │
                                                          ▼
                                                 ┌─────────────────┐
                                                 │   MongoDB       │
                                                 │   (Read Model)  │
                                                 └─────────────────┘
```

## How ReadModelReconciliator Works

The `ReadModelReconciliator` is a `HostedService` that:

1. **Subscribes** to the EventStoreDB category stream (`$ce-{database_name}`)
2. **Streams** all domain events via a persistent subscription (consumer group)
3. **Publishes** each event through the Mediator
4. **Handlers** receive events and update the Read Model (MongoDB)

### Key Components

| Component | Purpose |
|-----------|---------|
| `EventStoreOptions` | Configures database name and consumer group |
| `ReadModelConciliationOptions` | Consumer group for the reconciliator |
| `ReadModelReconciliator` | HostedService that streams events |
| `DomainEventHandler[T]` | Handlers that update MongoDB |

## Current Configuration

Your `main.py` already configures the infrastructure correctly:

```python
# Configure Event Sourcing
ESEventStore.configure(builder, EventStoreOptions("tools_provider", "tools_provider_group"))

# WriteModel - scans domain.entities for AggregateRoot types
DataAccessLayer.WriteModel().configure(
    builder,
    ["domain.entities"],
    lambda builder_, entity_type, key_type: EventSourcingRepository.configure(builder_, entity_type, key_type)
)

# ReadModel - scans for @queryable types and registers ReadModelReconciliator
DataAccessLayer.ReadModel().configure(
    builder,
    ["integration.models", "application.events.domain"],
    lambda builder_, entity_type, key_type: MotorRepository.configure(builder_, entity_type, key_type, "tools_provider")
)
```

Your `settings.py` has:

```python
consumer_group: Optional[str] = "tools-provider-consumer-group"
```

## What's Missing: Domain Event Handlers for Read Model

The `ReadModelReconciliator` publishes domain events via the Mediator, but you need **handlers** to:

1. Receive the domain events
2. Map them to DTOs
3. Persist to MongoDB

### Step 1: Create Read Model Projection Handlers

Create a new file `src/application/events/domain/task_projection_handlers.py`:

```python
"""
Read Model Projection Handlers for Task Aggregate.

These handlers listen to domain events from the ReadModelReconciliator
and update the MongoDB read model accordingly.
"""

import logging
from typing import Optional

from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.mapping import Mapper
from neuroglia.mediation import DomainEventHandler

from domain.events import (
    TaskCreatedDomainEvent,
    TaskTitleUpdatedDomainEvent,
    TaskDescriptionUpdatedDomainEvent,
    TaskStatusChangedDomainEvent,
    TaskPriorityChangedDomainEvent,
    TaskAssignedDomainEvent,
    TaskUnassignedDomainEvent,
    TaskDepartmentChangedDomainEvent,
)
from integration.models.task_dto import TaskDto

logger = logging.getLogger(__name__)


class TaskCreatedProjectionHandler(DomainEventHandler[TaskCreatedDomainEvent]):
    """Projects TaskCreatedDomainEvent to MongoDB Read Model."""

    def __init__(
        self,
        repository: Repository[TaskDto, str],
        mapper: Mapper,
    ):
        super().__init__()
        self._repository = repository
        self._mapper = mapper

    async def handle_async(self, event: TaskCreatedDomainEvent) -> None:
        """Create TaskDto in Read Model."""
        logger.info(f"📥 Projecting TaskCreated: {event.aggregate_id}")

        # Map domain event to DTO
        task_dto = TaskDto(
            id=event.aggregate_id,
            title=event.title,
            description=event.description,
            status=event.status,
            priority=event.priority,
            assignee_id=event.assignee_id,
            department=event.department,
            created_at=event.created_at,
            updated_at=event.updated_at,
            created_by=event.created_by,
        )

        await self._repository.add_async(task_dto)
        logger.info(f"✅ Projected TaskCreated to Read Model: {event.aggregate_id}")


class TaskTitleUpdatedProjectionHandler(DomainEventHandler[TaskTitleUpdatedDomainEvent]):
    """Projects TaskTitleUpdatedDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[TaskDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: TaskTitleUpdatedDomainEvent) -> None:
        """Update task title in Read Model."""
        logger.info(f"📥 Projecting TaskTitleUpdated: {event.aggregate_id}")

        task = await self._repository.get_async(event.aggregate_id)
        if task:
            task.title = event.title
            task.updated_at = event.updated_at
            await self._repository.update_async(task)
            logger.info(f"✅ Projected TaskTitleUpdated to Read Model: {event.aggregate_id}")
        else:
            logger.warning(f"⚠️ Task not found in Read Model: {event.aggregate_id}")


class TaskDescriptionUpdatedProjectionHandler(DomainEventHandler[TaskDescriptionUpdatedDomainEvent]):
    """Projects TaskDescriptionUpdatedDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[TaskDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: TaskDescriptionUpdatedDomainEvent) -> None:
        """Update task description in Read Model."""
        logger.info(f"📥 Projecting TaskDescriptionUpdated: {event.aggregate_id}")

        task = await self._repository.get_async(event.aggregate_id)
        if task:
            task.description = event.description
            task.updated_at = event.updated_at
            await self._repository.update_async(task)
            logger.info(f"✅ Projected TaskDescriptionUpdated to Read Model: {event.aggregate_id}")
        else:
            logger.warning(f"⚠️ Task not found in Read Model: {event.aggregate_id}")


class TaskStatusChangedProjectionHandler(DomainEventHandler[TaskStatusChangedDomainEvent]):
    """Projects TaskStatusChangedDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[TaskDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: TaskStatusChangedDomainEvent) -> None:
        """Update task status in Read Model."""
        logger.info(f"📥 Projecting TaskStatusChanged: {event.aggregate_id}")

        task = await self._repository.get_async(event.aggregate_id)
        if task:
            task.status = event.new_status
            task.updated_at = event.updated_at
            await self._repository.update_async(task)
            logger.info(f"✅ Projected TaskStatusChanged to Read Model: {event.aggregate_id}")
        else:
            logger.warning(f"⚠️ Task not found in Read Model: {event.aggregate_id}")


class TaskPriorityChangedProjectionHandler(DomainEventHandler[TaskPriorityChangedDomainEvent]):
    """Projects TaskPriorityChangedDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[TaskDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: TaskPriorityChangedDomainEvent) -> None:
        """Update task priority in Read Model."""
        logger.info(f"📥 Projecting TaskPriorityChanged: {event.aggregate_id}")

        task = await self._repository.get_async(event.aggregate_id)
        if task:
            task.priority = event.new_priority
            task.updated_at = event.updated_at
            await self._repository.update_async(task)
            logger.info(f"✅ Projected TaskPriorityChanged to Read Model: {event.aggregate_id}")
        else:
            logger.warning(f"⚠️ Task not found in Read Model: {event.aggregate_id}")


class TaskAssignedProjectionHandler(DomainEventHandler[TaskAssignedDomainEvent]):
    """Projects TaskAssignedDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[TaskDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: TaskAssignedDomainEvent) -> None:
        """Update task assignee in Read Model."""
        logger.info(f"📥 Projecting TaskAssigned: {event.aggregate_id}")

        task = await self._repository.get_async(event.aggregate_id)
        if task:
            task.assignee_id = event.assignee_id
            task.updated_at = event.updated_at
            await self._repository.update_async(task)
            logger.info(f"✅ Projected TaskAssigned to Read Model: {event.aggregate_id}")
        else:
            logger.warning(f"⚠️ Task not found in Read Model: {event.aggregate_id}")


class TaskUnassignedProjectionHandler(DomainEventHandler[TaskUnassignedDomainEvent]):
    """Projects TaskUnassignedDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[TaskDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: TaskUnassignedDomainEvent) -> None:
        """Clear task assignee in Read Model."""
        logger.info(f"📥 Projecting TaskUnassigned: {event.aggregate_id}")

        task = await self._repository.get_async(event.aggregate_id)
        if task:
            task.assignee_id = None
            task.updated_at = event.updated_at
            await self._repository.update_async(task)
            logger.info(f"✅ Projected TaskUnassigned to Read Model: {event.aggregate_id}")
        else:
            logger.warning(f"⚠️ Task not found in Read Model: {event.aggregate_id}")


class TaskDepartmentChangedProjectionHandler(DomainEventHandler[TaskDepartmentChangedDomainEvent]):
    """Projects TaskDepartmentChangedDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[TaskDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: TaskDepartmentChangedDomainEvent) -> None:
        """Update task department in Read Model."""
        logger.info(f"📥 Projecting TaskDepartmentChanged: {event.aggregate_id}")

        task = await self._repository.get_async(event.aggregate_id)
        if task:
            task.department = event.department
            task.updated_at = event.updated_at
            await self._repository.update_async(task)
            logger.info(f"✅ Projected TaskDepartmentChanged to Read Model: {event.aggregate_id}")
        else:
            logger.warning(f"⚠️ Task not found in Read Model: {event.aggregate_id}")
```

### Step 2: Update the `__init__.py` to Export Handlers

Update `src/application/events/domain/__init__.py`:

```python
from .tasks_events import TaskCreatedDomainEventHandler
from .task_projection_handlers import (
    TaskCreatedProjectionHandler,
    TaskTitleUpdatedProjectionHandler,
    TaskDescriptionUpdatedProjectionHandler,
    TaskStatusChangedProjectionHandler,
    TaskPriorityChangedProjectionHandler,
    TaskAssignedProjectionHandler,
    TaskUnassignedProjectionHandler,
    TaskDepartmentChangedProjectionHandler,
)

__all__ = [
    "TaskCreatedDomainEventHandler",
    "TaskCreatedProjectionHandler",
    "TaskTitleUpdatedProjectionHandler",
    "TaskDescriptionUpdatedProjectionHandler",
    "TaskStatusChangedProjectionHandler",
    "TaskPriorityChangedProjectionHandler",
    "TaskAssignedProjectionHandler",
    "TaskUnassignedProjectionHandler",
    "TaskDepartmentChangedProjectionHandler",
]
```

### Step 3: Ensure Mediator Scans the Handlers

The Mediator is already configured to scan `application.events.domain`:

```python
Mediator.configure(
    builder,
    [
        "application.commands",
        "application.queries",
        "application.events.domain",      # ✅ Already includes projection handlers
        "application.events.integration",
    ],
)
```

## How the Flow Works

1. **User creates a task** via POST /api/tasks/
2. **CreateTaskCommandHandler** creates the `Task` aggregate and stores events in EventStoreDB
3. **EventSourcingRepository** appends `TaskCreatedDomainEvent` to EventStoreDB
4. **ReadModelReconciliator** (running as HostedService) observes the category stream
5. **Reconciliator** publishes the event via Mediator
6. **TaskCreatedProjectionHandler** receives the event
7. **Handler** creates `TaskDto` and stores it in MongoDB via `Repository[TaskDto, str]`
8. **GET /api/tasks/** queries MongoDB and returns the task

## Potential Issues & Solutions

### Issue 1: MotorRepository Abstract Methods

As documented in `NEUROGLIA_CHANGE_REQUEST.md`, `MotorRepository` may fail due to missing `_do_*` abstract methods. Ensure `patches.py` is applied.

### Issue 2: Event Ordering

The `ReadModelReconciliator` uses a persistent subscription with consumer group, ensuring:

- At-least-once delivery
- Ordered processing within a stream
- Resume from last position on restart

### Issue 3: Duplicate Events

If the reconciliator crashes after processing but before ACK, events may be replayed. Handlers should be **idempotent**:

```python
async def handle_async(self, event: TaskCreatedDomainEvent) -> None:
    # Check if already exists (idempotent)
    existing = await self._repository.get_async(event.aggregate_id)
    if existing:
        logger.info(f"⏭️ Task already exists, skipping: {event.aggregate_id}")
        return

    # Create new task
    task_dto = TaskDto(...)
    await self._repository.add_async(task_dto)
```

### Issue 4: Concurrent Event Publishing

The current `tasks_events.py` handler also logs task creation. With projection handlers, you'll have **two handlers** for `TaskCreatedDomainEvent`:

1. `TaskCreatedDomainEventHandler` - Logs/notifications (side effects)
2. `TaskCreatedProjectionHandler` - Updates read model

This is fine - Mediator publishes to all registered handlers.

## Testing the Reconciliation

```bash
# 1. Create a task
TOKEN=$(curl -s -X POST "http://localhost:8041/realms/tools-provider/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password&client_id=tools-provider-public&username=admin&password=test" | jq -r '.access_token')

curl -X POST "http://localhost:8040/api/tasks/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"title": "Test Reconciliation", "description": "Testing read model sync"}'

# 2. Query the read model (should return the task if projection handlers work)
curl -X GET "http://localhost:8040/api/tasks/" \
  -H "Authorization: Bearer $TOKEN"

# 3. Check logs for projection messages
docker logs tools-provider-app 2>&1 | grep "Projecting"
```

## Summary

| Component | Status | Action Required |
|-----------|--------|-----------------|
| `EventStoreOptions` | ✅ Configured | None |
| `ReadModelConciliationOptions` | ✅ Configured via `consumer_group` setting | None |
| `ReadModelReconciliator` | ✅ Auto-registered by `DataAccessLayer.ReadModel()` | None |
| `Repository[TaskDto, str]` | ✅ Registered via `MotorRepository.configure()` | None |
| **Projection Handlers** | ❌ Missing | Create handlers in `task_projection_handlers.py` |

The key missing piece is the **projection handlers** that listen to domain events and update MongoDB.
