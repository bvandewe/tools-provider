# Knowledge Manager - Namespace Versioning

## Revision Model

Each namespace maintains a revision history enabling rollback and audit.

```python
@dataclass
class KnowledgeRevision:
    revision_number: int       # Sequential: 1, 2, 3...
    message: str              # "Added networking terms"
    created_by: str           # user_id
    created_at: datetime

    # Snapshot of state at revision
    terms: dict[str, dict]
    relationships: dict[str, dict]
    rules: dict[str, dict]
```

## Revision Workflow

```
┌─────────────────┐
│ Current State   │  (editable)
└────────┬────────┘
         │ create_revision()
         ▼
┌─────────────────┐
│ Revision N      │  (immutable snapshot)
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ Revision N-1    │
└─────────────────┘
         │
         ⋮
```

## API

### Create Revision

```
POST /namespaces/{id}/revisions
Body: { message: "Added 5 new terms" }
Response: { revision_number: 3, created_at: "..." }
```

### List Revisions

```
GET /namespaces/{id}/revisions
Response: [
  { revision_number: 3, message: "...", created_at: "...", term_count: 25 },
  { revision_number: 2, message: "...", created_at: "...", term_count: 20 },
  ...
]
```

### Rollback

```
POST /namespaces/{id}/revisions/{revision_number}/rollback
Response: { current_revision: 2, rolled_back_from: 3 }
```

### Compare Revisions

```
GET /namespaces/{id}/revisions/compare?from=1&to=3
Response: {
  added_terms: [...],
  removed_terms: [...],
  modified_terms: [...]
}
```

## Event Sourcing Integration

Revisions are derived from the event stream:

```python
async def create_revision(self, namespace_id: str, message: str) -> int:
    # 1. Load current aggregate state
    namespace = await self._repo.get_async(namespace_id)

    # 2. Snapshot current state
    snapshot = {
        "terms": namespace.state.terms,
        "relationships": namespace.state.relationships,
        "rules": namespace.state.rules,
    }

    # 3. Emit revision event
    namespace.create_revision(message, user_id)
    await self._repo.update_async(namespace)

    return namespace.state.current_revision
```

## Storage Efficiency

Only store diffs between revisions (optional optimization):

```python
# Full snapshot for every 10th revision
# Delta snapshots in between
if revision_number % 10 == 0:
    store_full_snapshot(snapshot)
else:
    store_delta(previous_snapshot, snapshot)
```

---

_Next: [08-multi-tenancy.md](08-multi-tenancy.md) - Multi-Tenancy_
