"""Projection handlers for Label domain events.

These handlers project domain events to the MongoDB read model (LabelDto).
They subscribe to events from EventStoreDB and update the MongoDB projections.
"""

import logging

from domain.events.label import LabelCreatedDomainEvent, LabelDeletedDomainEvent, LabelUpdatedDomainEvent
from integration.models.label_dto import LabelDto
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.mediation import DomainEventHandler

logger = logging.getLogger(__name__)


class LabelCreatedProjectionHandler(DomainEventHandler[LabelCreatedDomainEvent]):
    """Projects LabelCreatedDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[LabelDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: LabelCreatedDomainEvent) -> None:
        """Handle label created event - creates new LabelDto."""
        logger.debug(f"Projecting LabelCreatedDomainEvent: {event.aggregate_id}")

        # Idempotency check
        existing = await self._repository.get_async(event.aggregate_id)
        if existing:
            logger.debug(f"Label {event.aggregate_id} already exists, skipping projection")
            return

        dto = LabelDto(
            id=event.aggregate_id,
            name=event.name,
            description=event.description,
            color=event.color,
            tool_count=0,
            created_at=event.created_at,
            updated_at=event.created_at,
            created_by=event.created_by,
            is_deleted=False,
        )

        await self._repository.add_async(dto)
        logger.info(f"✅ Projected LabelCreated to Read Model: {event.aggregate_id}")


class LabelUpdatedProjectionHandler(DomainEventHandler[LabelUpdatedDomainEvent]):
    """Projects LabelUpdatedDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[LabelDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: LabelUpdatedDomainEvent) -> None:
        """Handle label updated event - updates name/description/color."""
        logger.debug(f"Projecting LabelUpdatedDomainEvent: {event.aggregate_id}")

        label = await self._repository.get_async(event.aggregate_id)
        if label:
            if event.name is not None:
                label.name = event.name
            if event.description is not None:
                label.description = event.description
            if event.color is not None:
                label.color = event.color
            label.updated_at = event.updated_at

            await self._repository.update_async(label)
            logger.info(f"✅ Projected LabelUpdated to Read Model: {event.aggregate_id}")
        else:
            logger.warning(f"Label {event.aggregate_id} not found for update projection")


class LabelDeletedProjectionHandler(DomainEventHandler[LabelDeletedDomainEvent]):
    """Projects LabelDeletedDomainEvent to MongoDB Read Model.

    Performs soft delete by setting is_deleted=True.
    """

    def __init__(self, repository: Repository[LabelDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: LabelDeletedDomainEvent) -> None:
        """Handle label deleted event - soft deletes label."""
        logger.debug(f"Projecting LabelDeletedDomainEvent: {event.aggregate_id}")

        label = await self._repository.get_async(event.aggregate_id)
        if label:
            label.is_deleted = True
            label.updated_at = event.deleted_at

            await self._repository.update_async(label)
            logger.info(f"✅ Projected LabelDeleted (soft) to Read Model: {event.aggregate_id}")
        else:
            logger.warning(f"Label {event.aggregate_id} not found for deletion projection")
