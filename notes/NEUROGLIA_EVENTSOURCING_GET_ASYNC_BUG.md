# Neuroglia EventSourcingRepository.get_async() Bug Report

## Bug Summary

`EventSourcingRepository.get_async()` raises `esdbclient.exceptions.NotFound` instead of returning `None` when the aggregate's event stream doesn't exist.

## Expected Behavior

According to the method signature `async def get_async(self, id: TKey) -> Optional[TAggregate]`, the method should:

- Return the aggregate if found
- Return `None` if the aggregate doesn't exist

## Actual Behavior

When calling `get_async()` for a non-existent aggregate, the method raises:

```
esdbclient.exceptions.NotFound: Stream 'sourcetool-{id}' not found
```

## Root Cause

In `neuroglia/data/infrastructure/event_sourcing/event_sourcing_repository.py`:

```python
async def get_async(self, id: TKey) -> Optional[TAggregate]:
    """Gets the aggregate with the specified id, if any"""
    stream_id = self._build_stream_id_for(id)
    events = await self._eventstore.read_async(stream_id, StreamReadDirection.FORWARDS, 0)
    return self._aggregator.aggregate(events, self.__orig_class__.__args__[0])
```

The `read_async` call propagates the `NotFound` exception from `esdbclient` when the stream doesn't exist, rather than handling it.

## Impact

This breaks common repository patterns like:

```python
# This pattern fails with NotFound instead of returning None
existing = await repository.get_async(id)
if existing is None:
    # Create new aggregate
    new_aggregate = MyAggregate(...)
    await repository.add_async(new_aggregate)
else:
    # Update existing
    existing.update(...)
    await repository.update_async(existing)
```

## Workaround

Catch the `kurrentdbclient.exceptions.NotFoundError` exception in application code:

```python
from kurrentdbclient.exceptions import NotFoundError as StreamNotFound

try:
    existing = await repository.get_async(id)
except StreamNotFound:
    existing = None

if existing is None:
    # Create new aggregate
    ...
```

Note: If using `esdbclient` directly (older versions), the exception is `esdbclient.exceptions.NotFound`.

## Suggested Fix

Modify `get_async()` to handle the `NotFound` exception:

```python
from esdbclient.exceptions import NotFound

async def get_async(self, id: TKey) -> Optional[TAggregate]:
    """Gets the aggregate with the specified id, if any"""
    stream_id = self._build_stream_id_for(id)
    try:
        events = await self._eventstore.read_async(stream_id, StreamReadDirection.FORWARDS, 0)
    except NotFound:
        return None
    return self._aggregator.aggregate(events, self.__orig_class__.__args__[0])
```

Alternatively, use `contains_async()` first:

```python
async def get_async(self, id: TKey) -> Optional[TAggregate]:
    """Gets the aggregate with the specified id, if any"""
    if not await self.contains_async(id):
        return None
    stream_id = self._build_stream_id_for(id)
    events = await self._eventstore.read_async(stream_id, StreamReadDirection.FORWARDS, 0)
    return self._aggregator.aggregate(events, self.__orig_class__.__args__[0])
```

## Environment

- **Python**: 3.12
- **neuroglia-framework**: latest
- **esdbclient**: 1.1
- **EventStoreDB**: 24.x

## Related Files

- `neuroglia/data/infrastructure/event_sourcing/event_sourcing_repository.py` (lines 115-120)
- `neuroglia/data/infrastructure/event_sourcing/event_store/event_store.py` (read_async method)

## Reproduction Steps

1. Create an EventSourcingRepository for an aggregate type
2. Call `get_async("non-existent-id")`
3. Observe `NotFound` exception instead of `None` return value

## Priority

**Medium-High** - This breaks common repository patterns and requires workarounds in all application code that checks for aggregate existence.
