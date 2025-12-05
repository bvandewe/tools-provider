# Neuroglia Change Request: kurrentdbclient Compatibility Fix

## Summary

`neuroglia-python` 0.7.0 has a bug in `ESEventStore._ensure_client()` that makes it incompatible with `kurrentdbclient`. The code incorrectly awaits the `AsyncKurrentDBClient` constructor and fails to call the required `connect()` method.

## Environment

- **neuroglia-python**: 0.7.0
- **kurrentdbclient**: 1.0.7
- **KurrentDB Server**: 25.0.0

## Problem Description

### Current Code (broken)

In `neuroglia/data/infrastructure/event_sourcing/event_store/event_store.py`:

```python
from kurrentdbclient import AsyncKurrentDBClient as AsyncClientFactory

class ESEventStore(EventStore):
    async def _ensure_client(self) -> Any:
        """Lazily initialize the async EventStoreDB client on first use"""
        if self._eventstore_client is None:
            if self._connection_string is None:
                raise RuntimeError("Neither connection string nor client provided")
            self._eventstore_client = await AsyncClientFactory(uri=self._connection_string)  # ❌ BUG
        return self._eventstore_client
```

### Issues

1. **`AsyncKurrentDBClient(uri=...)` is NOT awaitable** - It returns a client instance directly, not a coroutine. Awaiting it causes:

   ```
   TypeError: object AsyncKurrentDBClient can't be used in 'await' expression
   ```

2. **Missing `connect()` call** - After creating the client, `await client.connect()` must be called to establish the connection. Without it:

   ```
   AttributeError: 'AsyncKurrentDBClient' object has no attribute '_connection'
   ```

### Root Cause

The `esdbclient` library (predecessor) had a different API where `AsyncEventStoreDBClient(uri=...)` was awaitable. The `kurrentdbclient` library changed this API:

- Constructor returns client instance directly (not awaitable)
- Explicit `await client.connect()` is required to establish the connection

## Proposed Fix

```python
from kurrentdbclient import AsyncKurrentDBClient as AsyncClientFactory

class ESEventStore(EventStore):
    async def _ensure_client(self) -> Any:
        """Lazily initialize the async KurrentDB client on first use"""
        if self._eventstore_client is None:
            if self._connection_string is None:
                raise RuntimeError("Neither connection string nor client provided")
            # AsyncKurrentDBClient constructor is NOT awaitable - returns client directly
            client = AsyncClientFactory(uri=self._connection_string)
            # Must call connect() to establish the connection
            await client.connect()
            self._eventstore_client = client
        return self._eventstore_client
```

## Workaround

Until this is fixed in `neuroglia-python`, users can apply a runtime patch:

```python
# patches.py
import logging
from typing import Any

log = logging.getLogger(__name__)

def patch_neuroglia_eseventstore_ensure_client() -> None:
    """Fix neuroglia-python 0.7.0 kurrentdbclient compatibility bug"""
    from kurrentdbclient import AsyncKurrentDBClient
    from neuroglia.data.infrastructure.event_sourcing.event_store.event_store import ESEventStore

    async def patched_ensure_client(self: Any) -> Any:
        """Lazily initialize the async KurrentDB client on first use"""
        if self._eventstore_client is None:
            if self._connection_string is None:
                raise RuntimeError("Neither connection string nor client provided")
            client = AsyncKurrentDBClient(uri=self._connection_string)
            await client.connect()
            self._eventstore_client = client
            log.debug(f"KurrentDB client connected to {self._connection_string}")
        return self._eventstore_client

    ESEventStore._ensure_client = patched_ensure_client
    log.info("Patched neuroglia ESEventStore._ensure_client() for kurrentdbclient compatibility")

# Apply patch before any neuroglia initialization
patch_neuroglia_eseventstore_ensure_client()
```

## Impact

- **Severity**: Critical - Application fails to start
- **Affected Components**: Any application using `neuroglia-python` with `kurrentdbclient` 1.0.x
- **Error Messages**:
  1. `TypeError: object AsyncKurrentDBClient can't be used in 'await' expression`
  2. `AttributeError: 'AsyncKurrentDBClient' object has no attribute '_connection'`

## Additional Notes

### kurrentdbclient API Reference

```python
from kurrentdbclient import AsyncKurrentDBClient

# Create client (NOT awaitable)
client = AsyncKurrentDBClient(uri="esdb://localhost:2113?tls=false")

# Connect (IS awaitable - establishes connection)
await client.connect()

# Now client can be used
await client.append_to_stream(...)
```

### Alternative: Use async context manager

`AsyncKurrentDBClient` also supports async context manager:

```python
async with AsyncKurrentDBClient(uri="esdb://...") as client:
    # client is automatically connected
    await client.append_to_stream(...)
```

However, this pattern may not fit well with the lazy initialization pattern used in `ESEventStore`.

## References

- kurrentdbclient repository: https://github.com/pyeventsourcing/kurrentdbclient
- Original esdbclient issue: https://github.com/pyeventsourcing/kurrentdbclient/issues/35

---

**Requested by**: tools-provider team
**Date**: 2025-12-02
**Priority**: High
