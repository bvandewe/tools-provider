# Neuroglia Framework Enhancement: Simplified Repository Configuration

**Date**: December 2, 2025
**Submitted By**: tools-provider team
**Framework Version**: neuroglia-python v0.6.x
**Priority**: Medium
**Type**: Enhancement Request (Developer Experience)

---

## Summary

Request to simplify the `DataAccessLayer.WriteModel()` configuration API to support `EventSourcingRepositoryOptions` (specifically `DeleteMode`) without requiring users to write verbose custom factory functions.

---

## Current Behavior

### Problem: Verbose Custom Factory Required

When users need to configure `EventSourcingRepository` with custom options (e.g., `DeleteMode.HARD` for GDPR compliance), they must write a **37-line custom factory function**:

```python
# Current: 37 lines of boilerplate for a simple configuration change
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.data.infrastructure.event_sourcing.abstractions import (
    Aggregator, DeleteMode, EventStore
)
from neuroglia.data.infrastructure.event_sourcing.event_sourcing_repository import (
    EventSourcingRepository, EventSourcingRepositoryOptions
)
from neuroglia.dependency_injection import ServiceProvider

def configure_eventsourcing_repository(
    builder_: "WebApplicationBuilder",
    entity_type: type,
    key_type: type
) -> "WebApplicationBuilder":
    """Configure EventSourcingRepository with HARD delete mode enabled."""

    # Create options with HARD delete mode
    options = EventSourcingRepositoryOptions[entity_type, key_type](
        delete_mode=DeleteMode.HARD
    )

    # Factory function to create repository with explicit options
    def repository_factory(sp: ServiceProvider) -> EventSourcingRepository[entity_type, key_type]:
        eventstore = sp.get_required_service(EventStore)
        aggregator = sp.get_required_service(Aggregator)
        mediator = sp.get_service(Mediator)
        return EventSourcingRepository[entity_type, key_type](
            eventstore=eventstore,
            aggregator=aggregator,
            mediator=mediator,
            options=options,
        )

    # Register the repository with factory
    builder_.services.add_singleton(
        Repository[entity_type, key_type],
        implementation_factory=repository_factory,
    )
    return builder_

# Usage
DataAccessLayer.WriteModel().configure(
    builder,
    ["domain.entities"],
    configure_eventsourcing_repository,  # Custom factory required
)
```

### Issues with Current Approach

1. **Boilerplate Heavy**: 37 lines for a one-line configuration change (`delete_mode=DeleteMode.HARD`)
2. **Error Prone**: Users must manually resolve `EventStore`, `Aggregator`, and `Mediator` from `ServiceProvider`
3. **Inconsistent**: Other components like `ESEventStore`, `CloudEventPublisher`, `Mediator` use simple `.configure(builder, ...)` patterns
4. **Undiscoverable**: Users must read framework source code to understand how to customize repository creation
5. **Repetitive**: Every project needing custom options must copy this same boilerplate

---

## Proposed Enhancement

### Option 1: Add `options` Parameter to `DataAccessLayer.WriteModel()`

The simplest enhancement - add an optional `options` parameter:

```python
# Proposed: Single line configuration
DataAccessLayer.WriteModel(
    options=EventSourcingRepositoryOptions(delete_mode=DeleteMode.HARD)
).configure(
    builder,
    ["domain.entities"],
)
```

### Option 2: Fluent Builder Pattern

More flexible for future extensions:

```python
# Proposed: Fluent configuration
DataAccessLayer.WriteModel() \
    .with_delete_mode(DeleteMode.HARD) \
    .configure(builder, ["domain.entities"])
```

### Option 3: Static Factory Method on EventSourcingRepository

Align with other framework components that use `.configure()` pattern:

```python
# Proposed: Consistent with ESEventStore.configure(), CloudEventPublisher.configure(), etc.
EventSourcingRepository.configure(
    builder,
    ["domain.entities"],
    options=EventSourcingRepositoryOptions(delete_mode=DeleteMode.HARD),
)
```

---

## Recommended Implementation (Option 1)

### Changes to `DataAccessLayer` Class

```python
# neuroglia/hosting/configuration/data_access_layer.py

from dataclasses import dataclass, field
from typing import Optional, Callable, List
from neuroglia.data.infrastructure.event_sourcing.event_sourcing_repository import (
    EventSourcingRepository, EventSourcingRepositoryOptions
)

@dataclass
class WriteModelConfiguration:
    """Configuration for the Write Model (Event Sourcing)."""

    options: Optional[EventSourcingRepositoryOptions] = None

    def configure(
        self,
        builder: "WebApplicationBuilder",
        entity_packages: List[str],
        custom_configurator: Optional[Callable] = None,  # Still allow full customization
    ) -> "WebApplicationBuilder":
        """
        Configure the Write Model with EventSourcingRepository.

        Args:
            builder: The web application builder
            entity_packages: List of packages containing aggregate root entities
            custom_configurator: Optional custom configuration function (overrides options)
        """
        if custom_configurator:
            # Allow full customization if needed (backwards compatible)
            return self._configure_with_custom(builder, entity_packages, custom_configurator)

        # Use simplified configuration with options
        return self._configure_with_options(builder, entity_packages)

    def _configure_with_options(
        self,
        builder: "WebApplicationBuilder",
        entity_packages: List[str],
    ) -> "WebApplicationBuilder":
        """Configure repositories using the provided options."""
        from neuroglia.data.infrastructure.abstractions import Repository
        from neuroglia.data.infrastructure.event_sourcing.abstractions import (
            Aggregator, EventStore
        )
        from neuroglia.dependency_injection import ServiceProvider
        from neuroglia.mediation import Mediator

        # Discover aggregate types from packages
        aggregate_types = self._discover_aggregates(entity_packages)

        for entity_type, key_type in aggregate_types:
            # Create type-specific options if global options provided
            typed_options = None
            if self.options:
                typed_options = EventSourcingRepositoryOptions[entity_type, key_type](
                    delete_mode=self.options.delete_mode
                )

            # Factory function captures typed_options
            def make_factory(et, kt, opts):
                def repository_factory(sp: ServiceProvider):
                    return EventSourcingRepository[et, kt](
                        eventstore=sp.get_required_service(EventStore),
                        aggregator=sp.get_required_service(Aggregator),
                        mediator=sp.get_service(Mediator),
                        options=opts,
                    )
                return repository_factory

            builder.services.add_singleton(
                Repository[entity_type, key_type],
                implementation_factory=make_factory(entity_type, key_type, typed_options),
            )

        return builder


class DataAccessLayer:
    """Factory for data access layer configurations."""

    @staticmethod
    def WriteModel(
        options: Optional[EventSourcingRepositoryOptions] = None,
    ) -> WriteModelConfiguration:
        """
        Create a Write Model configuration for Event Sourcing.

        Args:
            options: Optional repository options (e.g., delete_mode)

        Returns:
            WriteModelConfiguration instance

        Example:
            # Simple (default options)
            DataAccessLayer.WriteModel().configure(builder, ["domain.entities"])

            # With HARD delete mode
            DataAccessLayer.WriteModel(
                options=EventSourcingRepositoryOptions(delete_mode=DeleteMode.HARD)
            ).configure(builder, ["domain.entities"])
        """
        return WriteModelConfiguration(options=options)

    @staticmethod
    def ReadModel() -> "ReadModelConfiguration":
        """Create a Read Model configuration for MongoDB."""
        return ReadModelConfiguration()
```

---

## Usage Comparison

### Before (Current - 37 lines)

```python
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.data.infrastructure.event_sourcing.abstractions import (
    Aggregator, DeleteMode, EventStore
)
from neuroglia.data.infrastructure.event_sourcing.event_sourcing_repository import (
    EventSourcingRepository, EventSourcingRepositoryOptions
)
from neuroglia.dependency_injection import ServiceProvider
from neuroglia.mediation import Mediator

def configure_eventsourcing_repository(builder_, entity_type, key_type):
    options = EventSourcingRepositoryOptions[entity_type, key_type](
        delete_mode=DeleteMode.HARD
    )

    def repository_factory(sp: ServiceProvider):
        eventstore = sp.get_required_service(EventStore)
        aggregator = sp.get_required_service(Aggregator)
        mediator = sp.get_service(Mediator)
        return EventSourcingRepository[entity_type, key_type](
            eventstore=eventstore,
            aggregator=aggregator,
            mediator=mediator,
            options=options,
        )

    builder_.services.add_singleton(
        Repository[entity_type, key_type],
        implementation_factory=repository_factory,
    )
    return builder_

DataAccessLayer.WriteModel().configure(
    builder,
    ["domain.entities"],
    configure_eventsourcing_repository,
)
```

### After (Proposed - 5 lines)

```python
from neuroglia.data.infrastructure.event_sourcing.abstractions import DeleteMode
from neuroglia.data.infrastructure.event_sourcing.event_sourcing_repository import (
    EventSourcingRepositoryOptions
)

DataAccessLayer.WriteModel(
    options=EventSourcingRepositoryOptions(delete_mode=DeleteMode.HARD)
).configure(builder, ["domain.entities"])
```

**Reduction: 37 lines → 5 lines (86% less boilerplate)**

---

## Backwards Compatibility

The proposal maintains full backwards compatibility:

1. **Default behavior unchanged**: `DataAccessLayer.WriteModel().configure(...)` without options works exactly as before
2. **Custom factory still supported**: The third parameter for custom configurators is still accepted and takes precedence
3. **No breaking changes**: Existing code continues to work without modification

---

## Additional Considerations

### Future Options Support

The `EventSourcingRepositoryOptions` class could be extended with additional options:

```python
@dataclass
class EventSourcingRepositoryOptions(Generic[TAggregate, TKey]):
    """Options for configuring EventSourcingRepository behavior."""

    delete_mode: DeleteMode = DeleteMode.DISABLED

    # Future options:
    # snapshot_frequency: int = 0  # Enable snapshots every N events
    # cache_enabled: bool = False  # Enable in-memory caching
    # optimistic_concurrency: bool = True  # Concurrency control mode
```

### Consistency with Other Framework Components

This pattern would align `DataAccessLayer` with other Neuroglia components:

| Component | Current Pattern |
|-----------|-----------------|
| `ESEventStore` | `.configure(builder, options)` ✅ |
| `CloudEventPublisher` | `.configure(builder)` ✅ |
| `Mediator` | `.configure(builder, packages)` ✅ |
| `DataAccessLayer.WriteModel` | `.configure(builder, packages, custom_factory)` ❌ |

---

## Summary

| Aspect | Before | After |
|--------|--------|-------|
| Lines of code | 37 | 5 |
| Custom factory required | Yes | No |
| Type-safe options | Manual | Built-in |
| Error-prone DI resolution | Yes | Handled by framework |
| Discoverable API | No | Yes (IDE autocomplete) |

This enhancement would significantly improve the developer experience for Neuroglia framework users who need to customize `EventSourcingRepository` behavior.

---

## References

- Related: [NEUROGLIA_EVENTSOURCING_DELETE_ENHANCEMENT.md](./NEUROGLIA_EVENTSOURCING_DELETE_ENHANCEMENT.md) - DeleteMode implementation
- Related: [NEUROGLIA_EVENTSOURCING_ARCHITECTURE.md](./NEUROGLIA_EVENTSOURCING_ARCHITECTURE.md) - Event sourcing data flow
