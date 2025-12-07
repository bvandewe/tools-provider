"""Projection handlers for SourceTool domain events.

These handlers project domain events to the MongoDB read model (SourceToolDto).
They subscribe to events from EventStoreDB and update the MongoDB projections.

Following the Task projection handler pattern:
- DomainEventHandler[TEvent] base class
- Idempotency checks before updates
- Handles creation, updates, and soft deletes
"""

import logging

from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.mediation import DomainEventHandler

from domain.events.source_tool import (
    LabelAddedToToolDomainEvent,
    LabelRemovedFromToolDomainEvent,
    SourceToolDefinitionUpdatedDomainEvent,
    SourceToolDeprecatedDomainEvent,
    SourceToolDisabledDomainEvent,
    SourceToolDiscoveredDomainEvent,
    SourceToolEnabledDomainEvent,
    SourceToolRestoredDomainEvent,
)
from domain.models import ToolDefinition
from integration.models.source_dto import SourceDto
from integration.models.source_tool_dto import SourceToolDto

logger = logging.getLogger(__name__)


class SourceToolDiscoveredProjectionHandler(DomainEventHandler[SourceToolDiscoveredDomainEvent]):
    """Projects SourceToolDiscoveredDomainEvent to MongoDB Read Model."""

    def __init__(
        self,
        tool_repository: Repository[SourceToolDto, str],
        source_repository: Repository[SourceDto, str],
    ):
        super().__init__()
        self._tool_repository = tool_repository
        self._source_repository = source_repository

    async def handle_async(self, event: SourceToolDiscoveredDomainEvent) -> None:
        """Handle tool discovered event - creates new SourceToolDto."""
        logger.debug(f"Projecting SourceToolDiscoveredDomainEvent: {event.aggregate_id}")

        # Idempotency check
        existing = await self._tool_repository.get_async(event.aggregate_id)
        if existing:
            logger.debug(f"SourceTool {event.aggregate_id} already exists, skipping projection")
            return

        # Get source name for denormalization
        source_name = ""
        if self._source_repository:
            source = await self._source_repository.get_async(event.source_id)
            if source:
                source_name = source.name

        # Parse definition for summary fields
        definition = ToolDefinition.from_dict(event.definition) if event.definition else None

        dto = SourceToolDto(
            id=event.aggregate_id,
            source_id=event.source_id,
            source_name=source_name,
            tool_name=event.tool_name,
            operation_id=event.operation_id,
            description=definition.description if definition else "",
            input_schema=definition.input_schema if definition else {},
            method=definition.execution_profile.method if definition else "",
            path=definition.source_path if definition else "",
            tags=definition.tags if definition else [],
            execution_mode=definition.execution_profile.mode.value if definition else "sync_http",
            required_audience=definition.execution_profile.required_audience if definition else "",
            timeout_seconds=definition.execution_profile.timeout_seconds if definition else 30,
            is_enabled=True,  # Tools enabled by default
            status="active",
            discovered_at=event.discovered_at,
            last_seen_at=event.discovered_at,
            updated_at=event.discovered_at,
            definition=event.definition,
        )

        await self._tool_repository.add_async(dto)
        logger.info(f"Projected new SourceTool: {event.aggregate_id}")


class SourceToolEnabledProjectionHandler(DomainEventHandler[SourceToolEnabledDomainEvent]):
    """Projects SourceToolEnabledDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[SourceToolDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: SourceToolEnabledDomainEvent) -> None:
        """Handle tool enabled event - updates is_enabled flag."""
        logger.debug(f"Projecting SourceToolEnabledDomainEvent: {event.aggregate_id}")

        existing = await self._repository.get_async(event.aggregate_id)
        if not existing:
            logger.warning(f"SourceTool {event.aggregate_id} not found for enabled projection")
            return

        existing.is_enabled = True
        existing.enabled_by = event.enabled_by
        existing.disabled_by = None
        existing.disable_reason = None
        existing.updated_at = event.enabled_at

        await self._repository.update_async(existing)
        logger.info(f"Projected SourceTool enabled: {event.aggregate_id}")


class SourceToolDisabledProjectionHandler(DomainEventHandler[SourceToolDisabledDomainEvent]):
    """Projects SourceToolDisabledDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[SourceToolDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: SourceToolDisabledDomainEvent) -> None:
        """Handle tool disabled event - updates is_enabled flag."""
        logger.debug(f"Projecting SourceToolDisabledDomainEvent: {event.aggregate_id}")

        existing = await self._repository.get_async(event.aggregate_id)
        if not existing:
            logger.warning(f"SourceTool {event.aggregate_id} not found for disabled projection")
            return

        existing.is_enabled = False
        existing.disabled_by = event.disabled_by
        existing.disable_reason = event.reason
        existing.updated_at = event.disabled_at

        await self._repository.update_async(existing)
        logger.info(f"Projected SourceTool disabled: {event.aggregate_id}")


class SourceToolDefinitionUpdatedProjectionHandler(DomainEventHandler[SourceToolDefinitionUpdatedDomainEvent]):
    """Projects SourceToolDefinitionUpdatedDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[SourceToolDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: SourceToolDefinitionUpdatedDomainEvent) -> None:
        """Handle definition updated event - updates tool details."""
        logger.debug(f"Projecting SourceToolDefinitionUpdatedDomainEvent: {event.aggregate_id}")

        existing = await self._repository.get_async(event.aggregate_id)
        if not existing:
            logger.warning(f"SourceTool {event.aggregate_id} not found for definition update projection")
            return

        # Parse new definition
        definition = ToolDefinition.from_dict(event.new_definition) if event.new_definition else None

        if definition:
            existing.description = definition.description
            existing.input_schema = definition.input_schema
            existing.method = definition.execution_profile.method
            existing.path = definition.source_path
            existing.tags = definition.tags
            existing.execution_mode = definition.execution_profile.mode.value
            existing.required_audience = definition.execution_profile.required_audience
            existing.timeout_seconds = definition.execution_profile.timeout_seconds
            existing.definition = event.new_definition

        existing.last_seen_at = event.updated_at
        existing.updated_at = event.updated_at

        await self._repository.update_async(existing)
        logger.info(f"Projected SourceTool definition updated: {event.aggregate_id}")


class SourceToolDeprecatedProjectionHandler(DomainEventHandler[SourceToolDeprecatedDomainEvent]):
    """Projects SourceToolDeprecatedDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[SourceToolDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: SourceToolDeprecatedDomainEvent) -> None:
        """Handle tool deprecated event - marks as deprecated."""
        logger.debug(f"Projecting SourceToolDeprecatedDomainEvent: {event.aggregate_id}")

        existing = await self._repository.get_async(event.aggregate_id)
        if not existing:
            logger.warning(f"SourceTool {event.aggregate_id} not found for deprecated projection")
            return

        existing.status = "deprecated"
        existing.is_enabled = False  # Deprecated tools are automatically disabled
        existing.updated_at = event.deprecated_at

        await self._repository.update_async(existing)
        logger.info(f"Projected SourceTool deprecated: {event.aggregate_id}")


class SourceToolRestoredProjectionHandler(DomainEventHandler[SourceToolRestoredDomainEvent]):
    """Projects SourceToolRestoredDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[SourceToolDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: SourceToolRestoredDomainEvent) -> None:
        """Handle tool restored event - reactivates deprecated tool."""
        logger.debug(f"Projecting SourceToolRestoredDomainEvent: {event.aggregate_id}")

        existing = await self._repository.get_async(event.aggregate_id)
        if not existing:
            logger.warning(f"SourceTool {event.aggregate_id} not found for restored projection")
            return

        # Parse new definition
        definition = ToolDefinition.from_dict(event.new_definition) if event.new_definition else None

        if definition:
            existing.description = definition.description
            existing.input_schema = definition.input_schema
            existing.method = definition.execution_profile.method
            existing.path = definition.source_path
            existing.tags = definition.tags
            existing.execution_mode = definition.execution_profile.mode.value
            existing.required_audience = definition.execution_profile.required_audience
            existing.timeout_seconds = definition.execution_profile.timeout_seconds
            existing.definition = event.new_definition

        existing.status = "active"
        existing.is_enabled = True  # Restored tools are re-enabled
        existing.last_seen_at = event.restored_at
        existing.updated_at = event.restored_at

        await self._repository.update_async(existing)
        logger.info(f"Projected SourceTool restored: {event.aggregate_id}")


class LabelAddedToToolProjectionHandler(DomainEventHandler[LabelAddedToToolDomainEvent]):
    """Projects LabelAddedToToolDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[SourceToolDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: LabelAddedToToolDomainEvent) -> None:
        """Handle label added event - adds label_id to tool's label_ids list."""
        logger.debug(f"Projecting LabelAddedToToolDomainEvent: {event.aggregate_id}")

        existing = await self._repository.get_async(event.aggregate_id)
        if not existing:
            logger.warning(f"SourceTool {event.aggregate_id} not found for label added projection")
            return

        # Ensure label_ids list exists (for backwards compatibility)
        if not hasattr(existing, "label_ids") or existing.label_ids is None:
            existing.label_ids = []

        # Add label if not already present (idempotency)
        if event.label_id not in existing.label_ids:
            existing.label_ids.append(event.label_id)
            existing.updated_at = event.added_at
            await self._repository.update_async(existing)
            logger.info(f"Projected label {event.label_id} added to tool: {event.aggregate_id}")
        else:
            logger.debug(f"Label {event.label_id} already on tool {event.aggregate_id}, skipping")


class LabelRemovedFromToolProjectionHandler(DomainEventHandler[LabelRemovedFromToolDomainEvent]):
    """Projects LabelRemovedFromToolDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[SourceToolDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: LabelRemovedFromToolDomainEvent) -> None:
        """Handle label removed event - removes label_id from tool's label_ids list."""
        logger.debug(f"Projecting LabelRemovedFromToolDomainEvent: {event.aggregate_id}")

        existing = await self._repository.get_async(event.aggregate_id)
        if not existing:
            logger.warning(f"SourceTool {event.aggregate_id} not found for label removed projection")
            return

        # Ensure label_ids list exists
        if not hasattr(existing, "label_ids") or existing.label_ids is None:
            existing.label_ids = []
            return  # Nothing to remove

        # Remove label if present (idempotency)
        if event.label_id in existing.label_ids:
            existing.label_ids.remove(event.label_id)
            existing.updated_at = event.removed_at
            await self._repository.update_async(existing)
            logger.info(f"Projected label {event.label_id} removed from tool: {event.aggregate_id}")
        else:
            logger.debug(f"Label {event.label_id} not on tool {event.aggregate_id}, skipping")
