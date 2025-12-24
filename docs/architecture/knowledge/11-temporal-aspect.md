# Temporal Aspect: "The Archive"

## Purpose

The Temporal Aspect provides **immutable, append-only event streams** for audit-critical entities. Each aggregate's complete history is persisted as a consistent sequence of `DomainEvent` instances, enabling:

- Full audit trail for compliance
- Time-travel queries ("What was the state at time T?")
- Debugging historical progression
- Undo/rollback capabilities

## Core Principle: Events as Facts

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        EVENT SOURCING PRINCIPLE                              │
│                                                                              │
│   "The current state is a LEFT FOLD over the event stream"                  │
│                                                                              │
│   State(now) = reduce(apply, initialState, [Event₁, Event₂, ..., Eventₙ])   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

Each event represents a **business fact that occurred**—not a state mutation, but a record of what happened. Events are:

- **Immutable**: Once appended, never modified or deleted
- **Ordered**: Strict sequence within an aggregate stream
- **Complete**: The stream is sufficient to reconstruct any historical state

## Event Stream Model

### Aggregate Stream

Each aggregate has its own stream in EventStoreDB:

```
Stream: "ExamBlueprint-{aggregate_id}"
┌──────────────────────────────────────────────────────────────────────────┐
│ Position │ Event Type                    │ Timestamp           │ Data    │
├──────────┼───────────────────────────────┼─────────────────────┼─────────┤
│    0     │ ExamBlueprintCreated          │ 2025-10-01T09:00:00 │ {...}   │
│    1     │ SectionAdded                  │ 2025-10-01T09:15:00 │ {...}   │
│    2     │ QuestionPoolAssigned          │ 2025-10-02T14:30:00 │ {...}   │
│    3     │ PassingScoreUpdated           │ 2025-10-05T11:00:00 │ {...}   │
│    4     │ BlueprintPublished            │ 2025-10-10T16:00:00 │ {...}   │
│    5     │ QuestionRetired               │ 2025-11-15T10:30:00 │ {...}   │
└──────────┴───────────────────────────────┴─────────────────────┴─────────┘
```

### Event Structure

```python
@cloudevent("exam.blueprint.created.v1")
class ExamBlueprintCreatedDomainEvent(DomainEvent):
    """Recorded when an exam blueprint is created."""
    aggregate_id: str
    owner_id: str
    title: str
    certification_id: str
    created_at: datetime

@cloudevent("exam.blueprint.section.added.v1")
class SectionAddedDomainEvent(DomainEvent):
    """Recorded when a section is added to a blueprint."""
    aggregate_id: str
    section_id: str
    title: str
    weight_percent: float
    question_count: int

@cloudevent("exam.blueprint.published.v1")
class BlueprintPublishedDomainEvent(DomainEvent):
    """Recorded when a blueprint becomes active."""
    aggregate_id: str
    version: str
    effective_date: datetime
    published_by: str
```

## Time-Travel Queries

### Reconstruct State at Point in Time

```python
async def get_blueprint_at_time(
    repository: EventSourcingRepository[ExamBlueprint, str],
    blueprint_id: str,
    as_of: datetime
) -> ExamBlueprint:
    """
    Reconstruct the blueprint state as it was at a specific timestamp.

    Replays events from the stream up to (but not after) the given time.
    """
    # Read events up to the specified timestamp
    events = await repository.read_events_async(
        stream_id=f"ExamBlueprint-{blueprint_id}",
        max_timestamp=as_of
    )

    # Rebuild state by replaying events
    blueprint = ExamBlueprint.create_empty(blueprint_id)
    for event in events:
        blueprint.apply(event)

    return blueprint
```

### Query Historical Progression

```python
async def get_blueprint_timeline(
    repository: EventSourcingRepository[ExamBlueprint, str],
    blueprint_id: str
) -> list[TimelineEntry]:
    """
    Get the complete history of changes to a blueprint.

    Returns a timeline suitable for audit logs or debugging.
    """
    events = await repository.read_all_events_async(
        stream_id=f"ExamBlueprint-{blueprint_id}"
    )

    return [
        TimelineEntry(
            timestamp=event.timestamp,
            event_type=event.__class__.__name__,
            actor=event.metadata.get("user_id"),
            summary=event.get_summary()
        )
        for event in events
    ]
```

### Compare States Across Time

```python
async def diff_blueprint_versions(
    blueprint_id: str,
    from_time: datetime,
    to_time: datetime
) -> BlueprintDiff:
    """
    Compare blueprint state between two points in time.

    Useful for auditing what changed during a specific period.
    """
    state_before = await get_blueprint_at_time(blueprint_id, from_time)
    state_after = await get_blueprint_at_time(blueprint_id, to_time)

    return BlueprintDiff(
        sections_added=[s for s in state_after.sections if s not in state_before.sections],
        sections_removed=[s for s in state_before.sections if s not in state_after.sections],
        questions_changed=compute_question_diff(state_before, state_after),
        passing_score_changed=(state_before.passing_score != state_after.passing_score)
    )
```

## AI Benefit: Historical Context

The AI can answer temporal questions that would be impossible with state-only persistence:

### Example: Certification Audit

**User Query**: "Show me the exam blueprint that was active when John earned his certification."

**AI Action**:

```python
# Get John's certification event
certification = await get_certification(john_id, cert_id)
exam_date = certification.earned_at

# Reconstruct the blueprint as it was on exam day
blueprint = await get_blueprint_at_time(certification.blueprint_id, exam_date)

# Now AI has the exact questions and passing criteria John faced
```

**AI Response**:
> "John took version 2.3 of the Python Senior exam on October 15th. At that time, the passing score was 75% and the exam had 60 questions across 4 sections. Here's the breakdown..."

### Example: Debugging User Struggles

**User Query**: "Why is Sarah struggling with Module 5?"

**AI Action**:

```python
# Get Sarah's learning history for Module 5
events = await get_user_events(
    user_id=sarah_id,
    event_types=["AttemptStarted", "AttemptFailed", "HintRequested"],
    concept_filter="module-5"
)

# Analyze the progression
timeline = [
    {"time": e.timestamp, "action": e.event_type, "details": e.data}
    for e in events
]
```

**AI Response**:
> "Looking at Sarah's history with Module 5:
>
> - October 1: First attempt, scored 45%, struggled with recursion questions
> - October 3: Second attempt, scored 52%, same pattern
> - October 5: Requested hint on 'base case' concept
> - October 8: Third attempt, scored 48%—no improvement on recursion
>
> Recommendation: Sarah may need remediation on prerequisite concepts (loops, stack frames) before tackling recursion."

## When to Use Event-Sourcing

The Temporal Aspect applies to **audit-critical aggregates only**:

| Entity | Event-Sourced? | Rationale |
|--------|----------------|-----------|
| `ExamBlueprint` | ✅ Yes | Legal audit trail, version history |
| `Certification` | ✅ Yes | Immutable credential record |
| `LearningPath` | ✅ Yes | Progression history for analytics |
| `SemanticProfile` | ❌ No | Frequent updates, no audit need |
| `LearningIntent` | ❌ No | Drift detection in state, CloudEvents for observability |
| `TelemetryWindow` | ❌ No | Ephemeral time-series |

## Integration with Other Aspects

The Temporal Aspect provides the **foundation** for historical queries in other aspects:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         ASPECT INTEGRATION                               │
│                                                                          │
│   TEMPORAL                SEMANTIC              INTENTIONAL              │
│   (EventStoreDB)          (Neo4j)               (MongoDB)                │
│        │                      │                      │                   │
│        │   "What was the     │   "How did the      │                    │
│        │    graph state      │    goal drift       │                    │
│        │    on Oct 1?"       │    over time?"      │                    │
│        │         │           │         │           │                    │
│        ▼         ▼           ▼         ▼           ▼                    │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │                    CONTEXT VECTOR                                │   │
│   │  [current_state, historical_context, progression_analysis]      │   │
│   └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

## API Endpoints

### Get Aggregate History

```
GET /temporal/{aggregate_type}/{id}/history
Query: ?from={timestamp}&to={timestamp}
Response: {
  events: [
    { position: 0, type: "Created", timestamp: "...", data: {...} },
    { position: 1, type: "Updated", timestamp: "...", data: {...} }
  ],
  current_position: 5
}
```

### Reconstruct State at Time

```
GET /temporal/{aggregate_type}/{id}/snapshot?as_of={timestamp}
Response: {
  state: { ... },
  reconstructed_from_position: 3,
  as_of: "2025-10-15T12:00:00Z"
}
```

### Diff Between Times

```
GET /temporal/{aggregate_type}/{id}/diff?from={t1}&to={t2}
Response: {
  changes: [
    { field: "passing_score", from: 70, to: 75 },
    { field: "sections", added: [...], removed: [...] }
  ]
}
```

---

_Next: [12-semantic-aspect.md](12-semantic-aspect.md) - Knowledge & Social Graph_
