# Neuroglia Aggregator Missing _pending_events Initialization Bug Report

## Bug Summary

`Aggregator.aggregate()` rehydrates aggregates using `object.__new__()` which bypasses `__init__`, resulting in aggregates without the `_pending_events` attribute. While `register_event()` lazily initializes this attribute, `_do_update_async()` does not check for its existence before accessing it.

## Expected Behavior

Aggregates rehydrated from event streams should be fully functional, including the ability to:

- Register new domain events
- Be updated via `repository.update_async()`

## Actual Behavior

When calling `update_async()` on a rehydrated aggregate that has no pending events:

```
AttributeError: 'SourceTool' object has no attribute '_pending_events'
```

## Root Cause

In `neuroglia/data/infrastructure/event_sourcing/abstractions.py`, the `Aggregator.aggregate()` method uses `object.__new__()` which doesn't call `__init__`, so `_pending_events` is never initialized:

```python
def aggregate(self, events: list, aggregate_type: type):
    aggregate: AggregateRoot = object.__new__(aggregate_type)  # <-- Bypasses __init__
    aggregate.state = aggregate.__orig_bases__[0].__args__[0]()
    # _pending_events is never initialized!
    ...
```

While `register_event()` handles this gracefully:

```python
def register_event(self, e: TEvent) -> TEvent:
    if not hasattr(self, "_pending_events"):
        self._pending_events = list[DomainEvent]()  # <-- Lazy init
    ...
```

The `_do_update_async()` does NOT:

```python
async def _do_update_async(self, aggregate: TAggregate) -> TAggregate:
    events = aggregate._pending_events  # <-- AttributeError if not initialized!
    if len(events) < 1:
        raise Exception("No pending events to persist")
    ...
```

## Impact

This causes issues when:

1. An aggregate is rehydrated via `get_async()`
2. A method is called that does NOT emit events (e.g., updating a timestamp)
3. `update_async()` is called, expecting to persist changes

## Workaround

1. **Don't call `update_async()` if no events were registered:**

   ```python
   entity = await repository.get_async(id)
   entity.some_non_event_method()  # Doesn't emit events
   # DON'T call update_async() - nothing to persist!
   ```

2. **For methods that SHOULD emit events, they'll work because `register_event()` handles lazy init.**

## Suggested Fix

Modify `_do_update_async()` to handle missing `_pending_events`:

```python
async def _do_update_async(self, aggregate: TAggregate) -> TAggregate:
    events = getattr(aggregate, '_pending_events', [])  # Safe access
    if len(events) < 1:
        raise Exception("No pending events to persist")
    ...
```

Or initialize `_pending_events` in the `Aggregator.aggregate()` method:

```python
def aggregate(self, events: list, aggregate_type: type):
    aggregate: AggregateRoot = object.__new__(aggregate_type)
    aggregate._pending_events = []  # <-- ADD THIS LINE
    aggregate.state = aggregate.__orig_bases__[0].__args__[0]()
    ...
```

## Environment

- **Python**: 3.11+
- **neuroglia-framework**: latest
- **EventStoreDB**: 24.x

## Related Files

- `neuroglia/data/infrastructure/event_sourcing/abstractions.py` (Aggregator.aggregate)
- `neuroglia/data/infrastructure/event_sourcing/event_sourcing_repository.py` (_do_update_async)
- `neuroglia/data/abstractions.py` (AggregateRoot.**init**, register_event)

## Priority

**Medium** - The workaround (not calling update_async when there are no events) is straightforward, but the inconsistency between `register_event()` and `_do_update_async()` is confusing.
