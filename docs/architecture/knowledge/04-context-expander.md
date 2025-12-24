# Knowledge Manager - Context Expander

## Purpose

The Context Expander is an interceptor that augments user queries with relevant domain knowledge before the agent processes them.

## Expansion Pipeline

```
User Query
    │
    ▼
┌───────────────────┐
│ 1. Term Detection │  Match terms + aliases in query
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ 2. Semantic Match │  Vector search for similar terms
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ 3. Graph Traverse │  Get related terms (depth=1)
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ 4. Rule Matching  │  Find applicable business rules
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ 5. Block Assembly │  Format as injection text
└─────────┬─────────┘
          │
          ▼
    Context Block
```

## Context Block Format

```markdown
---
## Domain Context

### Matched Terms
- **ExamBlueprint**: A structured definition of exam requirements including domains, skills, and item distribution.
- **ExamDomain**: A major content area within an exam blueprint.

### Related Concepts
- **Skill** (referenced by ExamDomain): A specific competency measured by items.

### Business Rules
- **Blueprint Completeness Rule**: Every ExamBlueprint must have at least one ExamDomain.
---
```

## Expansion Modes

| Mode | Behavior |
|------|----------|
| `auto` | Expand only if terms detected in query |
| `always` | Always perform semantic search |
| `keywords_only` | Only exact term/alias matches |
| `disabled` | Skip expansion entirely |

## Token Budget Management

```python
MAX_CONTEXT_TOKENS = 500  # Limit injection size

def trim_context_block(block: str, max_tokens: int) -> str:
    """Prioritize: matched terms > rules > related terms."""
    ...
```

## Performance

- Term detection: O(n) where n = query length
- Vector search: ~50ms (indexed)
- Graph traverse: ~20ms (cached)
- Target total latency: <100ms

---

_Next: [05-graph-analytics.md](05-graph-analytics.md) - Graph Analytics & Community Detection_
