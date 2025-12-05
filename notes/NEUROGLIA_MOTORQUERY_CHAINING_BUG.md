# Neuroglia MotorQuery Chaining Bug

## Summary

When chaining queryable operations (e.g., `.where()` followed by `.order_by()`) on a `MotorQuery`, the intermediate query object loses its generic type information, causing an `AttributeError`.

## Error

```
AttributeError: 'MotorQuery' object has no attribute '__orig_class__'
```

## Full Stack Trace

```python
File "/usr/local/lib/python3.11/site-packages/neuroglia/data/queryable.py", line 160, in order_by
    return self.provider.create_query(self.get_element_type(), expression)
                                      ^^^^^^^^^^^^^^^^^^^^^^^
File "/usr/local/lib/python3.11/site-packages/neuroglia/data/queryable.py", line 94, in get_element_type
    return self.__orig_class__.__args__[0]
           ^^^^^^^^^^^^^^^^^^^
AttributeError: 'MotorQuery' object has no attribute '__orig_class__'
```

## Reproduction

```python
from neuroglia.data.infrastructure.mongo import MotorRepository

class MotorSourceDtoRepository(MotorRepository[SourceDto, str]):
    async def get_enabled_async(self) -> List[SourceDto]:
        queryable = await self.query_async()
        # This FAILS - chaining .where() with .order_by()
        return await queryable.where(lambda source: source.is_enabled == True).order_by(lambda source: source.name).to_list_async()
```

### Works (single operation)

```python
queryable = await self.query_async()
return await queryable.where(lambda source: source.is_enabled == True).to_list_async()
```

### Fails (chained operations)

```python
queryable = await self.query_async()
return await queryable.where(lambda source: source.is_enabled == True).order_by(lambda source: source.name).to_list_async()
```

## Root Cause Analysis

The issue is in `neuroglia/data/queryable.py`:

1. When `query_async()` is called on `MotorRepository`, it returns a `MotorQueryable[T]` with proper `__orig_class__` set
2. When `.where()` is called, it internally calls `self.provider.create_query()` which creates a new `MotorQuery` object
3. The new `MotorQuery` object does NOT have `__orig_class__` set (this is a runtime attribute set by Python's `__class_getitem__`)
4. When `.order_by()` is called on this intermediate `MotorQuery`, it tries to call `get_element_type()` which accesses `__orig_class__`
5. Since `__orig_class__` was never set on the intermediate query, `AttributeError` is raised

### Relevant Code in `queryable.py`

```python
# Line 94
def get_element_type(self) -> type:
    return self.__orig_class__.__args__[0]  # <-- Fails here

# Line 160 (in order_by)
def order_by(self, key_selector: Callable[[TElement], Any]) -> "Queryable[TElement]":
    expression = self._build_expression(QueryOperator.ORDER_BY, ...)
    return self.provider.create_query(self.get_element_type(), expression)  # <-- Calls get_element_type()
```

## Suggested Fix

The `MotorQueryProvider.create_query()` method (or the base `QueryProvider.create_query()`) should propagate the element type to the newly created query object.

### Option 1: Store element_type explicitly

In `MotorQuery` (and base `Query`), store the element type as an instance attribute:

```python
class MotorQuery(Queryable[TElement]):
    def __init__(self, provider: "MotorQueryProvider", element_type: type, expression: Expression | None = None):
        super().__init__(provider, expression)
        self._element_type = element_type  # Store explicitly

    def get_element_type(self) -> type:
        # Try explicit attribute first, fall back to __orig_class__
        if hasattr(self, '_element_type') and self._element_type is not None:
            return self._element_type
        return self.__orig_class__.__args__[0]
```

### Option 2: Pass element_type through create_query

Modify `QueryProvider.create_query()` to accept and propagate element type:

```python
class MotorQueryProvider(QueryProvider):
    def create_query(self, element_type: type, expression: Expression | None = None) -> Queryable:
        query = MotorQuery(self, expression)
        query._element_type = element_type  # Propagate the type
        return query
```

### Option 3: Use typing.get_args at creation time

In the initial `query_async()` method, extract and store the type:

```python
async def query_async(self) -> Queryable[TElement]:
    element_type = get_args(self.__class__.__orig_bases__[0])[0]  # Extract from class definition
    query = self.query_provider.create_query(element_type, None)
    return query
```

## Current Workaround

Use MongoDB filter dictionaries directly instead of queryable lambda syntax:

```python
async def get_enabled_async(self) -> List[SourceDto]:
    # Instead of queryable chaining:
    # queryable = await self.query_async()
    # return await queryable.where(...).order_by(...).to_list_async()

    # Use MongoDB filters directly:
    return await self.find_async({"is_enabled": True}, sort=[("name", 1)])
```

## Impact

This bug affects any repository method that needs to chain multiple queryable operations (filtering + sorting, multiple filters, etc.). It significantly limits the usefulness of the type-safe queryable API.

## Environment

- Python: 3.11, 3.12
- neuroglia-framework version: Latest (as of December 2025)
- Database: MongoDB with Motor driver

## Related Issues

This is related to but distinct from the previously reported lambda parsing bug with multi-line method chains. That bug was in `_get_lambda_source_code()`. This bug is in the query object's type propagation.

## Files Affected in tools-provider

- `src/integration/repositories/motor_source_dto_repository.py`
- `src/integration/repositories/motor_tool_dto_repository.py`
- Any future repository with chained queryable operations

## Priority

**High** - This fundamentally breaks the fluent queryable API for any non-trivial queries.
