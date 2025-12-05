# Neuroglia Framework Enhancement: Hard and Soft Delete in EventSourcingRepository

**Date**: December 1, 2025
**Submitted By**: tools-provider team
**Framework Version**: neuroglia-python v0.6.13
**Priority**: High
**Type**: Enhancement Request

---

## Summary

Request to add support for both **hard delete** and **soft delete** strategies in `EventSourcingRepository`. Event sourcing paradigms traditionally preserve all events (immutable history), but production systems often need the ability to:

1. **Soft delete**: Mark an aggregate as deleted via a domain event while preserving the event stream
2. **Hard delete**: Physically remove the entire event stream (for GDPR compliance, data cleanup, etc.)

---

## Current Behavior

### EventSourcingRepository._do_remove_async

The current implementation in `EventSourcingRepository` has a placeholder that raises `NotImplementedError`:

```python
# neuroglia/data/infrastructure/event_sourcing/event_sourcing_repository.py

async def _do_remove_async(self, id: TKey) -> None:
    """Removes the aggregate root with the specified key, if any"""
    raise NotImplementedError("Event sourcing repositories do not support hard deletes")
```

### Workaround Required

Currently, to implement deletion in an event-sourced system, developers must:

1. Create a custom deletion domain event (e.g., `TaskDeletedDomainEvent`)
2. Handle deletion in the aggregate state
3. Manually manage the deletion workflow outside the repository pattern

```python
# Current workaround in domain entity
class Task(AggregateRoot[TaskState, str]):
    def mark_as_deleted(self, deleted_by: Optional[str] = None) -> None:
        """Mark the task as deleted by registering a deletion event."""
        self.state.on(
            self.register_event(
                TaskDeletedDomainEvent(
                    aggregate_id=self.id(),
                    title=self.state.title,
                    deleted_by=deleted_by,
                )
            )
        )

# In state class
class TaskState(AggregateState[str]):
    @dispatch(TaskDeletedDomainEvent)
    def on(self, event: TaskDeletedDomainEvent) -> None:
        """Apply the deleted event to the state."""
        # Note: We don't actually delete, just mark timestamp
        self.updated_at = datetime.now(timezone.utc)
```

This pattern works for soft delete but:

- ❌ Does not integrate with the repository's `remove_async` method
- ❌ Requires custom logic in command handlers to choose between soft/hard delete
- ❌ Hard delete (stream deletion) is not supported at all
- ❌ No standard way to query for non-deleted aggregates

---

## Proposed Enhancement

### 1. Add DeleteMode Enum

```python
# neuroglia/data/infrastructure/event_sourcing/abstractions.py

from enum import Enum

class DeleteMode(Enum):
    """Specifies how deletion should be handled in event-sourced repositories."""

    SOFT = "soft"
    """Append a tombstone event to the stream. Stream remains queryable but aggregate is marked as deleted."""

    HARD = "hard"
    """Physically delete the entire event stream from the event store."""

    DISABLED = "disabled"
    """Deletion is not allowed (current default behavior)."""
```

### 2. Enhanced EventSourcingRepository Configuration

```python
# neuroglia/data/infrastructure/event_sourcing/event_sourcing_repository.py

from dataclasses import dataclass
from typing import Optional, Type, Callable

@dataclass
class EventSourcingRepositoryOptions:
    """Configuration options for EventSourcingRepository."""

    delete_mode: DeleteMode = DeleteMode.DISABLED
    """Specifies how deletion should be handled."""

    tombstone_event_type: Optional[Type[DomainEvent]] = None
    """The domain event type to append when soft-deleting.
    Required when delete_mode is SOFT."""

    tombstone_event_factory: Optional[Callable[[TKey], DomainEvent]] = None
    """Factory function to create tombstone events.
    Takes the aggregate ID and returns a configured DomainEvent."""

    include_deleted_in_queries: bool = False
    """If True, soft-deleted aggregates will be included in query results.
    Default is False (deleted aggregates are filtered out)."""


class EventSourcingRepository(Generic[TAggregate, TKey], Repository[TAggregate, TKey]):
    """Represents an event sourcing repository implementation with configurable deletion."""

    def __init__(
        self,
        eventstore: EventStore,
        aggregator: Aggregator,
        mediator: Optional["Mediator"] = None,
        options: Optional[EventSourcingRepositoryOptions] = None,
    ):
        super().__init__(mediator)
        self._eventstore = eventstore
        self._aggregator = aggregator
        self._options = options or EventSourcingRepositoryOptions()
```

### 3. Implement _do_remove_async with Delete Modes

```python
async def _do_remove_async(self, id: TKey) -> None:
    """
    Removes the aggregate root with the specified key based on configured delete mode.

    Args:
        id: The identifier of the aggregate to remove

    Raises:
        NotImplementedError: When delete_mode is DISABLED
        ValueError: When delete_mode is SOFT but no tombstone configuration provided
    """
    match self._options.delete_mode:
        case DeleteMode.DISABLED:
            raise NotImplementedError(
                "Deletion is disabled for this repository. "
                "Configure delete_mode=DeleteMode.SOFT or DeleteMode.HARD to enable deletion."
            )

        case DeleteMode.SOFT:
            await self._soft_delete_async(id)

        case DeleteMode.HARD:
            await self._hard_delete_async(id)


async def _soft_delete_async(self, id: TKey) -> None:
    """
    Append a tombstone event to mark the aggregate as deleted.
    The event stream is preserved for audit and potential restoration.
    """
    if self._options.tombstone_event_factory is None:
        if self._options.tombstone_event_type is None:
            raise ValueError(
                "Soft delete requires either tombstone_event_type or "
                "tombstone_event_factory to be configured."
            )
        # Create a basic tombstone event if only type is provided
        tombstone_event = self._options.tombstone_event_type(aggregate_id=id)
    else:
        tombstone_event = self._options.tombstone_event_factory(id)

    stream_id = self._build_stream_id_for(id)

    # Read current stream to get version
    stream = await self._eventstore.read_async(stream_id)
    current_version = len(stream.events) - 1 if stream and stream.events else -1

    # Encode and append tombstone event
    encoded_event = self._encode_event(tombstone_event)
    await self._eventstore.append_async(stream_id, [encoded_event], current_version)


async def _hard_delete_async(self, id: TKey) -> None:
    """
    Physically delete the entire event stream from the event store.
    WARNING: This is irreversible and removes all history for this aggregate.
    """
    stream_id = self._build_stream_id_for(id)
    await self._eventstore.delete_async(stream_id)
```

### 4. EventStore Interface Enhancement

The `EventStore` abstraction needs a `delete_async` method:

```python
# neuroglia/data/infrastructure/event_sourcing/abstractions.py

class EventStore(ABC):
    """Abstract base class for event store implementations."""

    @abstractmethod
    async def append_async(
        self,
        stream_id: str,
        events: list[EventDescriptor],
        expected_version: Optional[int] = None,
    ) -> None:
        """Appends events to the specified stream."""
        ...

    @abstractmethod
    async def read_async(
        self,
        stream_id: str,
        start_version: int = 0,
        count: Optional[int] = None,
    ) -> Optional[EventStream]:
        """Reads events from the specified stream."""
        ...

    @abstractmethod
    async def delete_async(self, stream_id: str) -> None:
        """
        Deletes the entire event stream.

        This operation is irreversible and should be used with caution.
        Useful for GDPR compliance (right to be forgotten) or data cleanup.

        Args:
            stream_id: The identifier of the stream to delete

        Raises:
            StreamNotFoundException: If the stream does not exist
        """
        ...
```

### 5. ESEventStore Implementation for EventStoreDB

```python
# neuroglia/data/infrastructure/event_sourcing/event_store/event_store.py

class ESEventStore(EventStore):
    """EventStoreDB implementation of EventStore."""

    async def delete_async(self, stream_id: str) -> None:
        """
        Delete the stream from EventStoreDB.

        Uses EventStoreDB's stream deletion which supports:
        - Soft delete (default): Stream metadata marks it deleted, events remain
        - Hard delete (tombstone): Stream is permanently removed
        """
        try:
            # EventStoreDB client delete operation
            await self._client.delete_stream(stream_id)
        except StreamNotFoundError:
            raise StreamNotFoundException(f"Stream '{stream_id}' not found")
```

---

## Configuration Examples

### Example 1: Soft Delete with Custom Tombstone Event

```python
from neuroglia.data.infrastructure.event_sourcing import (
    EventSourcingRepository,
    EventSourcingRepositoryOptions,
    DeleteMode,
)
from domain.events import TaskDeletedDomainEvent

# Configure repository with soft delete
options = EventSourcingRepositoryOptions(
    delete_mode=DeleteMode.SOFT,
    tombstone_event_type=TaskDeletedDomainEvent,
)

# Register in dependency injection
EventSourcingRepository.configure(
    builder,
    aggregate_type=Task,
    key_type=str,
    options=options,
)
```

### Example 2: Soft Delete with Factory Function

```python
def create_deletion_event(task_id: str) -> TaskDeletedDomainEvent:
    return TaskDeletedDomainEvent(
        aggregate_id=task_id,
        title="",  # Will be ignored in projection
        deleted_by="system",
        deleted_at=datetime.now(timezone.utc),
    )

options = EventSourcingRepositoryOptions(
    delete_mode=DeleteMode.SOFT,
    tombstone_event_factory=create_deletion_event,
)
```

### Example 3: Hard Delete (GDPR Compliance)

```python
options = EventSourcingRepositoryOptions(
    delete_mode=DeleteMode.HARD,
)

# Usage in command handler
async def handle(self, command: DeleteUserDataCommand) -> None:
    # Hard delete removes all events - GDPR "right to be forgotten"
    await self._repository.remove_async(command.user_id)
```

### Example 4: Enhanced configure() Static Method

```python
@staticmethod
def configure(
    builder: ApplicationBuilderBase,
    aggregate_type: type[TAggregate],
    key_type: type[TKey],
    options: Optional[EventSourcingRepositoryOptions] = None,
    connection_string_name: str = "eventstore",
    domain_repository_type: Optional[type] = None,
) -> ApplicationBuilderBase:
    """
    Configure EventSourcingRepository with the dependency injection container.

    Args:
        builder: Application builder instance
        aggregate_type: The aggregate type this repository manages
        key_type: The type of the aggregate's identifier
        options: Repository configuration options (delete mode, tombstone config, etc.)
        connection_string_name: Name of connection string for event store
        domain_repository_type: Optional domain-layer repository interface to register

    Returns:
        The configured application builder
    """
    ...
```

---

## Impact on Querying

### Filtering Deleted Aggregates

When `include_deleted_in_queries=False` (default), the repository should filter out soft-deleted aggregates:

```python
async def get_async(self, id: TKey) -> Optional[TAggregate]:
    """Get aggregate by ID, excluding soft-deleted unless configured otherwise."""
    aggregate = await self._rehydrate_async(id)

    if aggregate and not self._options.include_deleted_in_queries:
        if self._is_soft_deleted(aggregate):
            return None

    return aggregate


async def list_async(self) -> AsyncIterable[TAggregate]:
    """List all aggregates, excluding soft-deleted unless configured otherwise."""
    # Implementation would need stream metadata or projection support
    ...


def _is_soft_deleted(self, aggregate: TAggregate) -> bool:
    """Check if aggregate has been soft-deleted by examining its events."""
    # Check if the last event is a tombstone event
    if self._options.tombstone_event_type:
        for event in reversed(aggregate._pending_events):
            if isinstance(event, self._options.tombstone_event_type):
                return True
    return False
```

---

## Alternative: Delegate Soft Delete to Aggregate

An alternative design leaves soft delete entirely to the aggregate pattern:

```python
class EventSourcingRepositoryOptions:
    """Configuration options for EventSourcingRepository."""

    delete_mode: DeleteMode = DeleteMode.DISABLED
    """
    DISABLED: _do_remove_async raises NotImplementedError (current behavior)
    SOFT: Calls aggregate.mark_deleted() if method exists, then persists
    HARD: Physically deletes the stream
    """


async def _soft_delete_async(self, id: TKey) -> None:
    """Soft delete by calling aggregate's mark_deleted method."""
    aggregate = await self.get_async(id)
    if aggregate is None:
        raise AggregateNotFoundException(f"Aggregate with id '{id}' not found")

    # Call the aggregate's deletion method (convention-based)
    if hasattr(aggregate, 'mark_deleted'):
        aggregate.mark_deleted()
    elif hasattr(aggregate, 'mark_as_deleted'):
        aggregate.mark_as_deleted()
    else:
        raise ValueError(
            f"Aggregate {type(aggregate).__name__} does not have a "
            "mark_deleted() or mark_as_deleted() method for soft delete"
        )

    # Persist the deletion event
    await self._do_update_async(aggregate)
```

**Benefits of this approach:**

- ✅ Aggregate controls its own deletion semantics
- ✅ Domain events are defined in domain layer (not infrastructure)
- ✅ Consistent with DDD principles
- ✅ Simpler repository configuration

---

## Migration Path

### Phase 1: Non-Breaking Changes

1. Add `DeleteMode` enum
2. Add `EventSourcingRepositoryOptions` dataclass
3. Add optional `options` parameter to `__init__`
4. Default behavior unchanged (`DeleteMode.DISABLED`)

### Phase 2: EventStore Enhancement

1. Add `delete_async` abstract method to `EventStore`
2. Implement in `ESEventStore` for EventStoreDB
3. Implement in any other event store adapters

### Phase 3: Repository Implementation

1. Implement `_soft_delete_async`
2. Implement `_hard_delete_async`
3. Update `_do_remove_async` to use delete mode

### Phase 4: Query Filtering

1. Add `include_deleted_in_queries` option
2. Implement filtering in `get_async`, `list_async`, etc.

---

## Testing Requirements

```python
import pytest
from neuroglia.data.infrastructure.event_sourcing import (
    EventSourcingRepository,
    EventSourcingRepositoryOptions,
    DeleteMode,
)

class TestEventSourcingRepositoryDelete:

    @pytest.mark.asyncio
    async def test_remove_disabled_raises_not_implemented(self, repository):
        """Default behavior raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            await repository.remove_async("task-123")

    @pytest.mark.asyncio
    async def test_soft_delete_appends_tombstone_event(self, soft_delete_repository):
        """Soft delete appends tombstone event to stream."""
        task = await soft_delete_repository.add_async(create_task())
        await soft_delete_repository.remove_async(task.id())

        # Verify tombstone event was appended
        stream = await event_store.read_async(f"task-{task.id()}")
        assert isinstance(stream.events[-1], TaskDeletedDomainEvent)

    @pytest.mark.asyncio
    async def test_soft_deleted_aggregate_not_returned_by_default(self, soft_delete_repository):
        """Soft-deleted aggregates are not returned by get_async."""
        task = await soft_delete_repository.add_async(create_task())
        await soft_delete_repository.remove_async(task.id())

        result = await soft_delete_repository.get_async(task.id())
        assert result is None

    @pytest.mark.asyncio
    async def test_soft_deleted_aggregate_returned_when_configured(self, include_deleted_repository):
        """Soft-deleted aggregates returned when include_deleted_in_queries=True."""
        task = await include_deleted_repository.add_async(create_task())
        await include_deleted_repository.remove_async(task.id())

        result = await include_deleted_repository.get_async(task.id())
        assert result is not None

    @pytest.mark.asyncio
    async def test_hard_delete_removes_stream(self, hard_delete_repository):
        """Hard delete physically removes the event stream."""
        task = await hard_delete_repository.add_async(create_task())
        await hard_delete_repository.remove_async(task.id())

        stream = await event_store.read_async(f"task-{task.id()}")
        assert stream is None

    @pytest.mark.asyncio
    async def test_soft_delete_requires_tombstone_config(self):
        """Soft delete without tombstone config raises ValueError."""
        options = EventSourcingRepositoryOptions(delete_mode=DeleteMode.SOFT)
        repo = EventSourcingRepository(event_store, aggregator, options=options)

        with pytest.raises(ValueError, match="tombstone"):
            await repo.remove_async("task-123")
```

---

## Files to Modify

| File | Changes |
|------|---------|
| `neuroglia/data/infrastructure/event_sourcing/abstractions.py` | Add `DeleteMode` enum, add `delete_async` to `EventStore` ABC |
| `neuroglia/data/infrastructure/event_sourcing/event_sourcing_repository.py` | Add `EventSourcingRepositoryOptions`, implement `_soft_delete_async`, `_hard_delete_async`, update `_do_remove_async` |
| `neuroglia/data/infrastructure/event_sourcing/event_store/event_store.py` | Implement `delete_async` for EventStoreDB |
| Tests | Add comprehensive test coverage for all delete modes |

---

## Related Patterns

### CQRS Read Model Cleanup

When using CQRS with read model projections (e.g., MongoDB), the `ReadModelReconciliator` should handle deletion events:

```python
class TaskProjectionHandler:
    @handles(TaskDeletedDomainEvent)
    async def handle(self, event: TaskDeletedDomainEvent) -> None:
        """Handle task deletion in read model."""
        # Option 1: Hard delete from read model
        await self._read_repository.remove_async(event.aggregate_id)

        # Option 2: Soft delete (mark as deleted)
        task = await self._read_repository.get_async(event.aggregate_id)
        if task:
            task.is_deleted = True
            task.deleted_at = event.timestamp
            await self._read_repository.update_async(task)
```

---

## Contact

Please reach out if you need additional context, use cases, or test scenarios to implement this enhancement.
