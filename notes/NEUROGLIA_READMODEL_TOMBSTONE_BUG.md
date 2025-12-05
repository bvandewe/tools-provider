# Neuroglia ReadModelReconciliator Tombstone Bug

## Issue

When using `DeleteMode.HARD` with `EventSourcingRepository`, the `ReadModelReconciliator` crashes on startup because it cannot parse tombstone events left by hard-deleted streams.

## Error Message

```
ERROR root:211 An exception occurred while decoding event with offset '0' from stream '$$tools_provider-task-8ea86302-e5f9-485c-9df3-0a4c55a3d155': Expecting value: line 1 column 1 (char 0)

ERROR root:228 An exception occurred while consuming events from stream '$ce-tools_provider', consequently to which the related subscription will be stopped: Expecting value: line 1 column 1 (char 0)
```

## Root Cause

When EventStoreDB hard-deletes a stream, it:

1. Deletes all events from the stream
2. Creates a **tombstone marker** with a `$$` prefix (e.g., `$$tools_provider-task-{id}`)
3. The tombstone appears in category projections like `$ce-tools_provider`

The `ReadModelReconciliator` subscribes to the category stream and tries to parse all events, including tombstones. Tombstone events have empty or invalid JSON data, causing a `JSONDecodeError`.

## Impact

- The `ReadModelReconciliator` subscription is **stopped** when it encounters a tombstone
- No further read model synchronization occurs
- The application continues running but read/write models become out of sync

## Workaround (Development)

Reset EventStoreDB to clear tombstones:

```bash
docker compose down eventstore
docker volume rm tools-provider_eventstore_data
docker compose up -d eventstore
docker compose restart app
```

## Suggested Fix for Neuroglia

The `ReadModelReconciliator` should handle tombstone events gracefully:

```python
# In ReadModelReconciliator.subscribe_async() or event processing logic

def process_event(self, event):
    # Skip tombstone streams (prefixed with $$)
    if event.stream_id.startswith("$$"):
        logger.debug(f"Skipping tombstone event from stream: {event.stream_id}")
        return

    # Skip system event types
    if event.event_type.startswith("$"):
        logger.debug(f"Skipping system event type: {event.event_type}")
        return

    try:
        decoded_data = json.loads(event.data)
        # ... process event
    except json.JSONDecodeError as e:
        logger.warning(f"Could not decode event from stream '{event.stream_id}': {e}")
        # Continue processing other events instead of stopping subscription
        return
```

## Alternative: Use SOFT Delete

If you need to preserve event history and avoid tombstones, use `DeleteMode.SOFT` instead:

```python
options = EventSourcingRepositoryOptions[Task, str](delete_mode=DeleteMode.SOFT)
```

With soft delete:

- Events are preserved
- A "deleted" marker event is appended
- No tombstones are created
- ReadModelReconciliator continues to work

## Related Files

- `src/main.py` - Repository configuration with `DeleteMode.HARD`
- `src/application/commands/delete_task_command.py` - Delete command handler
- `src/application/events/domain/task_projection_handlers.py` - Projection handlers

## Date Discovered

December 1, 2025

## Status

**Open** - Should be reported to Neuroglia maintainers
