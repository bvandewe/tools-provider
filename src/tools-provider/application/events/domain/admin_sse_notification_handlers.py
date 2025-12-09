"""Admin SSE notification handlers for domain events.

These handlers listen to domain events and broadcast notifications
to connected admin dashboard clients via SSE.

This keeps the SSE notification logic separate from the projection
handlers, following the Single Responsibility Principle.
"""

import logging

from api.controllers.admin_sse_controller import broadcast_group_event, broadcast_policy_event, broadcast_source_event, broadcast_tool_event
from domain.events.access_policy import (
    AccessPolicyActivatedDomainEvent,
    AccessPolicyDeactivatedDomainEvent,
    AccessPolicyDefinedDomainEvent,
    AccessPolicyDeletedDomainEvent,
    AccessPolicyUpdatedDomainEvent,
)
from domain.events.source_tool import SourceToolDeletedDomainEvent, SourceToolDeprecatedDomainEvent, SourceToolDisabledDomainEvent, SourceToolDiscoveredDomainEvent, SourceToolEnabledDomainEvent
from domain.events.tool_group import ToolGroupActivatedDomainEvent, ToolGroupCreatedDomainEvent, ToolGroupDeactivatedDomainEvent, ToolGroupUpdatedDomainEvent
from domain.events.upstream_source import InventoryIngestedDomainEvent, SourceDeregisteredDomainEvent, SourceHealthChangedDomainEvent, SourceRegisteredDomainEvent
from neuroglia.mediation import DomainEventHandler

logger = logging.getLogger(__name__)


# ============================================================================
# SOURCE EVENT HANDLERS
# ============================================================================


class SourceRegisteredNotificationHandler(DomainEventHandler[SourceRegisteredDomainEvent]):
    """Broadcasts source registration events to admin SSE clients."""

    async def handle_async(self, event: SourceRegisteredDomainEvent) -> None:
        """Broadcast source registered notification."""
        logger.debug(f"📡 Broadcasting source_registered: {event.aggregate_id}")
        await broadcast_source_event(
            action="registered",
            source_id=event.aggregate_id,
            source_name=event.name,
            details={
                "url": event.url,
                "source_type": str(event.source_type),
                "created_by": event.created_by,
            },
        )


class SourceDeregisteredNotificationHandler(DomainEventHandler[SourceDeregisteredDomainEvent]):
    """Broadcasts source deregistration (deletion) events to admin SSE clients."""

    async def handle_async(self, event: SourceDeregisteredDomainEvent) -> None:
        """Broadcast source deleted notification."""
        logger.debug(f"📡 Broadcasting source_deleted: {event.aggregate_id}")
        await broadcast_source_event(
            action="deleted",
            source_id=event.aggregate_id,
            source_name="",  # Name not available in delete event
            details={
                "deregistered_at": event.deregistered_at.isoformat() if event.deregistered_at else None,
            },
        )


class InventoryIngestedNotificationHandler(DomainEventHandler[InventoryIngestedDomainEvent]):
    """Broadcasts inventory ingestion events to admin SSE clients."""

    async def handle_async(self, event: InventoryIngestedDomainEvent) -> None:
        """Broadcast inventory updated notification."""
        logger.debug(f"📡 Broadcasting source_inventory_updated: {event.aggregate_id}")
        await broadcast_source_event(
            action="inventory_updated",
            source_id=event.aggregate_id,
            source_name="",  # Name not in this event
            details={
                "tool_count": event.tool_count,
                "ingested_at": event.ingested_at.isoformat() if event.ingested_at else None,
            },
        )


class SourceHealthChangedNotificationHandler(DomainEventHandler[SourceHealthChangedDomainEvent]):
    """Broadcasts source health change events to admin SSE clients."""

    async def handle_async(self, event: SourceHealthChangedDomainEvent) -> None:
        """Broadcast source health changed notification."""
        logger.debug(f"📡 Broadcasting source_health_changed: {event.aggregate_id}")
        await broadcast_source_event(
            action="health_changed",
            source_id=event.aggregate_id,
            source_name="",
            details={
                "old_status": str(event.old_status) if event.old_status else None,
                "new_status": str(event.new_status) if event.new_status else None,
            },
        )


# ============================================================================
# TOOL EVENT HANDLERS
# ============================================================================


class ToolDiscoveredNotificationHandler(DomainEventHandler[SourceToolDiscoveredDomainEvent]):
    """Broadcasts tool discovery events to admin SSE clients."""

    async def handle_async(self, event: SourceToolDiscoveredDomainEvent) -> None:
        """Broadcast tool discovered notification."""
        logger.debug(f"📡 Broadcasting tool_discovered: {event.aggregate_id}")
        await broadcast_tool_event(
            action="discovered",
            tool_id=event.aggregate_id,
            tool_name=event.tool_name,
            details={
                "source_id": event.source_id,
                "operation_id": event.operation_id,
            },
        )


class ToolEnabledNotificationHandler(DomainEventHandler[SourceToolEnabledDomainEvent]):
    """Broadcasts tool enabled events to admin SSE clients."""

    async def handle_async(self, event: SourceToolEnabledDomainEvent) -> None:
        """Broadcast tool enabled notification."""
        logger.debug(f"📡 Broadcasting tool_enabled: {event.aggregate_id}")
        await broadcast_tool_event(
            action="enabled",
            tool_id=event.aggregate_id,
            tool_name="",  # Name not in this event
            details={
                "enabled_by": event.enabled_by,
                "enabled_at": event.enabled_at.isoformat() if event.enabled_at else None,
            },
        )


class ToolDisabledNotificationHandler(DomainEventHandler[SourceToolDisabledDomainEvent]):
    """Broadcasts tool disabled events to admin SSE clients."""

    async def handle_async(self, event: SourceToolDisabledDomainEvent) -> None:
        """Broadcast tool disabled notification."""
        logger.debug(f"📡 Broadcasting tool_disabled: {event.aggregate_id}")
        await broadcast_tool_event(
            action="disabled",
            tool_id=event.aggregate_id,
            tool_name="",
            details={
                "disabled_by": event.disabled_by,
                "reason": event.reason,
                "disabled_at": event.disabled_at.isoformat() if event.disabled_at else None,
            },
        )


class ToolDeprecatedNotificationHandler(DomainEventHandler[SourceToolDeprecatedDomainEvent]):
    """Broadcasts tool deprecated events to admin SSE clients."""

    async def handle_async(self, event: SourceToolDeprecatedDomainEvent) -> None:
        """Broadcast tool deprecated notification."""
        logger.debug(f"📡 Broadcasting tool_deprecated: {event.aggregate_id}")
        await broadcast_tool_event(
            action="deprecated",
            tool_id=event.aggregate_id,
            tool_name="",
            details={
                "deprecated_at": event.deprecated_at.isoformat() if event.deprecated_at else None,
            },
        )


class ToolDeletedNotificationHandler(DomainEventHandler[SourceToolDeletedDomainEvent]):
    """Broadcasts tool deleted events to admin SSE clients."""

    async def handle_async(self, event: SourceToolDeletedDomainEvent) -> None:
        """Broadcast tool deleted notification."""
        logger.debug(f"📡 Broadcasting tool_deleted: {event.aggregate_id}")
        await broadcast_tool_event(
            action="deleted",
            tool_id=event.aggregate_id,
            tool_name="",
            details={
                "deleted_at": event.deleted_at.isoformat() if event.deleted_at else None,
                "deleted_by": event.deleted_by,
                "reason": event.reason,
            },
        )


# ============================================================================
# TOOL GROUP EVENT HANDLERS
# ============================================================================


class GroupCreatedNotificationHandler(DomainEventHandler[ToolGroupCreatedDomainEvent]):
    """Broadcasts tool group created events to admin SSE clients."""

    async def handle_async(self, event: ToolGroupCreatedDomainEvent) -> None:
        """Broadcast group created notification."""
        logger.debug(f"📡 Broadcasting group_created: {event.aggregate_id}")
        await broadcast_group_event(
            action="created",
            group_id=event.aggregate_id,
            group_name=event.name,
            details={
                "description": event.description,
                "created_by": event.created_by,
            },
        )


class GroupUpdatedNotificationHandler(DomainEventHandler[ToolGroupUpdatedDomainEvent]):
    """Broadcasts tool group updated events to admin SSE clients."""

    async def handle_async(self, event: ToolGroupUpdatedDomainEvent) -> None:
        """Broadcast group updated notification."""
        logger.debug(f"📡 Broadcasting group_updated: {event.aggregate_id}")
        await broadcast_group_event(
            action="updated",
            group_id=event.aggregate_id,
            group_name=event.name or "",
            details={
                "description": event.description,
            },
        )


class GroupActivatedNotificationHandler(DomainEventHandler[ToolGroupActivatedDomainEvent]):
    """Broadcasts tool group activated events to admin SSE clients."""

    async def handle_async(self, event: ToolGroupActivatedDomainEvent) -> None:
        """Broadcast group activated notification."""
        logger.debug(f"📡 Broadcasting group_activated: {event.aggregate_id}")
        await broadcast_group_event(
            action="activated",
            group_id=event.aggregate_id,
            group_name="",
            details={
                "activated_by": event.activated_by,
                "activated_at": event.activated_at.isoformat() if event.activated_at else None,
            },
        )


class GroupDeactivatedNotificationHandler(DomainEventHandler[ToolGroupDeactivatedDomainEvent]):
    """Broadcasts tool group deactivated events to admin SSE clients."""

    async def handle_async(self, event: ToolGroupDeactivatedDomainEvent) -> None:
        """Broadcast group deactivated notification."""
        logger.debug(f"📡 Broadcasting group_deactivated: {event.aggregate_id}")
        await broadcast_group_event(
            action="deactivated",
            group_id=event.aggregate_id,
            group_name="",
            details={
                "deactivated_by": event.deactivated_by,
                "reason": event.reason,
                "deactivated_at": event.deactivated_at.isoformat() if event.deactivated_at else None,
            },
        )


# ============================================================================
# ACCESS POLICY EVENT HANDLERS
# ============================================================================


class PolicyDefinedNotificationHandler(DomainEventHandler[AccessPolicyDefinedDomainEvent]):
    """Broadcasts access policy defined events to admin SSE clients."""

    async def handle_async(self, event: AccessPolicyDefinedDomainEvent) -> None:
        """Broadcast policy defined notification."""
        logger.debug(f"📡 Broadcasting policy_defined: {event.aggregate_id}")
        await broadcast_policy_event(
            action="defined",
            policy_id=event.aggregate_id,
            policy_name=event.name,
            details={
                "description": event.description,
                "matcher_count": len(event.claim_matchers) if event.claim_matchers else 0,
                "group_count": len(event.allowed_group_ids) if event.allowed_group_ids else 0,
                "defined_by": event.defined_by,
            },
        )


class PolicyUpdatedNotificationHandler(DomainEventHandler[AccessPolicyUpdatedDomainEvent]):
    """Broadcasts access policy updated events to admin SSE clients."""

    async def handle_async(self, event: AccessPolicyUpdatedDomainEvent) -> None:
        """Broadcast policy updated notification."""
        logger.debug(f"📡 Broadcasting policy_updated: {event.aggregate_id}")
        await broadcast_policy_event(
            action="updated",
            policy_id=event.aggregate_id,
            policy_name=event.name or "",
            details={
                "description": event.description,
            },
        )


class PolicyActivatedNotificationHandler(DomainEventHandler[AccessPolicyActivatedDomainEvent]):
    """Broadcasts access policy activated events to admin SSE clients."""

    async def handle_async(self, event: AccessPolicyActivatedDomainEvent) -> None:
        """Broadcast policy activated notification."""
        logger.debug(f"📡 Broadcasting policy_activated: {event.aggregate_id}")
        await broadcast_policy_event(
            action="activated",
            policy_id=event.aggregate_id,
            policy_name="",
            details={
                "activated_by": event.activated_by,
                "activated_at": event.activated_at.isoformat() if event.activated_at else None,
            },
        )


class PolicyDeactivatedNotificationHandler(DomainEventHandler[AccessPolicyDeactivatedDomainEvent]):
    """Broadcasts access policy deactivated events to admin SSE clients."""

    async def handle_async(self, event: AccessPolicyDeactivatedDomainEvent) -> None:
        """Broadcast policy deactivated notification."""
        logger.debug(f"📡 Broadcasting policy_deactivated: {event.aggregate_id}")
        await broadcast_policy_event(
            action="deactivated",
            policy_id=event.aggregate_id,
            policy_name="",
            details={
                "deactivated_by": event.deactivated_by,
                "reason": event.reason,
                "deactivated_at": event.deactivated_at.isoformat() if event.deactivated_at else None,
            },
        )


class PolicyDeletedNotificationHandler(DomainEventHandler[AccessPolicyDeletedDomainEvent]):
    """Broadcasts access policy deleted events to admin SSE clients."""

    async def handle_async(self, event: AccessPolicyDeletedDomainEvent) -> None:
        """Broadcast policy deleted notification."""
        logger.debug(f"📡 Broadcasting policy_deleted: {event.aggregate_id}")
        await broadcast_policy_event(
            action="deleted",
            policy_id=event.aggregate_id,
            policy_name="",
            details={
                "deleted_at": event.deleted_at.isoformat() if event.deleted_at else None,
                "deleted_by": event.deleted_by,
            },
        )
