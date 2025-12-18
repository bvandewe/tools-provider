# Pattern Discovery Reference

**Document Version:** 1.0.0
**Last Updated:** December 18, 2025
**Purpose:** Authoritative reference for Neuroglia framework patterns used in this codebase

---

## ⚠️ CRITICAL: Read This First

This document contains **verified imports and patterns** extracted from the existing codebase.
When implementing new features, you **MUST** use these exact imports and patterns.

**DO NOT** guess or hallucinate Neuroglia imports. If a pattern is not documented here,
search the codebase or ask for clarification.

---

## 1. Verified Neuroglia Imports

### 1.1 Core

```python
from neuroglia.core import OperationResult
```

### 1.2 Mediation (CQRS)

```python
from neuroglia.mediation import Command, CommandHandler, Mediator
from neuroglia.mediation import Query, QueryHandler  # For queries
from neuroglia.mediation import DomainEventHandler  # For domain event projection handlers
```

### 1.3 Mapping

```python
from neuroglia.mapping import Mapper
```

### 1.4 Data Access

```python
from neuroglia.data.infrastructure.abstractions import Repository
```

### 1.5 Cloud Events

```python
from neuroglia.eventing.cloud_events.cloud_event import CloudEvent, CloudEventSpecVersion
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_bus import CloudEventBus
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import CloudEventPublishingOptions
from neuroglia.integration.models import IntegrationEvent
```

### 1.6 Observability

```python
from neuroglia.observability.tracing import add_span_attributes
```

### 1.7 Hosting & Dependency Injection

```python
from neuroglia.hosting.abstractions import ApplicationBuilderBase
from neuroglia.hosting.web import WebApplicationBuilder
```

---

## 2. Command Handler Pattern

### 2.1 File Location

- `src/{app}/application/commands/{entity}/{action}_{entity}_command.py`

### 2.2 Imports Template

```python
"""Command description."""

import logging
from dataclasses import dataclass
from typing import Any

from neuroglia.core import OperationResult
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_bus import CloudEventBus
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import CloudEventPublishingOptions
from neuroglia.mapping import Mapper
from neuroglia.mediation import Command, CommandHandler, Mediator

from application.commands.command_handler_base import CommandHandlerBase
from domain.entities.{entity} import {Entity}
from integration.models.{entity}_dto import {Entity}Dto

log = logging.getLogger(__name__)
```

### 2.3 Command Class

```python
@dataclass
class {Action}{Entity}Command(Command[OperationResult[{Entity}Dto]]):
    """Command to {action} a {entity}."""

    field_a: str
    field_b: int
    # Add fields as needed
```

### 2.4 Handler Class

```python
class {Action}{Entity}CommandHandler(
    CommandHandlerBase,
    CommandHandler[{Action}{Entity}Command, OperationResult[{Entity}Dto]],
):
    """Handler for {Action}{Entity}Command."""

    def __init__(
        self,
        mediator: Mediator,
        mapper: Mapper,
        cloud_event_bus: CloudEventBus,
        cloud_event_publishing_options: CloudEventPublishingOptions,
        {entity}_repository: Repository[{Entity}, str],
    ):
        super().__init__(
            mediator,
            mapper,
            cloud_event_bus,
            cloud_event_publishing_options,
        )
        self.{entity}_repository = {entity}_repository

    async def handle_async(
        self,
        request: {Action}{Entity}Command,
    ) -> OperationResult[{Entity}Dto]:
        """Handle the command."""
        # Implementation here
        pass
```

---

## 3. CommandHandlerBase Pattern

### 3.1 Location

- `src/{app}/application/commands/command_handler_base.py`

### 3.2 agent-host Implementation

```python
"""Command handler base class for Agent Host."""

import datetime
import logging
import uuid
from dataclasses import asdict

from neuroglia.eventing.cloud_events.cloud_event import CloudEvent, CloudEventSpecVersion
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_bus import CloudEventBus
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import CloudEventPublishingOptions
from neuroglia.integration.models import IntegrationEvent
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator

log = logging.getLogger(__name__)


class CommandHandlerBase:
    """Represents the base class for all command handlers.

    Note: Helper methods like ok(), not_found(), forbidden(), bad_request(), etc.
    are inherited from neuroglia.mediation.RequestHandler via CommandHandler.
    Do NOT duplicate them here.
    """

    mediator: Mediator
    mapper: Mapper
    cloud_event_bus: CloudEventBus
    cloud_event_publishing_options: CloudEventPublishingOptions

    def __init__(
        self,
        mediator: Mediator,
        mapper: Mapper,
        cloud_event_bus: CloudEventBus,
        cloud_event_publishing_options: CloudEventPublishingOptions,
    ):
        self.mediator = mediator
        self.mapper = mapper
        self.cloud_event_bus = cloud_event_bus
        self.cloud_event_publishing_options = cloud_event_publishing_options

    async def publish_cloud_event_async(self, ev: IntegrationEvent) -> None:
        """Publish a cloud event from an integration event."""
        # Implementation details in actual file
        pass
```

---

## 4. Query Handler Pattern

### 4.1 File Location

- `src/{app}/application/queries/{entity}/get_{entity}_query.py`

### 4.2 Template

```python
"""Query description."""

import logging
from dataclasses import dataclass

from neuroglia.core import OperationResult
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator, Query, QueryHandler

from domain.repositories import {Entity}DtoRepository
from integration.models.{entity}_dto import {Entity}Dto

log = logging.getLogger(__name__)


@dataclass
class Get{Entity}Query(Query[OperationResult[{Entity}Dto]]):
    """Query to get a {entity} by ID."""

    {entity}_id: str


class Get{Entity}QueryHandler(QueryHandler[Get{Entity}Query, OperationResult[{Entity}Dto]]):
    """Handler for Get{Entity}Query."""

    def __init__(
        self,
        mediator: Mediator,
        mapper: Mapper,
        {entity}_repository: {Entity}DtoRepository,
    ):
        self.mediator = mediator
        self.mapper = mapper
        self.{entity}_repository = {entity}_repository

    async def handle_async(
        self,
        request: Get{Entity}Query,
    ) -> OperationResult[{Entity}Dto]:
        """Handle the query."""
        # Implementation here
        pass
```

---

## 5. Domain Event Handler Pattern (Projection Handlers)

### 5.1 How It Works

**Critical Understanding:**

- The `Repository` base class (`neuroglia.data.infrastructure.abstractions.Repository`) **automatically publishes domain events** to the Mediator after `add_async()` and `update_async()` operations.
- The Mediator **automatically discovers handlers** as long as their package is registered in `main.py`.
- No decorators needed - just extend `DomainEventHandler[TEvent]`.

### 5.2 File Location

- `src/{app}/application/events/domain/{entity}_projection_handlers.py`

### 5.3 Package Registration in main.py

```python
# In main.py - register the events package for auto-discovery
Mediator.configure(builder, [
    "application.commands",
    "application.queries",
    "application.events",           # General events
    "application.events.domain",    # Domain event projection handlers
])
```

### 5.4 Verified Pattern (from task_projection_handlers.py)

```python
"""Read Model Projection Handlers for {Entity} Aggregate.

These handlers listen to domain events and update the MongoDB read model accordingly.
The Repository automatically publishes domain events to the Mediator after persistence.
"""

import logging
from datetime import UTC, datetime

from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.mediation import DomainEventHandler

from domain.events import (
    {Entity}CreatedDomainEvent,
    {Entity}UpdatedDomainEvent,
    {Entity}DeletedDomainEvent,
)
from integration.models.{entity}_dto import {Entity}Dto

logger = logging.getLogger(__name__)


class {Entity}CreatedProjectionHandler(DomainEventHandler[{Entity}CreatedDomainEvent]):
    """Projects {Entity}CreatedDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[{Entity}Dto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: {Entity}CreatedDomainEvent) -> None:
        """Create {Entity}Dto in Read Model."""
        logger.info(f"📥 Projecting {Entity}Created: {event.aggregate_id}")

        # Idempotency check - skip if already exists
        existing = await self._repository.get_async(event.aggregate_id)
        if existing:
            logger.info(f"⏭️ {Entity} already exists in Read Model, skipping: {event.aggregate_id}")
            return

        # Map domain event to DTO
        dto = {Entity}Dto(
            id=event.aggregate_id,
            # ... map fields from event
            created_at=event.created_at,
            updated_at=event.updated_at,
        )

        await self._repository.add_async(dto)
        logger.info(f"✅ Projected {Entity}Created to Read Model: {event.aggregate_id}")


class {Entity}UpdatedProjectionHandler(DomainEventHandler[{Entity}UpdatedDomainEvent]):
    """Projects {Entity}UpdatedDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[{Entity}Dto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: {Entity}UpdatedDomainEvent) -> None:
        """Update {Entity} in Read Model."""
        logger.info(f"📥 Projecting {Entity}Updated: {event.aggregate_id}")

        entity = await self._repository.get_async(event.aggregate_id)
        if entity:
            # Update fields from event
            entity.updated_at = datetime.now(UTC)
            await self._repository.update_async(entity)
            logger.info(f"✅ Projected {Entity}Updated to Read Model: {event.aggregate_id}")
        else:
            logger.warning(f"⚠️ {Entity} not found in Read Model: {event.aggregate_id}")
```

### 5.5 Key Points

| Aspect | Pattern |
|--------|--------|
| Base class | `DomainEventHandler[TEvent]` |
| Method | `async def handle_async(self, event: TEvent) -> None` |
| Constructor | Call `super().__init__()` |
| Idempotency | Always check if entity exists before creating |
| Decorators | **NONE required** - auto-discovered via Mediator |

---

## 6. Controller Pattern

### 6.1 File Location

- `src/{app}/api/controllers/{entity}_controller.py`

### 6.2 Example

```python
"""Controller for {entity} endpoints."""

from typing import Annotated

from classy_fastapi import Routable, get, post, put, delete
from fastapi import Depends, Response

from api.controller_base import ControllerBase
from api.dependencies import get_current_user
from neuroglia.mediation import Mediator

from application.commands import {Action}{Entity}Command
from application.queries import Get{Entity}Query


class {Entity}Controller(ControllerBase, Routable):
    """REST controller for {entity} operations."""

    def __init__(self, mediator: Mediator):
        super().__init__(mediator)

    @get("/{id}")
    async def get_{entity}(
        self,
        id: str,
        user: dict = Depends(get_current_user),
    ) -> Response:
        """Get {entity} by ID."""
        query = Get{Entity}Query({entity}_id=id)
        result = await self.mediator.execute_async(query)
        return self.process(result)
```

---

## 7. Repository Patterns

### 7.1 Write Model (Aggregate Repository)

```python
from neuroglia.data.infrastructure.abstractions import Repository

# Usage in handler constructor:
{entity}_repository: Repository[{Entity}, str]
```

### 7.2 Read Model (DTO Repository)

```python
from domain.repositories import {Entity}DtoRepository

# Custom repository interface in domain/repositories/
```

### 7.3 Automatic Domain Event Publishing

**Critical:** The `Repository` base class automatically publishes domain events:

```python
# From neuroglia.data.infrastructure.abstractions.Repository:

async def add_async(self, entity: TEntity) -> TEntity:
    """Adds entity and automatically publishes its domain events."""
    result = await self._do_add_async(entity)
    await self._publish_domain_events(entity)  # Auto-publishes to Mediator!
    return result

async def update_async(self, entity: TEntity) -> TEntity:
    """Updates entity and automatically publishes its domain events."""
    result = await self._do_update_async(entity)
    await self._publish_domain_events(entity)  # Auto-publishes to Mediator!
    return result
```

This means:

- Domain events on AggregateRoot entities are **automatically published** after persistence.
- DomainEventHandler classes are **automatically discovered** by the Mediator.
- No manual event dispatching required in command handlers.

---

## 8. Dependency Injection Registration Pattern

### 8.1 The `configure()` Static Method Pattern

**All services should use a static `configure()` method for DI registration.**

```python
from neuroglia.hosting.abstractions import ApplicationBuilderBase


class MyService:
    """Example service."""

    def __init__(self, dependency_a: DependencyA, dependency_b: DependencyB):
        self._dependency_a = dependency_a
        self._dependency_b = dependency_b

    @staticmethod
    def configure(builder: ApplicationBuilderBase) -> None:
        """
        Configure MyService in the service collection.

        Follows Neuroglia framework pattern for service registration.

        Args:
            builder: The application builder
        """
        # Option 1: Simple singleton with factory
        def create_service(sp):
            return MyService(
                dependency_a=sp.get_required_service(DependencyA),
                dependency_b=sp.get_required_service(DependencyB),
            )

        builder.services.add_singleton(MyService, implementation_factory=create_service)

        # Option 2: Scoped (one per request) - preferred for request-scoped services
        # builder.services.add_scoped(MyService, implementation_factory=create_service)
```

### 8.2 Retrieving Settings in configure()

```python
@staticmethod
def configure(builder: ApplicationBuilderBase) -> None:
    # Get settings from builder
    settings = next(
        (d.singleton for d in builder.services if d.service_type is Settings),
        None,
    )

    if settings is None:
        logger.warning("Settings not found in services, using defaults")
        settings = Settings()

    # Use settings to configure service
    client = MyService(base_url=settings.my_service_url)
    builder.services.add_singleton(MyService, singleton=client)
```

### 8.3 MotorRepository.configure() - Full Example

See the Neuroglia source for comprehensive example with:

- Connection string resolution from settings
- Singleton vs scoped registration
- Domain interface registration
- Custom implementation types

**Reference:** `.venv/lib/python3.12/site-packages/neuroglia/data/infrastructure/mongo/motor_repository.py`

### 8.4 Calling configure() in main.py

```python
# In main.py
from my_module import MyService

def create_app() -> FastAPI:
    builder = WebApplicationBuilder(app_settings=app_settings)

    # Configure core Neuroglia services first
    Mediator.configure(builder, ["application.commands", "application.queries", "application.events.domain"])
    Mapper.configure(builder, ["application.mapping", "integration.models"])
    JsonSerializer.configure(builder, ["domain.entities", "domain.models"])

    # Configure repositories
    MotorRepository.configure(
        builder,
        entity_type=MyEntity,
        key_type=str,
        database_name="my_database",
    )

    # Configure custom services
    MyService.configure(builder)
```

---

## 9. Files to Read Before Implementing

When starting WebSocket implementation, read these files first:

### agent-host Application

| File | Purpose |
|------|---------|
| `src/agent-host/main.py` | DI registration & Mediator package discovery |
| `src/agent-host/application/commands/command_handler_base.py` | Base class pattern |
| `src/agent-host/application/commands/conversation/create_conversation_command.py` | Command example |
| `src/agent-host/application/queries/` | Query patterns |
| `src/agent-host/api/controllers/` | Controller patterns |

### tools-provider Reference (more mature patterns)

| File | Purpose |
|------|---------|
| `src/tools-provider/application/commands/source/register_source_command.py` | Full command example |
| `src/tools-provider/application/events/domain/task_projection_handlers.py` | **Domain event handler pattern** |
| `src/tools-provider/domain/entities/` | Aggregate patterns |

### Neuroglia Framework Source (for deep understanding)

| File | Purpose |
|------|---------|
| `.venv/.../neuroglia/data/infrastructure/abstractions.py` | Repository with auto event publishing |
| `.venv/.../neuroglia/data/infrastructure/mongo/motor_repository.py` | `configure()` DI pattern |

---

## 10. What's NOT in Neuroglia (Verified Gaps)

The following patterns are **NOT** part of Neuroglia and must be implemented:

| Pattern | Status | Notes |
|---------|--------|-------|
| WebSocket handling | Custom | Use Starlette WebSocket directly |
| Connection management | Custom | Implement ConnectionManager |
| Message routing | Custom | Implement MessageRouter |
| Rate limiting | Custom | Implement middleware |
| Redis PubSub | Custom | Use redis-py or aioredis |

---

## 11. Verification Commands

Run these to verify patterns before implementing:

```bash
# Find all Neuroglia imports in agent-host
grep -r "from neuroglia" src/agent-host/ --include="*.py"

# Find command handler examples
find src/agent-host/application/commands -name "*.py" -type f

# Find query handler examples
find src/agent-host/application/queries -name "*.py" -type f

# Find controller examples
find src/agent-host/api/controllers -name "*.py" -type f
```

---

_This document is auto-generated from codebase analysis. Update when Neuroglia framework changes._
