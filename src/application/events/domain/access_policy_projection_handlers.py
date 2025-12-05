"""
Read Model Projection Handlers for AccessPolicy Aggregate.

These handlers listen to domain events streamed by the ReadModelReconciliator
and update the MongoDB read model accordingly.

The ReadModelReconciliator subscribes to EventStoreDB's category stream ($ce-tools_provider)
and publishes each event through the Mediator. These handlers receive those events
and project them to MongoDB, keeping the Read Model in sync with the Write Model.
"""

import logging

from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.mediation import DomainEventHandler

from domain.events.access_policy import (
    AccessPolicyActivatedDomainEvent,
    AccessPolicyDeactivatedDomainEvent,
    AccessPolicyDefinedDomainEvent,
    AccessPolicyDeletedDomainEvent,
    AccessPolicyGroupsUpdatedDomainEvent,
    AccessPolicyMatchersUpdatedDomainEvent,
    AccessPolicyPriorityUpdatedDomainEvent,
    AccessPolicyUpdatedDomainEvent,
)
from integration.models.access_policy_dto import AccessPolicyDto

logger = logging.getLogger(__name__)


class AccessPolicyDefinedProjectionHandler(DomainEventHandler[AccessPolicyDefinedDomainEvent]):
    """Projects AccessPolicyDefinedDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[AccessPolicyDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: AccessPolicyDefinedDomainEvent) -> None:
        """Create AccessPolicyDto in Read Model."""
        logger.info(f"📥 Projecting AccessPolicyDefined: {event.aggregate_id}")

        # Idempotency check - skip if already exists
        existing = await self._repository.get_async(event.aggregate_id)
        if existing:
            logger.info(f"⏭️ AccessPolicy already exists in Read Model, skipping: {event.aggregate_id}")
            return

        # Map domain event to DTO
        policy_dto = AccessPolicyDto(
            id=event.aggregate_id,
            name=event.name,
            description=event.description,
            claim_matchers=list(event.claim_matchers),
            allowed_group_ids=list(event.allowed_group_ids),
            priority=event.priority,
            is_active=True,
            created_at=event.defined_at,
            updated_at=event.defined_at,
            created_by=event.defined_by,
            matcher_count=len(event.claim_matchers),
            group_count=len(event.allowed_group_ids),
        )

        await self._repository.add_async(policy_dto)
        logger.info(f"✅ Projected AccessPolicyDefined to Read Model: {event.aggregate_id}")


class AccessPolicyUpdatedProjectionHandler(DomainEventHandler[AccessPolicyUpdatedDomainEvent]):
    """Projects AccessPolicyUpdatedDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[AccessPolicyDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: AccessPolicyUpdatedDomainEvent) -> None:
        """Update policy basic info in Read Model."""
        logger.info(f"📥 Projecting AccessPolicyUpdated: {event.aggregate_id}")

        policy = await self._repository.get_async(event.aggregate_id)
        if policy:
            if event.name is not None:
                policy.name = event.name
            if event.description is not None:
                policy.description = event.description
            policy.updated_at = event.updated_at
            await self._repository.update_async(policy)
            logger.info(f"✅ Projected AccessPolicyUpdated to Read Model: {event.aggregate_id}")
        else:
            logger.warning(f"⚠️ AccessPolicy not found in Read Model for update: {event.aggregate_id}")


class AccessPolicyMatchersUpdatedProjectionHandler(DomainEventHandler[AccessPolicyMatchersUpdatedDomainEvent]):
    """Projects AccessPolicyMatchersUpdatedDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[AccessPolicyDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: AccessPolicyMatchersUpdatedDomainEvent) -> None:
        """Update policy claim matchers in Read Model."""
        logger.info(f"📥 Projecting AccessPolicyMatchersUpdated: {event.aggregate_id}")

        policy = await self._repository.get_async(event.aggregate_id)
        if policy:
            policy.claim_matchers = list(event.claim_matchers)
            policy.matcher_count = len(event.claim_matchers)
            policy.updated_at = event.updated_at
            await self._repository.update_async(policy)
            logger.info(f"✅ Projected AccessPolicyMatchersUpdated to Read Model: {event.aggregate_id}")
        else:
            logger.warning(f"⚠️ AccessPolicy not found in Read Model for matchers update: {event.aggregate_id}")


class AccessPolicyGroupsUpdatedProjectionHandler(DomainEventHandler[AccessPolicyGroupsUpdatedDomainEvent]):
    """Projects AccessPolicyGroupsUpdatedDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[AccessPolicyDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: AccessPolicyGroupsUpdatedDomainEvent) -> None:
        """Update policy allowed groups in Read Model."""
        logger.info(f"📥 Projecting AccessPolicyGroupsUpdated: {event.aggregate_id}")

        policy = await self._repository.get_async(event.aggregate_id)
        if policy:
            policy.allowed_group_ids = list(event.allowed_group_ids)
            policy.group_count = len(event.allowed_group_ids)
            policy.updated_at = event.updated_at
            await self._repository.update_async(policy)
            logger.info(f"✅ Projected AccessPolicyGroupsUpdated to Read Model: {event.aggregate_id}")
        else:
            logger.warning(f"⚠️ AccessPolicy not found in Read Model for groups update: {event.aggregate_id}")


class AccessPolicyPriorityUpdatedProjectionHandler(DomainEventHandler[AccessPolicyPriorityUpdatedDomainEvent]):
    """Projects AccessPolicyPriorityUpdatedDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[AccessPolicyDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: AccessPolicyPriorityUpdatedDomainEvent) -> None:
        """Update policy priority in Read Model."""
        logger.info(f"📥 Projecting AccessPolicyPriorityUpdated: {event.aggregate_id}")

        policy = await self._repository.get_async(event.aggregate_id)
        if policy:
            policy.priority = event.new_priority
            policy.updated_at = event.updated_at
            await self._repository.update_async(policy)
            logger.info(f"✅ Projected AccessPolicyPriorityUpdated to Read Model: {event.aggregate_id}")
        else:
            logger.warning(f"⚠️ AccessPolicy not found in Read Model for priority update: {event.aggregate_id}")


class AccessPolicyActivatedProjectionHandler(DomainEventHandler[AccessPolicyActivatedDomainEvent]):
    """Projects AccessPolicyActivatedDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[AccessPolicyDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: AccessPolicyActivatedDomainEvent) -> None:
        """Activate policy in Read Model."""
        logger.info(f"📥 Projecting AccessPolicyActivated: {event.aggregate_id}")

        policy = await self._repository.get_async(event.aggregate_id)
        if policy:
            policy.is_active = True
            policy.updated_at = event.activated_at
            await self._repository.update_async(policy)
            logger.info(f"✅ Projected AccessPolicyActivated to Read Model: {event.aggregate_id}")
        else:
            logger.warning(f"⚠️ AccessPolicy not found in Read Model for activation: {event.aggregate_id}")


class AccessPolicyDeactivatedProjectionHandler(DomainEventHandler[AccessPolicyDeactivatedDomainEvent]):
    """Projects AccessPolicyDeactivatedDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[AccessPolicyDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: AccessPolicyDeactivatedDomainEvent) -> None:
        """Deactivate policy in Read Model."""
        logger.info(f"📥 Projecting AccessPolicyDeactivated: {event.aggregate_id}")

        policy = await self._repository.get_async(event.aggregate_id)
        if policy:
            policy.is_active = False
            policy.updated_at = event.deactivated_at
            await self._repository.update_async(policy)
            logger.info(f"✅ Projected AccessPolicyDeactivated to Read Model: {event.aggregate_id}")
        else:
            logger.warning(f"⚠️ AccessPolicy not found in Read Model for deactivation: {event.aggregate_id}")


class AccessPolicyDeletedProjectionHandler(DomainEventHandler[AccessPolicyDeletedDomainEvent]):
    """Projects AccessPolicyDeletedDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[AccessPolicyDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: AccessPolicyDeletedDomainEvent) -> None:
        """Delete policy from Read Model."""
        logger.info(f"📥 Projecting AccessPolicyDeleted: {event.aggregate_id}")

        policy = await self._repository.get_async(event.aggregate_id)
        if policy:
            await self._repository.remove_async(event.aggregate_id)
            logger.info(f"✅ Projected AccessPolicyDeleted - removed from Read Model: {event.aggregate_id}")
        else:
            logger.warning(f"⚠️ AccessPolicy not found in Read Model for deletion: {event.aggregate_id}")
