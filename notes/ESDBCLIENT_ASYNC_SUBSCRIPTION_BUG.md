# esdbclient Bug Report: AsyncPersistentSubscription Missing subscription_id Propagation

## Summary

The `AsyncPersistentSubscription` class in esdbclient v1.1.7 has a bug where the `subscription_id` is not propagated to `_read_reqs`, causing ACK messages to be sent with an empty subscription ID. This results in EventStoreDB silently ignoring ACKs, leading to infinite event redelivery.

## Affected Version

- **esdbclient**: 1.1.7 (and potentially earlier versions)
- **Python**: 3.12
- **EventStoreDB**: 24.10.x

## Bug Location

**File**: `esdbclient/persistent.py`

**Class**: `AsyncPersistentSubscription`

**Method**: `async def init(self)`

## Root Cause

The synchronous `PersistentSubscription.__init__()` correctly sets:

```python
self._read_reqs.subscription_id = subscription_id.encode()
```

However, the asynchronous `AsyncPersistentSubscription.init()` method is **missing** this line, causing ACKs to be sent without a subscription ID.

## Symptoms

1. Events are processed successfully but ACKs are silently ignored by EventStoreDB
2. Subscription checkpoint never advances
3. Events are redelivered every `message_timeout` seconds (default: 30s)
4. No errors or exceptions are raised - the bug is completely silent
5. `inFlightMessages` in subscription info stays constant or grows

## Evidence

### Before Fix (empty subscription_id)

```
🚀 gRPC _write: SENDING ACK to server: subscription_id=, ids=['6181abcf-354f-44c0-918e-1cd58bdb7296']
```

### After Fix (subscription_id populated)

```
🚀 gRPC _write: SENDING ACK to server: subscription_id=$ce-tools_provider::tools_provider_group, ids=['9fa3bc62-51c6-48e1-a7b8-4305d32deb78']
```

## Comparison: Sync vs Async Implementation

### Sync Version (CORRECT) - `PersistentSubscription.__init__`

```python
def __init__(
    self,
    ...
    subscription_id: str,
    ...
):
    ...
    self._subscription_id = subscription_id
    self._read_reqs = SubscriptionReadReqs()
    self._read_reqs.subscription_id = subscription_id.encode()  # ✅ Correctly set
    ...
```

### Async Version (BUG) - `AsyncPersistentSubscription.init`

```python
async def init(self) -> None:
    ...
    # ❌ Missing: self._read_reqs.subscription_id = self._subscription_id.encode()
    ...
```

## Workaround

We implemented a runtime patch in `src/patches.py`:

```python
def patch_esdbclient_async_subscription_id():
    """
    Fix esdbclient bug: AsyncPersistentSubscription.init() doesn't propagate
    subscription_id to _read_reqs, causing ACKs to be sent with empty subscription ID.
    """
    from esdbclient.persistent import AsyncPersistentSubscription

    original_init = AsyncPersistentSubscription.init

    async def patched_init(self) -> None:
        await original_init(self)
        # Propagate subscription_id to _read_reqs (missing in esdbclient async version)
        if hasattr(self, '_subscription_id') and hasattr(self, '_read_reqs'):
            self._read_reqs.subscription_id = self._subscription_id.encode()
            log.info(f"🔧 Fixed esdbclient: propagated subscription_id to _read_reqs: {self._subscription_id}")

    AsyncPersistentSubscription.init = patched_init
```

## Suggested Fix

In `esdbclient/persistent.py`, add the missing line to `AsyncPersistentSubscription.init()`:

```python
async def init(self) -> None:
    ...
    # Add this line (matching the sync version):
    self._read_reqs.subscription_id = self._subscription_id.encode()
    ...
```

## Impact

- **Severity**: High
- **Impact**: Silent data loss / infinite redelivery loop
- **Affected Feature**: Persistent subscriptions with async client

## Debugging Journey

1. Observed events being redelivered every 60 seconds despite successful processing
2. Traced ACK flow from application → Neuroglia → esdbclient → gRPC
3. Added gRPC `_write` tracing to inspect ACK messages
4. Discovered `subscription_id` field was empty in ACK protobuf messages
5. Compared sync vs async implementations, found missing line
6. Applied runtime patch to confirm fix

## Related

- **Repository**: https://github.com/pyeventsourcing/kurrentdbclient
- **Issue**: https://github.com/pyeventsourcing/kurrentdbclient/issues/35

## Test Case

To reproduce:

1. Create an async persistent subscription using `AsyncPersistentSubscription`
2. Subscribe to events and ACK them
3. Observe that checkpoint never advances
4. Wait for `message_timeout` - events are redelivered

## Additional Observations

After applying the patch, we observed:

1. ACKs were being sent with the correct `subscription_id`
2. gRPC `_write` reported success (no exceptions)
3. However, events were **still being redelivered** after the message timeout

This suggests either:

- The existing subscription connection was in a bad state and needed full reconnection
- There may be an additional issue with the ACK message format
- EventStoreDB may have already "given up" on the events (moved to parked messages)

The subscription showed 19 parked messages, indicating EventStoreDB had already exceeded retry limits for those events before the fix was applied.

**Recommendation**: After applying the fix, delete and recreate the subscription to start fresh, or replay parked messages after the fix is confirmed working.

## Date Discovered

December 1, 2025

## Discovered By

Investigation of EventStoreDB ACK failures in a Neuroglia-based CQRS+ES application (tools-provider service using Neuroglia Python framework).
