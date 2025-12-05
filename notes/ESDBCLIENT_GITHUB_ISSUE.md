# GitHub Issue: AsyncPersistentSubscription Missing subscription_id Propagation

**Repository**: https://github.com/pyeventsourcing/esdbclient

## Issue Title

`AsyncPersistentSubscription.init()` doesn't propagate `subscription_id` to `_read_reqs`, causing ACKs to be silently ignored

## Issue Body

### Summary

The `AsyncPersistentSubscription.init()` method is missing a line that exists in the synchronous `PersistentSubscription.__init__()`. This causes ACK messages to be sent with an empty `subscription_id` field, which EventStoreDB silently ignores. The result is that events are redelivered after `message_timeout` expires, despite being successfully ACKed by the client.

### esdbclient Version

- **esdbclient**: 1.1.7 (latest as of December 2025)
- **Python**: 3.12
- **EventStoreDB**: 24.10.x

### Bug Location

**File**: `esdbclient/persistent.py`

### The Problem

The sync version `PersistentSubscription.__init__()` has:

```python
self._read_reqs.subscription_id = subscription_id.encode()
```

But the async version `AsyncPersistentSubscription.init()` is **missing this line**.

### Evidence

When logging the gRPC ACK messages being sent, the `subscription_id` field is empty:

```
🚀 gRPC _write: SENDING ACK to server: subscription_id=, ids=['6181abcf-354f-44c0-918e-1cd58bdb7296']
```

After patching:

```
🚀 gRPC _write: SENDING ACK to server: subscription_id=$ce-tools_provider::tools_provider_group, ids=['9fa3bc62-51c6-48e1-a7b8-4305d32deb78']
```

### Symptoms

1. Events are processed successfully but ACKs are silently ignored by EventStoreDB
2. Subscription checkpoint never advances
3. Events are redelivered every `message_timeout` seconds (default: 30s)
4. No errors or exceptions are raised - the bug is completely silent
5. `inFlightMessages` in subscription info stays constant

### Suggested Fix

Add the missing line to `AsyncPersistentSubscription.init()`:

```python
async def init(self) -> None:
    # ... existing code ...

    # Add this line (matching the sync version):
    self._read_reqs.subscription_id = self._subscription_id.encode()
```

### Workaround

We're using a runtime patch:

```python
from esdbclient.persistent import AsyncPersistentSubscription

original_init = AsyncPersistentSubscription.init

async def patched_init(self) -> None:
    await original_init(self)
    if hasattr(self, '_subscription_id') and hasattr(self, '_read_reqs'):
        self._read_reqs.subscription_id = self._subscription_id.encode()

AsyncPersistentSubscription.init = patched_init
```

### Steps to Reproduce

1. Create an async persistent subscription using `AsyncEventStoreDBClient`
2. Subscribe to events and ACK them using `subscription.ack(event)`
3. Observe that the subscription checkpoint never advances
4. Wait for `message_timeout` - events are redelivered

### Environment

- OS: macOS / Linux (Docker)
- Python: 3.12
- esdbclient: 1.1.7
- EventStoreDB: 24.10.x (Docker image)

### Related Code

The sync implementation in `PersistentSubscription.__init__()` correctly sets the subscription_id:
https://github.com/pyeventsourcing/esdbclient/blob/main/esdbclient/persistent.py

---

## Labels to Apply

- bug
- async
- persistent-subscriptions
