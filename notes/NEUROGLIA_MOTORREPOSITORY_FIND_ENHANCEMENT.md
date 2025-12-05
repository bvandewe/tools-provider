# Neuroglia MotorRepository.find_async() Enhancement Request

## Summary

The `MotorRepository.find_async()` method only accepts a `filter_dict` parameter and does not support essential MongoDB query options like `sort`, `limit`, `skip`, and `projection`. This significantly limits the usefulness of the method for real-world queries.

## Current Signature

```python
async def find_async(self, filter_dict: dict) -> list[TEntity]:
```

## Current Implementation

```python
async def find_async(self, filter_dict: dict) -> list[TEntity]:
    entities = []
    async for doc in self.collection.find(filter_dict):
        entity = self._deserialize_entity(doc)
        entities.append(entity)
    return entities
```

## Problem

Common query patterns are not supported:

```python
# FAILS - sort not supported
await repo.find_async({"is_enabled": True}, sort=[("name", 1)])

# FAILS - limit not supported
await repo.find_async({"status": "active"}, limit=10)

# FAILS - skip not supported (for pagination)
await repo.find_async({"status": "active"}, skip=20, limit=10)

# FAILS - projection not supported
await repo.find_async({"status": "active"}, projection={"name": 1, "email": 1})
```

## Requested Enhancement

### Option 1: Add Optional Parameters (Recommended)

```python
from typing import Optional, List, Tuple

async def find_async(
    self,
    filter_dict: dict,
    sort: Optional[List[Tuple[str, int]]] = None,
    limit: Optional[int] = None,
    skip: Optional[int] = None,
    projection: Optional[dict] = None,
) -> list[TEntity]:
    """
    Find entities matching a MongoDB filter query.

    Args:
        filter_dict: MongoDB query filter (e.g., {"state.email": "user@example.com"})
        sort: List of (field, direction) tuples. Direction: 1 for ascending, -1 for descending.
              Example: [("name", 1), ("created_at", -1)]
        limit: Maximum number of documents to return
        skip: Number of documents to skip (for pagination)
        projection: Fields to include/exclude. Example: {"name": 1, "email": 1}

    Returns:
        List of entities matching the filter

    Example:
        ```python
        # Find active users sorted by name, paginated
        users = await repository.find_async(
            {"state.is_active": True},
            sort=[("state.name", 1)],
            skip=20,
            limit=10
        )
        ```
    """
    cursor = self.collection.find(filter_dict, projection)

    if sort:
        cursor = cursor.sort(sort)
    if skip:
        cursor = cursor.skip(skip)
    if limit:
        cursor = cursor.limit(limit)

    entities = []
    async for doc in cursor:
        entity = self._deserialize_entity(doc)
        entities.append(entity)

    return entities
```

### Option 2: Add Separate Methods

Add additional methods for common patterns:

```python
async def find_sorted_async(
    self,
    filter_dict: dict,
    sort: List[Tuple[str, int]]
) -> list[TEntity]:
    """Find with sorting."""
    ...

async def find_paginated_async(
    self,
    filter_dict: dict,
    skip: int,
    limit: int,
    sort: Optional[List[Tuple[str, int]]] = None
) -> list[TEntity]:
    """Find with pagination support."""
    ...

async def count_async(self, filter_dict: dict) -> int:
    """Count documents matching filter (useful for pagination)."""
    return await self.collection.count_documents(filter_dict)
```

### Option 3: Accept **kwargs

```python
async def find_async(self, filter_dict: dict, **kwargs) -> list[TEntity]:
    """
    Find entities with optional MongoDB cursor options.

    Supported kwargs: sort, limit, skip, projection
    """
    cursor = self.collection.find(filter_dict, kwargs.get('projection'))

    if 'sort' in kwargs:
        cursor = cursor.sort(kwargs['sort'])
    if 'skip' in kwargs:
        cursor = cursor.skip(kwargs['skip'])
    if 'limit' in kwargs:
        cursor = cursor.limit(kwargs['limit'])

    entities = []
    async for doc in cursor:
        entity = self._deserialize_entity(doc)
        entities.append(entity)

    return entities
```

## Additional Useful Methods

Consider also adding:

```python
async def count_async(self, filter_dict: dict = None) -> int:
    """Count documents matching filter."""
    filter_dict = filter_dict or {}
    return await self.collection.count_documents(filter_dict)

async def exists_async(self, filter_dict: dict) -> bool:
    """Check if any document matches the filter."""
    return await self.collection.count_documents(filter_dict, limit=1) > 0

async def find_one_async(self, filter_dict: dict) -> Optional[TEntity]:
    """Find a single document matching the filter."""
    doc = await self.collection.find_one(filter_dict)
    if doc:
        return self._deserialize_entity(doc)
    return None
```

## Current Workaround

Without this enhancement, users must access the collection directly:

```python
class MotorSourceDtoRepository(MotorRepository[SourceDto, str]):
    async def get_enabled_async(self) -> List[SourceDto]:
        # Workaround: Access collection directly
        cursor = self.collection.find({"is_enabled": True}).sort("name", 1)
        entities = []
        async for doc in cursor:
            entity = self._deserialize_entity(doc)
            entities.append(entity)
        return entities
```

This workaround:

- Exposes internal implementation details
- Requires knowledge of the `_deserialize_entity` method
- Is error-prone and verbose
- Bypasses any future enhancements to `find_async`

## Impact

**High** - Sorting and pagination are fundamental database operations required by virtually all applications. The current implementation forces users to either:

1. Use the broken queryable API (see NEUROGLIA_MOTORQUERY_CHAINING_BUG.md)
2. Access internal methods directly (fragile workaround)
3. Load all data and sort in Python (inefficient)

## Environment

- Python: 3.11, 3.12
- neuroglia-framework version: Latest (as of December 2025)
- Database: MongoDB with Motor driver

## Priority

**High** - This is a fundamental limitation that affects any non-trivial query.
