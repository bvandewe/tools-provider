"""Projection handlers for ToolGroup domain events.

These handlers project domain events to the MongoDB read model (ToolGroupDto).
They subscribe to events from EventStoreDB and update the MongoDB projections.

Following the existing projection handler patterns:
- DomainEventHandler[TEvent] base class
- Idempotency checks before updates
- Handles creation, updates, and soft deletes
"""

import logging

from domain.events.tool_group import (
    ExplicitToolAddedDomainEvent,
    ExplicitToolRemovedDomainEvent,
    SelectorAddedDomainEvent,
    SelectorRemovedDomainEvent,
    ToolExcludedDomainEvent,
    ToolGroupActivatedDomainEvent,
    ToolGroupCreatedDomainEvent,
    ToolGroupDeactivatedDomainEvent,
    ToolGroupDeletedDomainEvent,
    ToolGroupUpdatedDomainEvent,
    ToolIncludedDomainEvent,
)
from integration.models.tool_group_dto import ToolGroupDto
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.mediation import DomainEventHandler

logger = logging.getLogger(__name__)


class ToolGroupCreatedProjectionHandler(DomainEventHandler[ToolGroupCreatedDomainEvent]):
    """Projects ToolGroupCreatedDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[ToolGroupDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: ToolGroupCreatedDomainEvent) -> None:
        """Handle tool group created event - creates new ToolGroupDto."""
        logger.debug(f"Projecting ToolGroupCreatedDomainEvent: {event.aggregate_id}")

        # Idempotency check
        existing = await self._repository.get_async(event.aggregate_id)
        if existing:
            logger.debug(f"ToolGroup {event.aggregate_id} already exists, skipping projection")
            return

        dto = ToolGroupDto(
            id=event.aggregate_id,
            name=event.name,
            description=event.description,
            selector_count=0,
            explicit_tool_count=0,
            excluded_tool_count=0,
            selectors=[],
            explicit_tool_ids=[],
            excluded_tool_ids=[],
            is_active=True,
            created_at=event.created_at,
            updated_at=event.created_at,
            created_by=event.created_by,
        )

        await self._repository.add_async(dto)
        logger.info(f"✅ Projected ToolGroupCreated to Read Model: {event.aggregate_id}")


class ToolGroupUpdatedProjectionHandler(DomainEventHandler[ToolGroupUpdatedDomainEvent]):
    """Projects ToolGroupUpdatedDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[ToolGroupDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: ToolGroupUpdatedDomainEvent) -> None:
        """Handle tool group updated event - updates name/description."""
        logger.debug(f"Projecting ToolGroupUpdatedDomainEvent: {event.aggregate_id}")

        group = await self._repository.get_async(event.aggregate_id)
        if group:
            if event.name is not None:
                group.name = event.name
            if event.description is not None:
                group.description = event.description
            group.updated_at = event.updated_at

            await self._repository.update_async(group)
            logger.info(f"✅ Projected ToolGroupUpdated to Read Model: {event.aggregate_id}")
        else:
            logger.warning(f"⚠️ ToolGroup not found in Read Model for update: {event.aggregate_id}")


class SelectorAddedProjectionHandler(DomainEventHandler[SelectorAddedDomainEvent]):
    """Projects SelectorAddedDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[ToolGroupDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: SelectorAddedDomainEvent) -> None:
        """Handle selector added event - adds selector to group."""
        logger.debug(f"Projecting SelectorAddedDomainEvent: {event.aggregate_id}")

        group = await self._repository.get_async(event.aggregate_id)
        if group:
            # Check if selector already exists (idempotency)
            selector_id = event.selector.get("id")
            if not any(s.get("id") == selector_id for s in group.selectors):
                group.selectors.append(event.selector)
                group.selector_count = len(group.selectors)
                group.updated_at = event.added_at

                await self._repository.update_async(group)
                logger.info(f"✅ Projected SelectorAdded to Read Model: {event.aggregate_id}")
            else:
                logger.debug(f"Selector {selector_id} already exists in group {event.aggregate_id}")
        else:
            logger.warning(f"⚠️ ToolGroup not found in Read Model for selector add: {event.aggregate_id}")


class SelectorRemovedProjectionHandler(DomainEventHandler[SelectorRemovedDomainEvent]):
    """Projects SelectorRemovedDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[ToolGroupDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: SelectorRemovedDomainEvent) -> None:
        """Handle selector removed event - removes selector from group."""
        logger.debug(f"Projecting SelectorRemovedDomainEvent: {event.aggregate_id}")

        group = await self._repository.get_async(event.aggregate_id)
        if group:
            group.selectors = [s for s in group.selectors if s.get("id") != event.selector_id]
            group.selector_count = len(group.selectors)
            group.updated_at = event.removed_at

            await self._repository.update_async(group)
            logger.info(f"✅ Projected SelectorRemoved to Read Model: {event.aggregate_id}")
        else:
            logger.warning(f"⚠️ ToolGroup not found in Read Model for selector remove: {event.aggregate_id}")


class ExplicitToolAddedProjectionHandler(DomainEventHandler[ExplicitToolAddedDomainEvent]):
    """Projects ExplicitToolAddedDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[ToolGroupDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: ExplicitToolAddedDomainEvent) -> None:
        """Handle explicit tool added event - adds tool to explicit list."""
        logger.debug(f"Projecting ExplicitToolAddedDomainEvent: {event.aggregate_id}")

        group = await self._repository.get_async(event.aggregate_id)
        if group:
            # Check if tool already exists (idempotency)
            if not any(m.get("tool_id") == event.tool_id for m in group.explicit_tool_ids):
                membership = {
                    "tool_id": event.tool_id,
                    "added_at": event.added_at.isoformat(),
                    "added_by": event.added_by,
                }
                group.explicit_tool_ids.append(membership)
                group.explicit_tool_count = len(group.explicit_tool_ids)
                group.updated_at = event.added_at

                await self._repository.update_async(group)
                logger.info(f"✅ Projected ExplicitToolAdded to Read Model: {event.aggregate_id}")
            else:
                logger.debug(f"Tool {event.tool_id} already exists in group {event.aggregate_id}")
        else:
            logger.warning(f"⚠️ ToolGroup not found in Read Model for tool add: {event.aggregate_id}")


class ExplicitToolRemovedProjectionHandler(DomainEventHandler[ExplicitToolRemovedDomainEvent]):
    """Projects ExplicitToolRemovedDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[ToolGroupDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: ExplicitToolRemovedDomainEvent) -> None:
        """Handle explicit tool removed event - removes tool from explicit list."""
        logger.debug(f"Projecting ExplicitToolRemovedDomainEvent: {event.aggregate_id}")

        group = await self._repository.get_async(event.aggregate_id)
        if group:
            group.explicit_tool_ids = [m for m in group.explicit_tool_ids if m.get("tool_id") != event.tool_id]
            group.explicit_tool_count = len(group.explicit_tool_ids)
            group.updated_at = event.removed_at

            await self._repository.update_async(group)
            logger.info(f"✅ Projected ExplicitToolRemoved to Read Model: {event.aggregate_id}")
        else:
            logger.warning(f"⚠️ ToolGroup not found in Read Model for tool remove: {event.aggregate_id}")


class ToolExcludedProjectionHandler(DomainEventHandler[ToolExcludedDomainEvent]):
    """Projects ToolExcludedDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[ToolGroupDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: ToolExcludedDomainEvent) -> None:
        """Handle tool excluded event - adds tool to exclusion list."""
        logger.debug(f"Projecting ToolExcludedDomainEvent: {event.aggregate_id}")

        group = await self._repository.get_async(event.aggregate_id)
        if group:
            # Check if tool already excluded (idempotency)
            if not any(e.get("tool_id") == event.tool_id for e in group.excluded_tool_ids):
                exclusion = {
                    "tool_id": event.tool_id,
                    "excluded_at": event.excluded_at.isoformat(),
                    "excluded_by": event.excluded_by,
                    "reason": event.reason,
                }
                group.excluded_tool_ids.append(exclusion)
                group.excluded_tool_count = len(group.excluded_tool_ids)
                group.updated_at = event.excluded_at

                await self._repository.update_async(group)
                logger.info(f"✅ Projected ToolExcluded to Read Model: {event.aggregate_id}")
            else:
                logger.debug(f"Tool {event.tool_id} already excluded from group {event.aggregate_id}")
        else:
            logger.warning(f"⚠️ ToolGroup not found in Read Model for tool exclude: {event.aggregate_id}")


class ToolIncludedProjectionHandler(DomainEventHandler[ToolIncludedDomainEvent]):
    """Projects ToolIncludedDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[ToolGroupDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: ToolIncludedDomainEvent) -> None:
        """Handle tool included event - removes tool from exclusion list."""
        logger.debug(f"Projecting ToolIncludedDomainEvent: {event.aggregate_id}")

        group = await self._repository.get_async(event.aggregate_id)
        if group:
            group.excluded_tool_ids = [e for e in group.excluded_tool_ids if e.get("tool_id") != event.tool_id]
            group.excluded_tool_count = len(group.excluded_tool_ids)
            group.updated_at = event.included_at

            await self._repository.update_async(group)
            logger.info(f"✅ Projected ToolIncluded to Read Model: {event.aggregate_id}")
        else:
            logger.warning(f"⚠️ ToolGroup not found in Read Model for tool include: {event.aggregate_id}")


class ToolGroupActivatedProjectionHandler(DomainEventHandler[ToolGroupActivatedDomainEvent]):
    """Projects ToolGroupActivatedDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[ToolGroupDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: ToolGroupActivatedDomainEvent) -> None:
        """Handle tool group activated event - sets is_active to True."""
        logger.debug(f"Projecting ToolGroupActivatedDomainEvent: {event.aggregate_id}")

        group = await self._repository.get_async(event.aggregate_id)
        if group:
            group.is_active = True
            group.updated_at = event.activated_at

            await self._repository.update_async(group)
            logger.info(f"✅ Projected ToolGroupActivated to Read Model: {event.aggregate_id}")
        else:
            logger.warning(f"⚠️ ToolGroup not found in Read Model for activation: {event.aggregate_id}")


class ToolGroupDeactivatedProjectionHandler(DomainEventHandler[ToolGroupDeactivatedDomainEvent]):
    """Projects ToolGroupDeactivatedDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[ToolGroupDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: ToolGroupDeactivatedDomainEvent) -> None:
        """Handle tool group deactivated event - sets is_active to False."""
        logger.debug(f"Projecting ToolGroupDeactivatedDomainEvent: {event.aggregate_id}")

        group = await self._repository.get_async(event.aggregate_id)
        if group:
            group.is_active = False
            group.updated_at = event.deactivated_at

            await self._repository.update_async(group)
            logger.info(f"✅ Projected ToolGroupDeactivated to Read Model: {event.aggregate_id}")
        else:
            logger.warning(f"⚠️ ToolGroup not found in Read Model for deactivation: {event.aggregate_id}")


class ToolGroupDeletedProjectionHandler(DomainEventHandler[ToolGroupDeletedDomainEvent]):
    """Projects ToolGroupDeletedDomainEvent to MongoDB Read Model.

    Removes the group from the read model entirely (hard delete).
    """

    def __init__(self, repository: Repository[ToolGroupDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: ToolGroupDeletedDomainEvent) -> None:
        """Handle tool group deleted event - removes from read model."""
        logger.debug(f"Projecting ToolGroupDeletedDomainEvent: {event.aggregate_id}")

        group = await self._repository.get_async(event.aggregate_id)
        if group:
            await self._repository.remove_async(event.aggregate_id)
            logger.info(f"✅ Projected ToolGroupDeleted (removed) from Read Model: {event.aggregate_id}")
        else:
            logger.debug(f"ToolGroup {event.aggregate_id} not found in Read Model for deletion (already removed)")
