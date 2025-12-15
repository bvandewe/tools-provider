"""
Read Model Projection Handlers for UpstreamSource Aggregate.

These handlers listen to domain events streamed by the ReadModelReconciliator
and update the MongoDB read model accordingly.

The ReadModelReconciliator subscribes to EventStoreDB's category stream ($ce-tools_provider)
and publishes each event through the Mediator. These handlers receive those events
and project them to MongoDB, keeping the Read Model in sync with the Write Model.
"""

import logging

from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.mediation import DomainEventHandler

from domain.enums import HealthStatus
from domain.events.upstream_source import (
    InventoryIngestedDomainEvent,
    SourceDeregisteredDomainEvent,
    SourceDisabledDomainEvent,
    SourceEnabledDomainEvent,
    SourceHealthChangedDomainEvent,
    SourceRegisteredDomainEvent,
    SourceSyncFailedDomainEvent,
    SourceUpdatedDomainEvent,
)
from integration.models.source_dto import SourceDto

logger = logging.getLogger(__name__)


class SourceRegisteredProjectionHandler(DomainEventHandler[SourceRegisteredDomainEvent]):
    """Projects SourceRegisteredDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[SourceDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: SourceRegisteredDomainEvent) -> None:
        """Create SourceDto in Read Model."""
        logger.info(f"📥 Projecting SourceRegistered: {event.aggregate_id}")

        # Idempotency check - skip if already exists
        existing = await self._repository.get_async(event.aggregate_id)
        if existing:
            logger.info(f"⏭️ Source already exists in Read Model, skipping: {event.aggregate_id}")
            return

        # Map domain event to DTO
        source_dto = SourceDto(
            id=event.aggregate_id,
            name=event.name,
            url=event.url,
            source_type=event.source_type,
            health_status=HealthStatus.UNKNOWN,
            is_enabled=True,
            inventory_count=0,
            inventory_hash="",
            last_sync_at=None,
            last_sync_error=None,
            consecutive_failures=0,
            created_at=event.created_at,
            updated_at=event.created_at,
            created_by=event.created_by,
            default_audience=event.default_audience,
            openapi_url=event.openapi_url,
            description=event.description,
            auth_mode=event.auth_mode,
            required_scopes=event.required_scopes or [],
            mcp_config=event.mcp_config,
        )

        await self._repository.add_async(source_dto)
        logger.info(f"✅ Projected SourceRegistered to Read Model: {event.aggregate_id}")


class InventoryIngestedProjectionHandler(DomainEventHandler[InventoryIngestedDomainEvent]):
    """Projects InventoryIngestedDomainEvent to MongoDB Read Model.

    Updates the source's inventory metadata and health status.
    The actual tool definitions are handled separately.
    """

    def __init__(self, repository: Repository[SourceDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: InventoryIngestedDomainEvent) -> None:
        """Update source inventory info in Read Model."""
        logger.info(f"📥 Projecting InventoryIngested: {event.aggregate_id} ({event.tool_count} tools)")

        source = await self._repository.get_async(event.aggregate_id)
        if source:
            source.inventory_count = event.tool_count
            source.inventory_hash = event.inventory_hash
            source.last_sync_at = event.ingested_at
            source.last_sync_error = None
            source.consecutive_failures = 0
            source.health_status = HealthStatus.HEALTHY
            source.updated_at = event.ingested_at

            await self._repository.update_async(source)
            logger.info(f"✅ Projected InventoryIngested to Read Model: {event.aggregate_id}")
        else:
            logger.warning(f"⚠️ Source not found in Read Model for inventory update: {event.aggregate_id}")


class SourceSyncFailedProjectionHandler(DomainEventHandler[SourceSyncFailedDomainEvent]):
    """Projects SourceSyncFailedDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[SourceDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: SourceSyncFailedDomainEvent) -> None:
        """Update source sync failure info in Read Model."""
        logger.info(f"📥 Projecting SourceSyncFailed: {event.aggregate_id} (attempt {event.attempt})")

        source = await self._repository.get_async(event.aggregate_id)
        if source:
            source.last_sync_error = event.error
            source.consecutive_failures = event.attempt
            source.updated_at = event.failed_at

            # Update health status based on failure count
            if event.attempt >= 3:
                source.health_status = HealthStatus.UNHEALTHY
            elif event.attempt >= 1:
                source.health_status = HealthStatus.DEGRADED

            await self._repository.update_async(source)
            logger.info(f"✅ Projected SourceSyncFailed to Read Model: {event.aggregate_id}")
        else:
            logger.warning(f"⚠️ Source not found in Read Model for sync failure: {event.aggregate_id}")


class SourceHealthChangedProjectionHandler(DomainEventHandler[SourceHealthChangedDomainEvent]):
    """Projects SourceHealthChangedDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[SourceDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: SourceHealthChangedDomainEvent) -> None:
        """Update source health status in Read Model."""
        logger.info(f"📥 Projecting SourceHealthChanged: {event.aggregate_id} ({event.old_status} → {event.new_status})")

        source = await self._repository.get_async(event.aggregate_id)
        if source:
            source.health_status = event.new_status
            source.updated_at = event.changed_at

            await self._repository.update_async(source)
            logger.info(f"✅ Projected SourceHealthChanged to Read Model: {event.aggregate_id}")
        else:
            logger.warning(f"⚠️ Source not found in Read Model for health update: {event.aggregate_id}")


class SourceEnabledProjectionHandler(DomainEventHandler[SourceEnabledDomainEvent]):
    """Projects SourceEnabledDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[SourceDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: SourceEnabledDomainEvent) -> None:
        """Enable source in Read Model."""
        logger.info(f"📥 Projecting SourceEnabled: {event.aggregate_id}")

        source = await self._repository.get_async(event.aggregate_id)
        if source:
            source.is_enabled = True
            source.updated_at = event.enabled_at

            await self._repository.update_async(source)
            logger.info(f"✅ Projected SourceEnabled to Read Model: {event.aggregate_id}")
        else:
            logger.warning(f"⚠️ Source not found in Read Model for enable: {event.aggregate_id}")


class SourceDisabledProjectionHandler(DomainEventHandler[SourceDisabledDomainEvent]):
    """Projects SourceDisabledDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[SourceDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: SourceDisabledDomainEvent) -> None:
        """Disable source in Read Model."""
        logger.info(f"📥 Projecting SourceDisabled: {event.aggregate_id}")

        source = await self._repository.get_async(event.aggregate_id)
        if source:
            source.is_enabled = False
            source.updated_at = event.disabled_at

            await self._repository.update_async(source)
            logger.info(f"✅ Projected SourceDisabled to Read Model: {event.aggregate_id}")
        else:
            logger.warning(f"⚠️ Source not found in Read Model for disable: {event.aggregate_id}")


class SourceDeregisteredProjectionHandler(DomainEventHandler[SourceDeregisteredDomainEvent]):
    """Projects SourceDeregisteredDomainEvent to MongoDB Read Model.

    Depending on delete mode (soft vs hard), either marks as disabled
    or removes from the read model.
    """

    def __init__(self, repository: Repository[SourceDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: SourceDeregisteredDomainEvent) -> None:
        """Handle source deregistration in Read Model."""
        logger.info(f"📥 Projecting SourceDeregistered: {event.aggregate_id}")

        source = await self._repository.get_async(event.aggregate_id)
        if source:
            # For now, just disable. Could also delete based on configuration.
            source.is_enabled = False
            source.updated_at = event.deregistered_at

            await self._repository.update_async(source)
            logger.info(f"✅ Projected SourceDeregistered to Read Model: {event.aggregate_id}")
        else:
            logger.warning(f"⚠️ Source not found in Read Model for deregistration: {event.aggregate_id}")


class SourceUpdatedProjectionHandler(DomainEventHandler[SourceUpdatedDomainEvent]):
    """Projects SourceUpdatedDomainEvent to MongoDB Read Model.

    Updates the source's editable fields: name, description, url.
    """

    def __init__(self, repository: Repository[SourceDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: SourceUpdatedDomainEvent) -> None:
        """Update source fields in Read Model."""
        logger.info(f"📥 Projecting SourceUpdated: {event.aggregate_id}")

        source = await self._repository.get_async(event.aggregate_id)
        if source:
            if event.name is not None:
                source.name = event.name
            if event.description is not None:
                source.description = event.description
            if event.url is not None:
                source.url = event.url
            if event.required_scopes is not None:
                source.required_scopes = event.required_scopes
            source.updated_at = event.updated_at

            await self._repository.update_async(source)
            logger.info(f"✅ Projected SourceUpdated to Read Model: {event.aggregate_id}")
        else:
            logger.warning(f"⚠️ Source not found in Read Model for update: {event.aggregate_id}")
