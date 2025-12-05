"""
Patches for third-party library bugs.

This module contains runtime patches for bugs in dependencies that haven't
been fixed upstream yet.

CURRENT PATCHES NEEDED:
- Bug #1: neuroglia-python 0.7.0 ESEventStore._ensure_client() awaits non-awaitable AsyncKurrentDBClient
  The kurrentdbclient.AsyncKurrentDBClient constructor returns a client directly (not awaitable),
  but neuroglia tries to await it. Additionally, AsyncKurrentDBClient.connect() must be called
  to establish the connection before the client can be used.

PREVIOUSLY FIXED (no longer need patches):
- esdbclient AsyncPersistentSubscription.init() missing subscription_id propagation
  FIXED IN: kurrentdbclient 1.0.7+ (subscription_id now properly propagated in async init())
  See: https://github.com/pyeventsourcing/kurrentdbclient/issues/35
- ack_id for resolved link events in ESEventStore (fixed in Neuroglia)
- clear_pending_events() called before event publishing (fixed in Neuroglia)

DESIGN NOTE - CloudEvent Publishing:
The Neuroglia EventSourcingRepository intentionally overrides _publish_domain_events() to do nothing.
This is by design:
1. Write Path: Persists events to EventStoreDB but does NOT publish via mediator
2. Read Path: ReadModelReconciliator subscribes to EventStoreDB and publishes ALL events via mediator
3. This ensures single, reliable event publishing from the source of truth (EventStoreDB)
Result: CloudEvents are emitted exactly once per domain event, with no duplicates.
"""

import logging
from typing import Any

log = logging.getLogger(__name__)


def patch_neuroglia_eseventstore_ensure_client() -> None:
    """
    Fix neuroglia-python 0.7.0 bug: ESEventStore._ensure_client() incorrectly awaits
    AsyncKurrentDBClient constructor which is not awaitable.

    The kurrentdbclient.AsyncKurrentDBClient(uri=...) returns a client instance directly,
    not a coroutine. But neuroglia's code does:
        self._eventstore_client = await AsyncClientFactory(uri=self._connection_string)

    Additionally, the AsyncKurrentDBClient requires calling connect() to establish the
    connection before it can be used.

    This patch replaces _ensure_client with a version that:
    1. Creates the client without await
    2. Calls await client.connect() to establish the connection
    """
    from kurrentdbclient import AsyncKurrentDBClient
    from neuroglia.data.infrastructure.event_sourcing.event_store.event_store import ESEventStore

    async def patched_ensure_client(self: Any) -> Any:
        """Lazily initialize the async KurrentDB client on first use"""
        if self._eventstore_client is None:
            if self._connection_string is None:
                raise RuntimeError("Neither connection string nor client provided")
            # AsyncKurrentDBClient constructor is NOT awaitable - it returns client directly
            client = AsyncKurrentDBClient(uri=self._connection_string)
            # Must call connect() to establish the connection
            await client.connect()
            self._eventstore_client = client
            log.debug(f"🔧 KurrentDB client connected to {self._connection_string}")
        return self._eventstore_client

    ESEventStore._ensure_client = patched_ensure_client  # type: ignore[method-assign]
    log.info("🔧 Patched neuroglia ESEventStore._ensure_client() for kurrentdbclient compatibility")


def apply_all_patches() -> None:
    """
    Apply all patches needed for the tools-provider service.

    Patches applied:
    1. patch_neuroglia_eseventstore_ensure_client() - Fixes neuroglia 0.7.0 await bug with kurrentdbclient
    """
    log.info("🔧 Applying framework patches...")

    # Fix neuroglia bug with kurrentdbclient
    patch_neuroglia_eseventstore_ensure_client()

    log.info("🔧 All patches applied successfully")
