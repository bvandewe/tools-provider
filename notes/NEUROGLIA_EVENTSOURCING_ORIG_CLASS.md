# Neuroglia EventSourcingRepository: Generic Type Resolution via `__orig_class__`

## Summary

Research findings on how `EventSourcingRepository[Task, str]` resolves its generic type arguments at runtime and whether command handlers can inject `Repository[Task, str]` directly instead of using `EventSourcingTaskRepository`.

**TL;DR**: Yes, you CAN inject `Repository[Task, str]` directly IF:

1. The repository is created via `DataAccessLayer.WriteModel` (or any factory using subscript notation `EventSourcingRepository[Task, str]()`)
2. You DO NOT use a concrete subclass like `EventSourcingTaskRepository`

---

## The `__orig_class__` Mechanism

### What is `__orig_class__`?

Python's `typing` module sets `__orig_class__` on instances when a generic class is instantiated using subscript notation:

```python
# __orig_class__ IS SET
repo = EventSourcingRepository[Task, str]()
# repo.__orig_class__ = EventSourcingRepository[Task, str]
# repo.__orig_class__.__args__ = (Task, str)

# __orig_class__ is NOT SET
class TaskRepo(EventSourcingRepository[Task, str]):
    pass
repo = TaskRepo()
# repo.__orig_class__ → AttributeError!
```

### How Neuroglia Uses `__orig_class__`

The `EventSourcingRepository` class relies on `__orig_class__` in two critical methods:

```python
# event_sourcing_repository.py, lines 119 and 252

def _build_stream_id_for(self, aggregate_id: TKey):
    """Builds a new stream id for the specified aggregate"""
    aggregate_name = self.__orig_class__.__args__[0].__name__  # ← Uses __orig_class__
    return f"{aggregate_name.lower()}-{aggregate_id}"

async def get_async(self, id: TKey) -> Optional[TAggregate]:
    """Gets the aggregate with the specified id, if any"""
    stream_id = self._build_stream_id_for(id)
    events = await self._eventstore.read_async(stream_id, StreamReadDirection.FORWARDS, 0)
    return self._aggregator.aggregate(events, self.__orig_class__.__args__[0])  # ← Uses __orig_class__
```

---

## DataAccessLayer.WriteModel Behavior

### How It Creates Repositories

Looking at `data_access_layer.py`:

```python
# neuroglia/hosting/configuration/data_access_layer.py, lines 124-129

def make_factory(et, kt, opts):
    def repository_factory(sp: ServiceProvider):
        return EventSourcingRepository[et, kt](  # ← Subscript notation!
            eventstore=sp.get_required_service(EventStore),
            aggregator=sp.get_required_service(Aggregator),
            mediator=sp.get_service(Mediator),
            options=opts,
        )
    return repository_factory
```

**Key Insight**: Because `DataAccessLayer.WriteModel` uses subscript notation (`EventSourcingRepository[et, kt]()`), the created instance WILL have `__orig_class__` set correctly.

### Service Registration

```python
builder.services.add_singleton(
    Repository[aggregate_type, key_type],  # Service type
    implementation_factory=make_factory(aggregate_type, key_type, typed_options),
)
```

This registers `Repository[Task, str]` → `EventSourcingRepository[Task, str]` with the factory that creates properly subscripted instances.

---

## Why `EventSourcingTaskRepository` Was Created

The current codebase has `EventSourcingTaskRepository` that overrides `_build_stream_id_for` and `get_async`:

```python
# eventsourcing_task_repository.py

class EventSourcingTaskRepository(EventSourcingRepository[Task, str]):

    def _build_stream_id_for(self, aggregate_id: str) -> str:
        """Overrides base class to avoid __orig_class__ lookup issue."""
        return f"task-{aggregate_id}"  # Hardcoded!

    async def get_async(self, id: str) -> Task | None:
        """Overrides base class to avoid __orig_class__ lookup issue."""
        stream_id = self._build_stream_id_for(id)
        events = await self._eventstore.read_async(stream_id, StreamReadDirection.FORWARDS, 0)
        return self._aggregator.aggregate(events, Task)  # Hardcoded!
```

This was necessary because:

1. The subclass is instantiated as `EventSourcingTaskRepository()` (no subscript)
2. Without subscript notation, `__orig_class__` is NOT set
3. The base class methods would fail with `AttributeError`

---

## Test Results

### Scenario 1: Factory with Subscript Notation ✅

```python
def make_factory(et, kt):
    def factory():
        return EventSourcingRepository[et, kt]()  # Subscript!
    return factory

repo = make_factory(Task, str)()
# repo.__orig_class__ = EventSourcingRepository[Task, str]
# repo._build_stream_id_for("123") → "task-123" ✅
# repo.get_async("123") works ✅
```

### Scenario 2: Concrete Subclass Without Overrides ❌

```python
class TaskRepo(EventSourcingRepository[Task, str]):
    pass  # No overrides

repo = TaskRepo()
# repo.__orig_class__ → AttributeError!
# repo._build_stream_id_for("123") → AttributeError ❌
```

### Scenario 3: Concrete Subclass With Overrides ✅

```python
class TaskRepo(EventSourcingRepository[Task, str]):
    def _build_stream_id_for(self, aggregate_id: str) -> str:
        return f"task-{aggregate_id}"  # Hardcoded

    async def get_async(self, id: str) -> Task | None:
        # ... hardcoded Task type
        return self._aggregator.aggregate(events, Task)

repo = TaskRepo()
# Works because methods are overridden ✅
```

---

## Recommendations

### Option A: Use `Repository[Task, str]` Directly (Recommended)

If you rely solely on `DataAccessLayer.WriteModel` to create repositories:

1. **Remove** `EventSourcingTaskRepository` subclass
2. **Inject** `Repository[Task, str]` in command handlers
3. **Let** the framework handle type resolution via `__orig_class__`

**Changes to `main.py`:**

```python
# BEFORE
def task_repository_factory(sp: ServiceProvider) -> EventSourcingTaskRepository:
    return EventSourcingTaskRepository(...)

builder.services.add_scoped(EventSourcingTaskRepository, implementation_factory=task_repository_factory)

# AFTER - Just use DataAccessLayer.WriteModel, no custom registration needed!
DataAccessLayer.WriteModel(
    options=EventSourcingRepositoryOptions(delete_mode=DeleteMode.HARD),
).configure(builder, ["domain.entities"])
# Repository[Task, str] is automatically registered
```

**Changes to command handlers:**

```python
# BEFORE
class CreateTaskCommandHandler:
    def __init__(self, task_repository: EventSourcingTaskRepository, ...):
        ...

# AFTER
from neuroglia.data.infrastructure.abstractions import Repository

class CreateTaskCommandHandler:
    def __init__(self, task_repository: Repository[Task, str], ...):
        ...
```

### Option B: Keep Subclass (If Customization Needed)

Keep `EventSourcingTaskRepository` if you need:

- Custom stream naming conventions
- Additional repository methods
- Explicit type safety without relying on `__orig_class__`

But ensure you:

1. Override `_build_stream_id_for()` and `get_async()`
2. Use the concrete type in command handler injection

---

## Technical Details: How `__orig_class__` Gets Set

Python's `typing.Generic.__class_getitem__` returns a `_GenericAlias` that, when called:

```python
class _GenericAlias:
    def __call__(self, *args, **kwargs):
        result = self.__origin__(*args, **kwargs)
        result.__orig_class__ = self  # ← Magic happens here!
        return result
```

This only happens when using subscript notation (`Foo[Bar]()`), not when directly instantiating a subclass (`FooBar()`).

---

## References

- Python typing module: https://docs.python.org/3/library/typing.html
- PEP 560 – Core support for typing: https://peps.python.org/pep-0560/
- Neuroglia EventSourcingRepository: `.venv/lib/python3.12/site-packages/neuroglia/data/infrastructure/event_sourcing/event_sourcing_repository.py`
- Neuroglia DataAccessLayer: `.venv/lib/python3.12/site-packages/neuroglia/hosting/configuration/data_access_layer.py`
