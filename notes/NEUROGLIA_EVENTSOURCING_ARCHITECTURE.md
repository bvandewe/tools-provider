# Neuroglia Event Sourcing Architecture

**Date**: December 2, 2025
**Version**: 1.0
**Status**: Verified through diagnostic logging

---

## Executive Summary

This document describes the **event publishing architecture** in Neuroglia's Event Sourcing implementation. The key insight is that **domain events are published exactly once** through a carefully designed separation between the Write Path and Read Path.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           NEUROGLIA EVENT SOURCING                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   ┌──────────────┐     ┌────────────────────┐     ┌───────────────────────┐     │
│   │   Command    │────▶│  EventSourcing     │────▶│    EventStoreDB       │     │
│   │   Handler    │     │  Repository        │     │   (Source of Truth)   │     │
│   └──────────────┘     └────────────────────┘     └───────────┬───────────┘     │
│                                 │                              │                 │
│                                 │ ❌ Does NOT                  │                 │
│                                 │    publish events            │                 │
│                                 │    via mediator              ▼                 │
│                                 │                  ┌───────────────────────┐     │
│                                 │                  │ Persistent Subscription│     │
│                                 │                  │  ($ce-{database})     │     │
│                                 │                  └───────────┬───────────┘     │
│                                 │                              │                 │
│                                 │                              ▼                 │
│                                 │                  ┌───────────────────────┐     │
│                                 │                  │  ReadModelReconciliator│     │
│                                 │                  │  (HostedService)      │     │
│                                 │                  └───────────┬───────────┘     │
│                                 │                              │                 │
│                                 │                              │ ✅ Publishes    │
│                                 │                              │    ALL events   │
│                                 │                              │    via mediator │
│                                 │                              ▼                 │
│                                 │                  ┌───────────────────────┐     │
│                                 │                  │   Mediator Pipeline   │     │
│                                 │                  │  ┌─────────────────┐  │     │
│                                 │                  │  │ Pipeline        │  │     │
│                                 │                  │  │ Behaviors       │  │     │
│                                 │                  │  └────────┬────────┘  │     │
│                                 │                  │           │           │     │
│                                 │                  │  ┌────────▼────────┐  │     │
│                                 │                  │  │ Domain Event    │  │     │
│                                 │                  │  │ Handlers        │  │     │
│                                 │                  │  │ (Projections)   │  │     │
│                                 │                  │  └────────┬────────┘  │     │
│                                 │                  │           │           │     │
│                                 │                  │  ┌────────▼────────┐  │     │
│                                 │                  │  │ CloudEvent      │  │     │
│                                 │                  │  │ Behavior        │  │     │
│                                 │                  │  └─────────────────┘  │     │
│                                 │                  └───────────────────────┘     │
│                                 │                              │                 │
│                                 │                              ▼                 │
│                                 │                  ┌───────────────────────┐     │
│                                 │                  │  MongoDB Read Model   │     │
│                                 │                  │  CloudEvent Sink      │     │
│                                 │                  └───────────────────────┘     │
│                                 │                              │                 │
│                                 │                              ▼                 │
│                                 │                  ┌───────────────────────┐     │
│                                 │                  │   ACK to EventStoreDB │     │
│                                 │                  └───────────────────────┘     │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Key Design Decision: Event Publishing Location

### The Question

In a CQRS + Event Sourcing architecture, there are two potential places to publish domain events via the mediator:

1. **Write Path**: After `EventSourcingRepository` persists events to EventStoreDB
2. **Read Path**: When `ReadModelReconciliator` receives events from EventStoreDB subscription

### Neuroglia's Answer: Read Path Only

**Neuroglia publishes events ONLY from the Read Path.** This is implemented through an intentional override in `EventSourcingRepository`:

```python
# neuroglia/data/infrastructure/event_sourcing/event_sourcing_repository.py

class EventSourcingRepository(Generic[TAggregate, TKey], Repository[TAggregate, TKey]):

    async def _publish_domain_events(self, entity: TAggregate) -> None:
        """
        Override base class event publishing for event-sourced aggregates.

        Event sourcing repositories DO NOT publish events directly because:
        1. Events are already persisted to the EventStore
        2. ReadModelReconciliator subscribes to EventStore and publishes ALL events
        3. Publishing here would cause DOUBLE PUBLISHING

        For event-sourced aggregates:
        - Events are persisted to EventStore by _do_add_async/_do_update_async
        - ReadModelReconciliator.on_event_record_stream_next_async() publishes via mediator
        - This ensures single, reliable event publishing from the source of truth
        """
        # Do nothing - ReadModelReconciliator handles event publishing from EventStore
        pass
```

### Contrast with State-Based Repositories

For **state-based repositories** (like `MotorRepository` for MongoDB), the base class `Repository._publish_domain_events()` IS called because:

- Events are not stored separately from state
- There's no subscription mechanism to deliver events later
- Events must be published immediately after state is persisted

---

## Why This Design?

### 1. Single Source of Truth

EventStoreDB is the authoritative source for all domain events. By publishing only from the EventStoreDB subscription:

- Events are guaranteed to be persisted before publishing
- No risk of publishing events that failed to persist
- Order of events is preserved as stored

### 2. Reliable Delivery

The persistent subscription provides:

- **At-least-once delivery**: Events are redelivered until ACKed
- **Checkpoint tracking**: Resume from last processed event on restart
- **Consumer groups**: Multiple instances can share the workload

### 3. No Duplicate CloudEvents

Since events are published from exactly one location (ReadModelReconciliator), there's no risk of:

- Double publishing (once from Write Path, once from Read Path)
- Race conditions between Write and Read paths
- Inconsistent behavior based on timing

### 4. Eventual Consistency Model

This design embraces eventual consistency:

- Commands complete quickly (just persist to EventStoreDB)
- Read model updates happen asynchronously
- CloudEvents are emitted after successful read model projection

---

## Data Flow: Step by Step

### 1. Command Execution

```
Client → Controller → Mediator.execute_async(CreateTaskCommand)
                           │
                           ▼
                  CreateTaskCommandHandler
                           │
                           ▼
                  Task.create(...) → TaskCreatedDomainEvent added to _pending_events
                           │
                           ▼
                  EventSourcingRepository.add_async(task)
                           │
                           ├──▶ _do_add_async() → Persist to EventStoreDB ✅
                           │
                           └──▶ _publish_domain_events() → EMPTY (no-op) ✅
                           │
                           ▼
                  Return TaskDto to client
```

### 2. Event Processing (Asynchronous)

```
EventStoreDB Persistent Subscription
         │
         ▼
ReadModelReconciliator.on_event_record_stream_next_async(event)
         │
         ▼
Mediator.publish_async(TaskCreatedDomainEvent)
         │
         ├──▶ Pipeline Behaviors (Metrics, Tracing, etc.)
         │
         ├──▶ TaskCreatedProjectionHandler → Update MongoDB Read Model
         │
         └──▶ DomainEventCloudEventBehavior → Emit CloudEvent
         │
         ▼
ACK event to EventStoreDB
```

---

## Implications

### For Application Developers

1. **Domain event handlers are called from the Read Path**, not the Write Path
2. **Read model updates are eventually consistent** with the Write Model
3. **CloudEvents are emitted AFTER read model projection** completes

### For Handler Implementation

Projection handlers should be:

- **Idempotent**: Same event processed twice should have same result
- **Side-effect aware**: CloudEvents are emitted after handler completes
- **Fast**: Don't block the event processing pipeline

### For Testing

- Unit tests can mock the mediator to verify event content
- Integration tests should verify end-to-end flow including projections
- CloudEvent tests should subscribe to the CloudEvent sink

---

## Related Bugs (Fixed)

### esdbclient Bug #1: Missing subscription_id (Issue #35)

**Status**: Patched in `src/patches.py`
**Issue**: https://github.com/pyeventsourcing/kurrentdbclient/issues/35

The async `AsyncPersistentSubscription.init()` doesn't propagate `subscription_id` to `_read_reqs`, causing ACKs to be sent with empty subscription ID.

**Patch**:

```python
def patch_esdbclient_async_subscription_id():
    from esdbclient.persistent import AsyncPersistentSubscription
    original_init = AsyncPersistentSubscription.init

    async def patched_init(self) -> None:
        await original_init(self)
        if hasattr(self, '_subscription_id') and hasattr(self, '_read_reqs'):
            self._read_reqs.subscription_id = self._subscription_id.encode()

    AsyncPersistentSubscription.init = patched_init
```

### Neuroglia Bug #2: Wrong ACK ID for Resolved Links (Fixed in Neuroglia)

**Status**: Fixed in Neuroglia framework

When using `resolveLinktos=true`, ACKs must use `e.ack_id` (link event ID), not `e.id` (resolved event ID).

**Fix in ESEventStore**:

```python
# Use ack_id for resolved link events, fall back to id
ack_id = getattr(e, 'ack_id', e.id)
```

---

## Verification

This architecture was verified through diagnostic logging on December 2, 2025:

```log
10:36:29,143  ✅ Command 'CreateTaskCommand' completed
10:36:29,147  📥 READ PATH: Received TaskCreatedDomainEvent from subscription
10:36:29,148  📥 READ PATH: Publishing TaskCreatedDomainEvent via mediator
10:36:29,153  Found 3 pipeline behaviors for TaskCreatedDomainEvent
10:36:29,154  📥 Projecting TaskCreated
10:36:29,235  ✅ Projected TaskCreated to Read Model
10:36:29,240  Emitting CloudEvent 'io.tools-provider.task.created.v1'
10:36:29,242  ACK sent for event
10:36:29,264  Published cloudevent
```

Key observations:

1. No "📤 WRITE PATH" log for Task aggregate (correctly suppressed)
2. Only "📥 READ PATH" publishes the domain event
3. CloudEvent emitted exactly once
4. ACK sent after successful processing

---

## References

- [Neuroglia Documentation](https://bvandewe.github.io/pyneuro/)
- [Event Sourcing Pattern](https://bvandewe.github.io/pyneuro/patterns/event-sourcing/)
- [CQRS Pattern](https://bvandewe.github.io/pyneuro/patterns/cqrs/)
- [esdbclient Issue #35](https://github.com/pyeventsourcing/kurrentdbclient/issues/35)
