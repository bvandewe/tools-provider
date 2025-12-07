# Neuroglia Framework Bug Report: Race Condition in Domain Event Projection

**Component:** `neuroglia.mediation.Mediator` / Event Publishing
**Severity:** High
**Affects:** Read Model projections in CQRS/Event Sourcing scenarios
**Version:** (Current as of December 2025)

---

## Summary

When an aggregate emits multiple domain events during a single operation (e.g., `ToolGroupCreatedDomainEvent` followed by `SelectorAddedDomainEvent`), the Mediator dispatches these events to their respective `DomainEventHandler` implementations **concurrently**. This causes a race condition where handlers for subsequent events may execute before handlers for the initial event have completed their work.

This breaks the fundamental guarantee of event ordering within an aggregate stream.

---

## Reproduction Scenario

### Setup

- Aggregate: `ToolGroup` with state containing `selectors: List[ToolSelector]`
- Two projection handlers:
  1. `ToolGroupCreatedProjectionHandler` - Creates `ToolGroupDto` in MongoDB
  2. `SelectorAddedProjectionHandler` - Updates existing `ToolGroupDto` to add selector

### Command Execution

```python
# In CreateToolGroupCommandHandler.handle_async():

# 1. Create aggregate (emits ToolGroupCreatedDomainEvent)
tool_group = ToolGroup(name="Test", description="...")

# 2. Add selector (emits SelectorAddedDomainEvent)
tool_group.add_selector(selector, added_by=user_id)

# 3. Persist - both events are saved atomically to EventStoreDB
await self.tool_group_repository.add_async(tool_group)
```

### Expected Behavior

Events should be processed **sequentially in emission order**:

1. `ToolGroupCreatedProjectionHandler.handle_async()` runs → Creates ToolGroupDto in MongoDB
2. `SelectorAddedProjectionHandler.handle_async()` runs → Updates the existing ToolGroupDto

### Actual Behavior

Events are dispatched **concurrently**:

```
21:32:45,920 - Projecting ToolGroupCreatedDomainEvent: a2165ca2-...
21:32:45,980 - Projecting SelectorAddedDomainEvent: a2165ca2-...     # Started before Created finished!
21:32:45,986 - ✅ Projected ToolGroupCreated to Read Model           # MongoDB write completes
21:32:45,987 - ⚠️ ToolGroup not found in Read Model for selector add # FAILS - document doesn't exist yet!
```

The `SelectorAddedProjectionHandler` queries MongoDB for the ToolGroup before `ToolGroupCreatedProjectionHandler` has committed its insert.

---

## Root Cause Analysis

The issue appears to be in how the Mediator publishes domain events. When `EventSourcingRepository.add_async()` (or `update_async()`) persists an aggregate with multiple pending events, all events are published through the Mediator without awaiting completion of each handler before dispatching the next.

### Likely Code Path (Hypothesis)

```python
# Suspected pattern in EventSourcingRepository or related code:
for event in aggregate.pending_events:
    # This likely does NOT await each publish before moving to next
    await mediator.publish_async(event)  # Or possibly fire-and-forget
```

Or in the Mediator itself:

```python
# If publish_async dispatches to multiple handlers concurrently:
async def publish_async(self, event):
    handlers = self._get_handlers_for(event)
    # Concurrent dispatch - problematic for ordered events
    await asyncio.gather(*[h.handle_async(event) for h in handlers])
```

---

## Impact

This bug affects **any CQRS/Event Sourcing implementation** where:

1. An aggregate emits multiple events in a single operation
2. Projection handlers have dependencies on prior events being processed
3. The read model requires consistent state built from ordered events

### Affected Patterns

- Creating an entity with initial child collections (e.g., Group with Selectors)
- Bulk operations that emit multiple events per item
- Saga/Process Manager patterns that rely on event ordering
- Any projection handler that updates (rather than creates) a document

---

## Proposed Solution

### Option 1: Sequential Event Publishing (Recommended)

Events from a single aggregate operation should be published **sequentially**, awaiting each handler before dispatching the next:

```python
# In the event publishing logic:
for event in aggregate.pending_events:
    await mediator.publish_async(event)  # Await completion before next event
```

This maintains the causal ordering guarantee that event sourcing provides.

### Option 2: Aggregate-Scoped Event Batching

Provide an API to publish all events from an aggregate as an ordered batch:

```python
await mediator.publish_batch_async(
    aggregate_id=aggregate.id(),
    events=aggregate.pending_events,
    ordered=True  # Ensures sequential processing
)
```

### Option 3: Event Correlation with Ordering Hints

Add metadata to events indicating their position in the aggregate's event sequence:

```python
@dataclass
class DomainEvent:
    aggregate_id: str
    sequence_number: int  # Position in this batch
    batch_id: str         # Groups related events
```

The Mediator could then ensure events with the same `batch_id` are processed in `sequence_number` order.

---

## Workarounds (Current)

Until this is fixed in the framework, applications must implement defensive patterns:

### Workaround A: Retry with Backoff in Handlers

```python
async def handle_async(self, event: SelectorAddedDomainEvent) -> None:
    for attempt in range(3):
        group = await self._repository.get_async(event.aggregate_id)
        if group:
            break
        await asyncio.sleep(0.1 * (attempt + 1))  # Exponential backoff

    if not group:
        raise EventProcessingError(f"ToolGroup {event.aggregate_id} not found after retries")
```

### Workaround B: Upsert Pattern

```python
async def handle_async(self, event: SelectorAddedDomainEvent) -> None:
    # Use MongoDB upsert to handle missing document
    await self._collection.update_one(
        {"_id": event.aggregate_id},
        {"$push": {"selectors": event.selector}},
        upsert=True  # Creates doc if missing
    )
```

**Both workarounds are suboptimal** as they add complexity, potential data inconsistency, and don't address the fundamental ordering violation.

---

## Test Case

```python
@pytest.mark.asyncio
async def test_aggregate_events_processed_in_order():
    """Events from a single aggregate operation should be processed sequentially."""

    processing_order = []

    class TrackingCreatedHandler(DomainEventHandler[ToolGroupCreatedDomainEvent]):
        async def handle_async(self, event):
            await asyncio.sleep(0.1)  # Simulate DB write latency
            processing_order.append(("created", event.aggregate_id))

    class TrackingSelectorHandler(DomainEventHandler[SelectorAddedDomainEvent]):
        async def handle_async(self, event):
            processing_order.append(("selector", event.aggregate_id))

    # Create aggregate with selector
    tool_group = ToolGroup(name="Test", description="")
    tool_group.add_selector(ToolSelector(id="sel-1", name_pattern="*"))

    await repository.add_async(tool_group)

    # Wait for all handlers to complete
    await asyncio.sleep(0.2)

    # Assert ordering: created MUST complete before selector starts
    assert processing_order == [
        ("created", tool_group.id()),
        ("selector", tool_group.id()),
    ]
```

---

## Environment

- **Framework:** python-neuroglia
- **Event Store:** KurrentDB (EventStoreDB fork)
- **Read Model:** MongoDB (via Motor async driver)
- **Pattern:** CQRS with Event Sourcing, Read Model projections via DomainEventHandlers

---

## References

- [Event Sourcing - Martin Fowler](https://martinfowler.com/eaaDev/EventSourcing.html) - "Events are processed in order"
- [CQRS Journey - Microsoft](https://docs.microsoft.com/en-us/previous-versions/msp-n-p/jj554200(v=pandp.10)) - Event ordering guarantees
- Related issue: See `notes/NEUROGLIA_AGGREGATOR_PENDING_EVENTS_BUG.md` if exists

---

## Requested Action

1. Confirm this is unintended behavior (events from same aggregate processed concurrently)
2. Implement sequential event processing for events emitted from a single aggregate operation
3. Consider adding configuration option for parallel vs sequential handler dispatch

Thank you for reviewing this issue. Happy to provide additional logs, traces, or a minimal reproduction repository if helpful.
