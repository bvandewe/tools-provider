# Neuroglia Framework Change Request

**Version Affected:** 0.6.12 → 0.6.13
**Date:** December 1, 2025
**Submitted By:** tools-provider team
**Priority:** High (Blocking Issue)
**Status:** ✅ **RESOLVED in v0.6.13** (with one outstanding issue)

---

## Resolution Summary

Most issues documented in this change request have been fixed in **neuroglia-python v0.6.13**.

The following fixes were applied:

1. ✅ **EventSourcingRepository** - Now implements `_do_add_async`, `_do_update_async`, `_do_remove_async`
2. ✅ **MongoRepository** - Now implements `_do_add_async`, `_do_update_async`, `_do_remove_async`
3. ✅ **queryable.py** - Now imports `List` from typing
4. ✅ **mongo_repository.py** - Now imports `List` from typing
5. ✅ **ReadModelReconciliator** - Now uses `call_soon_threadsafe` instead of `asyncio.run()`

**Runtime patches in `src/patches.py` have been removed** - the file now contains only a no-op function for backward compatibility.

---

## Outstanding Issue: EventSourcingRepository Clears Events Before Publishing

**Status:** ⚠️ **STILL OPEN in v0.6.13**

### Problem

The `EventSourcingRepository._do_add_async()` calls `aggregate.clear_pending_events()` at the end:

```python
# event_sourcing_repository.py, line 47-58
async def _do_add_async(self, aggregate: TAggregate) -> TAggregate:
    stream_id = self._build_stream_id_for(aggregate.id())
    events = aggregate._pending_events
    ...
    aggregate.clear_pending_events()  # ❌ Events cleared HERE
    return aggregate
```

Then the base class `Repository.add_async()` calls:

```python
result = await self._do_add_async(entity)
await self._publish_domain_events(entity)  # ❌ Events already cleared!
```

This means the base class's automatic domain event publishing via `_publish_domain_events()` does NOT work for `EventSourcingRepository`, because events are already cleared.

### Current Workaround

Command handlers must manually capture and publish events:

```python
# In CreateTaskCommandHandler.handle_async():
events = list(task._pending_events)  # Capture before repository clears them
saved_task = await self.task_repository.add_async(task)

# Manually publish since repository clears events before base class can publish
for event in events:
    await self.mediator.publish_async(event)
```

### Proposed Fix

Remove `clear_pending_events()` from `EventSourcingRepository._do_add_async()` and `_do_update_async()`. The base class `_publish_domain_events()` already clears events after publishing:

```python
# abstractions.py, line 207-208
if hasattr(entity, "clear_pending_events"):
    entity.clear_pending_events()
```

**File:** `neuroglia/data/infrastructure/event_sourcing/event_sourcing_repository.py`

---

## Original Issue Documentation (Historical)

The following sections document the original issues found in v0.6.12 for historical reference.

---

## Issue 1: EventSourcingRepository Cannot Be Instantiated

### Error Message

```
TypeError: Can't instantiate abstract class EventSourcingRepository with abstract methods _do_add_async, _do_remove_async, _do_update_async
```

### Root Cause

The `Repository` base class in `neuroglia/data/infrastructure/abstractions.py` defines abstract methods:

```python
@abstractmethod
async def _do_add_async(self, entity: TEntity) -> TEntity:
    """Subclasses must implement this method to provide the actual persistence logic."""
    ...

@abstractmethod
async def _do_update_async(self, entity: TEntity) -> TEntity:
    """Subclasses must implement this method to provide the actual persistence logic."""
    ...

@abstractmethod
async def _do_remove_async(self, id: TKey) -> None:
    """Subclasses must implement this method to provide the actual persistence logic."""
    ...
```

The base class's `add_async`, `update_async`, and `remove_async` methods follow a Template Method Pattern:

```python
async def add_async(self, entity: TEntity) -> TEntity:
    result = await self._do_add_async(entity)  # Calls abstract method
    await self._publish_domain_events(entity)
    return result
```

However, `EventSourcingRepository` in `neuroglia/data/infrastructure/event_sourcing/event_sourcing_repository.py` **overrides** `add_async`, `update_async`, `remove_async` directly without implementing the `_do_*` abstract methods:

```python
# Current implementation (lines 43-67)
async def add_async(self, aggregate: TAggregate) -> TAggregate:
    """Adds and persists the specified aggregate"""
    stream_id = self._build_stream_id_for(aggregate.id())
    events = aggregate._pending_events
    if len(events) < 1:
        raise Exception()
    encoded_events = [self._encode_event(e) for e in events]
    await self._eventstore.append_async(stream_id, encoded_events)
    aggregate.state.state_version = events[-1].aggregate_version
    aggregate.clear_pending_events()
    return aggregate
```

Since `EventSourcingRepository` extends `Repository[TAggregate, TKey]` but doesn't implement the `_do_*` abstract methods, Python's ABC mechanism prevents instantiation.

### Proposed Fix

**Option A (Recommended):** Make `EventSourcingRepository` follow the Template Method Pattern

Rename the method implementations to `_do_*` and let the base class handle event publishing:

```python
class EventSourcingRepository(Generic[TAggregate, TKey], Repository[TAggregate, TKey]):
    """Represents an event sourcing repository implementation"""

    def __init__(self, eventstore: EventStore, aggregator: Aggregator, mediator: Optional["Mediator"] = None):
        super().__init__(mediator)  # Pass mediator to base class
        self._eventstore = eventstore
        self._aggregator = aggregator

    async def _do_add_async(self, aggregate: TAggregate) -> TAggregate:
        """Adds and persists the specified aggregate"""
        stream_id = self._build_stream_id_for(aggregate.id())
        events = aggregate._pending_events
        if len(events) < 1:
            raise Exception("No pending events to persist")
        encoded_events = [self._encode_event(e) for e in events]
        await self._eventstore.append_async(stream_id, encoded_events)
        aggregate.state.state_version = events[-1].aggregate_version
        aggregate.clear_pending_events()
        return aggregate

    async def _do_update_async(self, aggregate: TAggregate) -> TAggregate:
        """Persists the changes made to the specified aggregate"""
        stream_id = self._build_stream_id_for(aggregate.id())
        events = aggregate._pending_events
        if len(events) < 1:
            raise Exception("No pending events to persist")
        encoded_events = [self._encode_event(e) for e in events]
        await self._eventstore.append_async(stream_id, encoded_events, aggregate.state.state_version)
        aggregate.state.state_version = events[-1].aggregate_version
        aggregate.clear_pending_events()
        return aggregate

    async def _do_remove_async(self, id: TKey) -> None:
        """Removes the aggregate root with the specified key, if any"""
        raise NotImplementedError("Event sourcing repositories do not support hard deletes")
```

**Option B:** Keep override pattern but add stub implementations

If you prefer to keep the direct `add_async`/`update_async` overrides (bypassing the base class template), you still need to implement the abstract methods as stubs:

```python
async def _do_add_async(self, entity: TAggregate) -> TAggregate:
    raise NotImplementedError("Use add_async directly")

async def _do_update_async(self, entity: TAggregate) -> TAggregate:
    raise NotImplementedError("Use update_async directly")

async def _do_remove_async(self, id: TKey) -> None:
    raise NotImplementedError("Use remove_async directly")
```

### File to Modify

`neuroglia/data/infrastructure/event_sourcing/event_sourcing_repository.py`

---

## Issue 2: MongoRepository Cannot Be Instantiated

### Error Message

```
TypeError: Can't instantiate abstract class MongoRepository with abstract methods _do_add_async, _do_remove_async, _do_update_async
```

### Root Cause

Same issue as EventSourcingRepository. The `MongoRepository` class has `add_async`, `update_async`, `remove_async` methods but doesn't implement the `_do_*` abstract methods required by the base `Repository` class.

### Proposed Fix

Rename the existing implementations to follow the Template Method Pattern:

```python
# In MongoRepository class

async def _do_add_async(self, entity: TEntity) -> TEntity:
    """Persist entity to MongoDB"""
    # Current add_async logic goes here
    ...

async def _do_update_async(self, entity: TEntity) -> TEntity:
    """Update entity in MongoDB"""
    # Current update_async logic goes here
    ...

async def _do_remove_async(self, id: TKey) -> None:
    """Remove entity from MongoDB"""
    # Current remove_async logic goes here
    ...
```

Then remove the overriding `add_async`, `update_async`, `remove_async` methods so the base class's template methods are used (which call `_do_*` and then publish events).

### File to Modify

`neuroglia/data/infrastructure/mongo/mongo_repository.py`

---

## Issue 3: Missing `List` Import in queryable.py

### Error Message

```
NameError: name 'List' is not defined
```

### Root Cause

The file `neuroglia/data/queryable.py` uses `List` at line 230 but doesn't import it:

```python
# Line 230
return self.provider.execute(self.expression, List)
```

Current imports (lines 1-8):

```python
import ast
import inspect
import os
from abc import ABC, abstractclassmethod
from ast import Attribute, Name, NodeTransformer, expr
from collections.abc import Callable
from typing import Any, Generic, Optional, TypeVar
```

`List` is not imported from `typing`.

### Proposed Fix

Add `List` to the typing imports:

```python
from typing import Any, Generic, List, Optional, TypeVar
```

### File to Modify

`neuroglia/data/queryable.py` - Line 7

---

## Issue 4: Missing `List` Import in mongo_repository.py

### Error Message

```
NameError: name 'List' is not defined
```

### Root Cause

The file `neuroglia/data/infrastructure/mongo/mongo_repository.py` uses `List` at lines 118-119 but doesn't import it:

```python
# Lines 118-119
type_ = query_type if isclass(query_type) or query_type == List else type(query_type)
if issubclass(type_, List):
```

Current imports (lines 1-6):

```python
import ast
from ast import NodeVisitor, expr
from dataclasses import dataclass
from inspect import isclass
from typing import Any, Generic, Optional
```

`List` is not imported from `typing`.

### Proposed Fix

Add `List` to the typing imports:

```python
from typing import Any, Generic, List, Optional
```

### File to Modify

`neuroglia/data/infrastructure/mongo/mongo_repository.py` - Line 6

---

## Current Workaround

We have implemented runtime monkey-patches in our application to work around these issues. This is not a sustainable solution and causes:

1. Fragile code that may break with future updates
2. Patches must be applied before any neuroglia imports occur
3. Confusion for developers debugging issues

**Workaround file:** `src/patches.py`

```python
from neuroglia.data.infrastructure.event_sourcing.event_sourcing_repository import EventSourcingRepository
from neuroglia.data.infrastructure.mongo.mongo_repository import MongoRepository


def apply_patches() -> None:
    """Applies runtime patches to fix issues in the neuroglia library."""

    # Patch MongoRepository
    if not hasattr(MongoRepository, "_do_add_async"):
        MongoRepository._do_add_async = MongoRepository.add_async

    if not hasattr(MongoRepository, "_do_update_async"):
        MongoRepository._do_update_async = MongoRepository.update_async

    if not hasattr(MongoRepository, "_do_remove_async"):
        MongoRepository._do_remove_async = MongoRepository.remove_async

    if hasattr(MongoRepository, "__abstractmethods__"):
        MongoRepository.__abstractmethods__ = frozenset(
            m for m in MongoRepository.__abstractmethods__
            if m not in ["_do_add_async", "_do_update_async", "_do_remove_async"]
        )

    # Patch EventSourcingRepository with stub implementations
    async def _esr_do_add_async(self, entity):
        raise NotImplementedError("EventSourcingRepository.add_async should be called directly")

    async def _esr_do_update_async(self, entity):
        raise NotImplementedError("EventSourcingRepository.update_async should be called directly")

    async def _esr_do_remove_async(self, id):
        raise NotImplementedError("EventSourcingRepository.remove_async should be called directly")

    if "_do_add_async" in getattr(EventSourcingRepository, "__abstractmethods__", frozenset()):
        EventSourcingRepository._do_add_async = _esr_do_add_async
        EventSourcingRepository._do_update_async = _esr_do_update_async
        EventSourcingRepository._do_remove_async = _esr_do_remove_async

    if hasattr(EventSourcingRepository, "__abstractmethods__"):
        EventSourcingRepository.__abstractmethods__ = frozenset(
            m for m in EventSourcingRepository.__abstractmethods__
            if m not in ["_do_add_async", "_do_update_async", "_do_remove_async"]
        )

    # Patch missing List imports
    from typing import List

    import neuroglia.data.queryable
    if not hasattr(neuroglia.data.queryable, "List"):
        neuroglia.data.queryable.List = List

    import neuroglia.data.infrastructure.mongo.mongo_repository
    if not hasattr(neuroglia.data.infrastructure.mongo.mongo_repository, "List"):
        neuroglia.data.infrastructure.mongo.mongo_repository.List = List
```

---

## Summary of Changes Requested

| Issue | File | Change |
|-------|------|--------|
| 1 | `event_sourcing_repository.py` | Implement `_do_add_async`, `_do_update_async`, `_do_remove_async` |
| 2 | `mongo_repository.py` | Implement `_do_add_async`, `_do_update_async`, `_do_remove_async` |
| 3 | `queryable.py` | Add `List` to imports from `typing` |
| 4 | `mongo_repository.py` | Add `List` to imports from `typing` |
| 5 | `read_model_reconciliator.py` | Replace `asyncio.run()` with proper async scheduling |

---

## Issue 5: ReadModelReconciliator Breaks Motor Event Loop

### Error Message

```
RuntimeError: Event loop is closed
```

This error occurs when querying MongoDB after the `ReadModelReconciliator` has processed events.

### Root Cause

The `ReadModelReconciliator.subscribe_async()` method uses `asyncio.run()` inside its RxPY subscription callback:

```python
# neuroglia/data/infrastructure/event_sourcing/read_model_reconciliator.py, line 47
async def subscribe_async(self):
    observable = await self._event_store.observe_async(f'$ce-{self._event_store_options.database_name}', self._event_store_options.consumer_group)
    self._subscription = AsyncRx.subscribe(observable, lambda e: asyncio.run(self.on_event_record_stream_next_async(e)))
```

`asyncio.run()` creates a new event loop and **closes it when done**. This breaks Motor's MongoDB client because:

1. Motor's async cursor is bound to the main application event loop
2. When `asyncio.run()` closes its temporary loop, Motor's internal state becomes corrupted
3. Subsequent Motor operations fail with "Event loop is closed"

### Proposed Fix

Replace `asyncio.run()` with thread-safe scheduling to the main event loop:

```python
async def subscribe_async(self):
    observable = await self._event_store.observe_async(
        f'$ce-{self._event_store_options.database_name}',
        self._event_store_options.consumer_group
    )

    # Get the current event loop to schedule tasks on
    loop = asyncio.get_event_loop()

    def on_next(e):
        """Schedule the async handler on the main event loop."""
        try:
            loop.call_soon_threadsafe(
                lambda: asyncio.create_task(self.on_event_record_stream_next_async(e))
            )
        except RuntimeError:
            logging.warning(f"Event loop closed, skipping event: {type(e.data).__name__}")

    self._subscription = AsyncRx.subscribe(observable, on_next)
```

### File to Modify

`neuroglia/data/infrastructure/event_sourcing/read_model_reconciliator.py`

---

## Testing Verification

After applying these fixes, the following should work without errors:

```python
from neuroglia.data.infrastructure.event_sourcing.event_sourcing_repository import EventSourcingRepository
from neuroglia.data.infrastructure.mongo.mongo_repository import MongoRepository
from neuroglia.data.queryable import Queryable

# Should be instantiable
repo = EventSourcingRepository[MyAggregate, str](eventstore, aggregator)
mongo_repo = MongoRepository[MyEntity, str](client, db, collection, MyEntity, serializer)

# Queryable should work
queryable = Queryable(...)
results = await queryable.to_list()

# ReadModelReconciliator should work with Motor without breaking event loop
# After creating an entity and having the reconciliator project it,
# subsequent Motor queries should work:
all_entities = await motor_repository.get_all_async()  # Should not raise "Event loop is closed"
```

---

## Contact

Please reach out if you need additional context or test cases to reproduce these issues.
