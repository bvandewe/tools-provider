# Neuroglia Team: esdbclient AsyncPersistentSubscription Bug & Patch

**Date**: December 2, 2025
**From**: tools-provider team
**Priority**: High
**Affects**: All Neuroglia applications using async EventStoreDB persistent subscriptions

---

## Summary

We discovered a bug in **esdbclient v1.1.7** (the latest version) that causes **persistent subscription ACKs to fail silently** when using the async client. This affects the `ReadModelReconciliator` and any component using `AsyncEventStoreDBClient` with persistent subscriptions.

**Symptoms**:

- Events are redelivered every `message_timeout` seconds despite being processed successfully
- Checkpoint never advances in EventStoreDB
- Events eventually get parked after `maxRetryCount` attempts
- Read models may process the same event multiple times

---

## Root Cause

The **`AsyncPersistentSubscription.init()`** method is missing a line that exists in the synchronous **`PersistentSubscription.__init__()`**.

### Sync Version (CORRECT) - `PersistentSubscription.__init__()`

```python
# esdbclient/persistent.py, line ~632
self._read_reqs.subscription_id = subscription_id.encode()
```

### Async Version (BUG) - `AsyncPersistentSubscription.init()`

```python
# esdbclient/persistent.py, lines ~517-518
# This line is MISSING!
# Only sets self._subscription_id, but never propagates it to _read_reqs
```

The `BaseSubscriptionReadReqs.__init__()` initializes `subscription_id = b""` (empty bytes). The sync version overwrites this with the correct value, but the async version never does. As a result, ACK messages are sent with an empty `subscription_id` field, which EventStoreDB silently ignores.

---

## The Patch

Add this to your application startup (before any EventStoreDB operations):

```python
import logging

log = logging.getLogger(__name__)


def patch_esdbclient_async_subscription_id():
    """
    Fix esdbclient bug: AsyncPersistentSubscription.init() doesn't propagate
    subscription_id to _read_reqs, causing ACKs to be sent with empty subscription ID.

    The sync version (PersistentSubscription) has this line in __init__:
        self._read_reqs.subscription_id = subscription_id.encode()

    But the async version (AsyncPersistentSubscription) is missing it!
    This causes ACKs to fail silently because EventStoreDB doesn't know which
    subscription the ACK is for.
    """
    from esdbclient.persistent import AsyncPersistentSubscription

    original_init = AsyncPersistentSubscription.init

    async def patched_init(self) -> None:
        await original_init(self)
        # Propagate subscription_id to _read_reqs (missing in esdbclient async version)
        if hasattr(self, '_subscription_id') and hasattr(self, '_read_reqs'):
            self._read_reqs.subscription_id = self._subscription_id.encode()
            log.debug(f"Patched: propagated subscription_id to _read_reqs: {self._subscription_id}")

    AsyncPersistentSubscription.init = patched_init
    log.info("Patched esdbclient AsyncPersistentSubscription.init() to propagate subscription_id")


# Call at application startup
patch_esdbclient_async_subscription_id()
```

---

## Integration with Neuroglia

If Neuroglia provides an `ESEventStore` or similar abstraction, the patch should be applied **before** the first persistent subscription is created. Suggested integration points:

### Option 1: Application-level patch (recommended for now)

Apply the patch in your application's `main.py` before configuring the Neuroglia framework:

```python
# main.py
from patches import patch_esdbclient_async_subscription_id

# Apply patch before any EventStoreDB operations
patch_esdbclient_async_subscription_id()

# Then configure Neuroglia...
app = build_app()
```

### Option 2: Framework-level fix (for Neuroglia maintainers)

Add the patch to Neuroglia's EventStore initialization, perhaps in `neuroglia/data/infrastructure/event_sourcing/event_store/`.

---

## Verification

After applying the patch, you should see in logs:

```
🔧 Patched esdbclient AsyncPersistentSubscription.init() to propagate subscription_id
🔧 Fixed esdbclient: propagated subscription_id to _read_reqs: $ce-your_db::your_consumer_group
```

And in EventStoreDB admin UI (`http://localhost:2113`):

- Navigate to **Persistent Subscriptions** → your subscription
- The `lastCheckpointedEventPosition` should now advance
- `totalInFlightMessages` should decrease after processing

---

## Upstream Bug Report

Bug report filed with the kurrentdbclient maintainers:

- **Repository**: https://github.com/pyeventsourcing/kurrentdbclient
- **Issue**: https://github.com/pyeventsourcing/kurrentdbclient/issues/35

### Suggested Fix for esdbclient

In `esdbclient/persistent.py`, add the missing line to `AsyncPersistentSubscription.init()`:

```python
async def init(self) -> None:
    # ... existing code ...

    # Add this line (matching the sync version):
    self._read_reqs.subscription_id = self._subscription_id.encode()
```

---

## Why This Wasn't Caught Earlier

1. **Silent failure**: EventStoreDB silently ignores ACKs with empty subscription IDs (no error returned)
2. **Sync version works**: Most examples/tests use the sync client
3. **Idempotent handlers mask the issue**: Redelivered events often succeed silently
4. **Timeout-based redelivery**: Looks like transient network issues

---

## Affected Versions

- **esdbclient**: 1.1.7 (and likely all earlier versions with async support)
- **kurrentdbclient**: Likely affected (same codebase, rebranded)
- **Python**: 3.9+ (async support)
- **EventStoreDB**: All versions (the bug is client-side)

---

## Questions?

Happy to provide more details or help integrate the patch into the Neuroglia framework.

---

## Files Reference

- **Patch implementation**: `src/patches.py` (function `patch_esdbclient_async_subscription_id`)
- **Detailed bug analysis**: `notes/ESDBCLIENT_ASYNC_SUBSCRIPTION_BUG.md`
- **GitHub issue template**: `notes/ESDBCLIENT_GITHUB_ISSUE.md`
