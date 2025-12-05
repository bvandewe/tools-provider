"""Domain events package.

Contains all domain events for the MCP Tools Provider aggregates.
"""

# SourceTool events (Phase 1)
from .source_tool import (
    SourceToolDefinitionUpdatedDomainEvent,
    SourceToolDeletedDomainEvent,
    SourceToolDeprecatedDomainEvent,
    SourceToolDisabledDomainEvent,
    SourceToolDiscoveredDomainEvent,
    SourceToolEnabledDomainEvent,
    SourceToolRestoredDomainEvent,
)

# Task events (existing)
from .task import (
    TaskAssigneeUpdatedDomainEvent,
    TaskCreatedDomainEvent,
    TaskDeletedDomainEvent,
    TaskDepartmentUpdatedDomainEvent,
    TaskDescriptionUpdatedDomainEvent,
    TaskPriorityUpdatedDomainEvent,
    TaskStatusUpdatedDomainEvent,
    TaskTitleUpdatedDomainEvent,
    TaskUpdatedDomainEvent,
)

# UpstreamSource events (Phase 1)
from .upstream_source import (
    InventoryIngestedDomainEvent,
    SourceAuthUpdatedDomainEvent,
    SourceDeregisteredDomainEvent,
    SourceDisabledDomainEvent,
    SourceEnabledDomainEvent,
    SourceHealthChangedDomainEvent,
    SourceRegisteredDomainEvent,
    SourceSyncFailedDomainEvent,
    SourceSyncStartedDomainEvent,
)

# User events (existing)
from .user import UserLoggedInDomainEvent

__all__ = [
    # Task events
    "TaskAssigneeUpdatedDomainEvent",
    "TaskCreatedDomainEvent",
    "TaskDeletedDomainEvent",
    "TaskDepartmentUpdatedDomainEvent",
    "TaskDescriptionUpdatedDomainEvent",
    "TaskPriorityUpdatedDomainEvent",
    "TaskStatusUpdatedDomainEvent",
    "TaskTitleUpdatedDomainEvent",
    "TaskUpdatedDomainEvent",
    # User events
    "UserLoggedInDomainEvent",
    # UpstreamSource events
    "InventoryIngestedDomainEvent",
    "SourceAuthUpdatedDomainEvent",
    "SourceDeregisteredDomainEvent",
    "SourceDisabledDomainEvent",
    "SourceEnabledDomainEvent",
    "SourceHealthChangedDomainEvent",
    "SourceRegisteredDomainEvent",
    "SourceSyncFailedDomainEvent",
    "SourceSyncStartedDomainEvent",
    # SourceTool events
    "SourceToolDefinitionUpdatedDomainEvent",
    "SourceToolDeletedDomainEvent",
    "SourceToolDeprecatedDomainEvent",
    "SourceToolDisabledDomainEvent",
    "SourceToolDiscoveredDomainEvent",
    "SourceToolEnabledDomainEvent",
    "SourceToolRestoredDomainEvent",
]
