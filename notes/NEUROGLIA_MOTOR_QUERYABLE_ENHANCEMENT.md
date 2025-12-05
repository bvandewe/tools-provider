# Neuroglia Framework Enhancement: Queryable MotorRepository and Custom Repository Registration

## Summary

Two related enhancement requests for `DataAccessLayer.ReadModel`:

1. **Make `MotorRepository` queryable** - Add `QueryableRepository` support to `MotorRepository` (async Motor driver) to match `MongoRepository` (sync PyMongo driver) capabilities
2. **Custom repository registration** - Allow `DataAccessLayer.ReadModel` to register custom domain repository implementations for DTOs

---

## Current Behavior

### Issue 1: MotorRepository Lacks Queryable Support

The `MongoRepository` (synchronous) extends `QueryableRepository` and provides LINQ-style querying:

```python
# mongo_repository.py
class MongoRepository(Generic[TEntity, TKey], QueryableRepository[TEntity, TKey]):
    async def query_async(self) -> Queryable[TEntity]:
        # Returns MongoQuery with fluent API
```

However, `MotorRepository` (async) only extends `Repository`:

```python
# motor_repository.py
class MotorRepository(Generic[TEntity, TKey], Repository[TEntity, TKey]):
    # No query_async() method
    # No Queryable support
```

This creates an asymmetry where:

- **Synchronous apps** can use `MongoRepository` with full queryable support
- **Async apps (FastAPI)** using `MotorRepository` cannot use queryable features

### Issue 2: DataAccessLayer.ReadModel Registration Differences

When `repository_type='mongo'`, the `ReadModel` registers:

- `Repository[T, K]`
- `QueryableRepository[T, K]` (via factory)
- `GetByIdQueryHandler[T, K]`
- `ListQueryHandler[T, K]`

When `repository_type='motor'`, it only calls `MotorRepository.configure()` which registers:

- `Repository[T, K]`
- `MotorRepository[T, K]`

**Missing for motor:**

- No `QueryableRepository[T, K]` registration
- No `GetByIdQueryHandler` / `ListQueryHandler` registration
- No way to register custom domain repository interfaces

### Current Workaround

To use custom repository implementations with domain-specific query methods, users must manually register them:

```python
# Current: Two-step registration required for async apps
DataAccessLayer.ReadModel(
    database_name="myapp",
    repository_type="motor"
).configure(builder, ["integration.models"])

# Manual registration for custom repository interface
builder.services.add_scoped(TaskDtoRepository, MotorTaskDtoRepository)
```

This is error-prone and inconsistent with the framework's philosophy of convention over configuration.

---

## Proposed Enhancement

### Part 1: Make MotorRepository Queryable

Add `QueryableRepository` support to `MotorRepository` with async-compatible query implementation.

#### 1.1 Create MotorQuery and MotorQueryProvider

```python
# neuroglia/data/infrastructure/mongo/motor_query.py
from typing import Generic, Optional
from ast import expr
from neuroglia.data.queryable import Queryable, QueryProvider, T


class MotorQuery(Generic[T], Queryable[T]):
    """Represents an async Motor MongoDB query."""

    def __init__(self, query_provider: "MotorQueryProvider", expression: Optional[expr] = None):
        super().__init__(query_provider, expression)


class MotorQueryProvider(QueryProvider):
    """Represents the async Motor implementation of the QueryProvider."""

    def __init__(self, collection: AsyncIOMotorCollection, entity_type: type):
        self._collection = collection
        self._entity_type = entity_type

    def create_query(self, element_type: type, expression: expr) -> Queryable:
        return MotorQuery[element_type](self, expression)

    async def execute_async(self, expression: expr, query_type: type) -> Any:
        """Execute query asynchronously using Motor."""
        query = MotorQueryBuilder(self._collection, JavaScriptExpressionTranslator()).build(expression)

        type_ = query_type if isclass(query_type) or query_type == List else type(query_type)
        if issubclass(type_, List):
            return [doc async for doc in query]
        else:
            return await query.to_list(length=1)[0] if await query.to_list(length=1) else None
```

#### 1.2 Update MotorRepository to Extend QueryableRepository

```python
# motor_repository.py - Updated
class MotorRepository(Generic[TEntity, TKey], QueryableRepository[TEntity, TKey]):
    """Async MongoDB repository with queryable support."""

    async def query_async(self) -> Queryable[TEntity]:
        """Returns a queryable for fluent LINQ-style queries."""
        return MotorQuery[TEntity](
            MotorQueryProvider(self.collection, self._entity_type)
        )

    # Existing methods unchanged...
```

### Part 2: Custom Repository Registration in DataAccessLayer.ReadModel

Add optional `repository_mappings` parameter to register custom domain repository interfaces.

#### 2.1 Enhanced ReadModel Configuration

```python
class DataAccessLayer:
    class ReadModel:
        def __init__(
            self,
            database_name: Optional[str] = None,
            repository_type: str = "mongo",
            repository_mappings: Optional[dict[type, type]] = None,  # NEW
        ):
            """Initialize ReadModel configuration.

            Args:
                database_name: MongoDB database name
                repository_type: 'mongo' (sync) or 'motor' (async)
                repository_mappings: Optional mapping of abstract repository interfaces
                                    to their concrete implementations.
                                    Example: {TaskDtoRepository: MotorTaskDtoRepository}
            """
            self._database_name = database_name
            self._repository_type = repository_type
            self._repository_mappings = repository_mappings or {}
```

#### 2.2 Updated configure() Method

```python
def _configure_with_database_name(self, builder, modules):
    # ... existing motor configuration ...

    elif self._repository_type == "motor":
        from neuroglia.data.infrastructure.mongo.motor_repository import MotorRepository

        for module in [ModuleLoader.load(module_name) for module_name in modules]:
            # Filter by @queryable decorator (consistent with mongo)
            for entity_type in TypeFinder.get_types(
                module,
                lambda cls: inspect.isclass(cls) and hasattr(cls, "__queryable__")
            ):
                key_type = str

                MotorRepository.configure(
                    builder=builder,
                    entity_type=entity_type,
                    key_type=key_type,
                    database_name=self._database_name,
                )

                # NEW: Register QueryableRepository alias
                def make_queryable_factory(et, kt):
                    def queryable_factory(provider: ServiceProvider):
                        return provider.get_required_service(Repository[et, kt])
                    return queryable_factory

                builder.services.try_add_scoped(
                    QueryableRepository[entity_type, key_type],
                    implementation_factory=make_queryable_factory(entity_type, key_type),
                )

                # NEW: Register query handlers (consistent with mongo)
                builder.services.add_transient(
                    RequestHandler,
                    GetByIdQueryHandler[entity_type, key_type]
                )
                builder.services.add_transient(
                    RequestHandler,
                    ListQueryHandler[entity_type, key_type]
                )

        # NEW: Register custom repository mappings
        for abstract_type, implementation_type in self._repository_mappings.items():
            builder.services.add_scoped(abstract_type, implementation_type)

    return builder
```

---

## Usage After Enhancement

### Simple Case: Direct Repository Injection (No Custom Repository Needed)

```python
# main.py
DataAccessLayer.ReadModel(
    database_name="tools_provider",
    repository_type="motor",
).configure(builder, ["integration.models"])

# Query handler - inject Repository directly, use query() for complex queries
class GetTasksQueryHandler(QueryHandler[GetTasksQuery, OperationResult]):
    def __init__(self, task_repository: Repository[TaskDto, str]):
        self.task_repository = task_repository

    async def handle_async(self, request: GetTasksQuery) -> OperationResult:
        # Use built-in methods
        task = await self.task_repository.get_async(request.task_id)

        # Use queryable for complex queries
        tasks = await self.task_repository.query_async() \
            .where(lambda t: t.department == request.department) \
            .order_by(lambda t: t.created_at) \
            .to_list_async()

        return self.ok(tasks)
```

### Advanced Case: Custom Domain Repository

```python
# main.py - With custom repository mapping
DataAccessLayer.ReadModel(
    database_name="tools_provider",
    repository_type="motor",
    repository_mappings={
        TaskDtoRepository: MotorTaskDtoRepository,  # Custom implementation
    }
).configure(builder, ["integration.models"])

# Query handler - inject custom repository for domain-specific methods
class GetTasksQueryHandler(QueryHandler[GetTasksQuery, OperationResult]):
    def __init__(self, task_repository: TaskDtoRepository):
        self.task_repository = task_repository

    async def handle_async(self, request: GetTasksQuery) -> OperationResult:
        # Domain-specific methods
        if "admin" in request.user_info.get("roles", []):
            tasks = await self.task_repository.get_all_async()
        else:
            tasks = await self.task_repository.get_by_department_async(
                request.user_info.get("department")
            )
        return self.ok(tasks)
```

---

## Benefits

### 1. Consistency Between Sync and Async Drivers

- `MotorRepository` gains same queryable capabilities as `MongoRepository`
- FastAPI apps can use LINQ-style queries
- Parity between sync and async repository patterns

### 2. Simplified Configuration

- Single-line registration for custom repositories
- Convention over configuration
- Reduced boilerplate in `main.py`

### 3. Framework-Idiomatic Approach

- Follows existing patterns (`repository_mappings` similar to `options`)
- Backwards compatible (existing code works unchanged)
- Explicit configuration when needed

### 4. Type Safety

- Custom repository interfaces preserved
- IDE autocompletion for domain-specific methods
- Compile-time type checking

---

## Migration Path

### Phase 1: MotorRepository Queryable (Non-Breaking)

1. Add `MotorQuery` and `MotorQueryProvider` classes
2. Update `MotorRepository` to extend `QueryableRepository`
3. Add `query_async()` method implementation
4. Existing code continues to work

### Phase 2: DataAccessLayer Enhancement (Non-Breaking)

1. Add `repository_mappings` parameter (optional, defaults to empty dict)
2. Register `QueryableRepository[T, K]` alias for motor
3. Register query handlers for motor (like mongo)
4. Filter by `@queryable` decorator (consistent with mongo)

### Phase 3: Documentation

1. Update data access documentation
2. Add migration guide for existing custom repositories
3. Update examples to show queryable usage

---

## Files to Modify

| File | Changes |
|------|---------|
| `neuroglia/data/infrastructure/mongo/motor_repository.py` | Extend `QueryableRepository`, add `query_async()` |
| `neuroglia/data/infrastructure/mongo/motor_query.py` | NEW: `MotorQuery`, `MotorQueryProvider`, `MotorQueryBuilder` |
| `neuroglia/data/infrastructure/mongo/__init__.py` | Export new query classes |
| `neuroglia/hosting/configuration/data_access_layer.py` | Add `repository_mappings`, fix motor registration |

---

## Alternative Considered

### Option B: Separate Method for Custom Repository

Instead of `repository_mappings` dict, add a separate `with_repository()` method:

```python
DataAccessLayer.ReadModel(database_name="myapp", repository_type="motor") \
    .with_repository(TaskDtoRepository, MotorTaskDtoRepository) \
    .configure(builder, ["integration.models"])
```

**Pros:** Fluent API, chainable
**Cons:** More complex implementation, requires builder pattern changes

### Recommendation

Option A (constructor parameter) is simpler and consistent with existing `options` pattern in `WriteModel`.

---

## Test Cases

```python
# Test 1: MotorRepository extends QueryableRepository
def test_motor_repository_is_queryable():
    repo = MotorRepository[TaskDto, str](...)
    assert isinstance(repo, QueryableRepository)

# Test 2: query_async() returns proper Queryable
async def test_motor_query_async():
    repo = MotorRepository[TaskDto, str](...)
    query = await repo.query_async()
    assert isinstance(query, Queryable)

# Test 3: Custom repository registration via repository_mappings
def test_custom_repository_registration():
    builder = WebApplicationBuilder(...)
    DataAccessLayer.ReadModel(
        database_name="test",
        repository_type="motor",
        repository_mappings={TaskDtoRepository: MotorTaskDtoRepository}
    ).configure(builder, ["integration.models"])

    # Verify registration
    sp = builder.services.build_service_provider()
    repo = sp.get_service(TaskDtoRepository)
    assert isinstance(repo, MotorTaskDtoRepository)

# Test 4: Motor registers QueryableRepository alias
def test_motor_registers_queryable_repository():
    builder = WebApplicationBuilder(...)
    DataAccessLayer.ReadModel(
        database_name="test",
        repository_type="motor"
    ).configure(builder, ["integration.models"])

    sp = builder.services.build_service_provider()
    repo = sp.get_service(QueryableRepository[TaskDto, str])
    assert repo is not None
```

---

## References

- Current `MongoRepository` queryable implementation: `neuroglia/data/infrastructure/mongo/mongo_repository.py`
- `QueryableRepository` interface: `neuroglia/data/infrastructure/abstractions.py`
- `DataAccessLayer.ReadModel`: `neuroglia/hosting/configuration/data_access_layer.py`
- Motor async driver: https://motor.readthedocs.io/
