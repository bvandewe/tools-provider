"""Domain events package.

Contains all domain events for the MCP Tools Provider aggregates.
"""

# AccessPolicy events (Phase 4)
from .access_policy import (
    AccessPolicyActivatedDomainEvent,
    AccessPolicyDeactivatedDomainEvent,
    AccessPolicyDefinedDomainEvent,
    AccessPolicyDeletedDomainEvent,
    AccessPolicyGroupsUpdatedDomainEvent,
    AccessPolicyMatchersUpdatedDomainEvent,
    AccessPolicyPriorityUpdatedDomainEvent,
    AccessPolicyUpdatedDomainEvent,
)

# CircuitBreaker events (Infrastructure)
from .circuit_breaker import CircuitBreakerClosedDomainEvent, CircuitBreakerHalfOpenedDomainEvent, CircuitBreakerOpenedDomainEvent, CircuitBreakerTransitionReason

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

# ToolGroup events (Phase 3)
from .tool_group import (
    ExplicitToolAddedDomainEvent,
    ExplicitToolRemovedDomainEvent,
    SelectorAddedDomainEvent,
    SelectorRemovedDomainEvent,
    ToolExcludedDomainEvent,
    ToolGroupActivatedDomainEvent,
    ToolGroupCreatedDomainEvent,
    ToolGroupDeactivatedDomainEvent,
    ToolGroupUpdatedDomainEvent,
    ToolIncludedDomainEvent,
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
    SourceUpdatedDomainEvent,
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
    "SourceUpdatedDomainEvent",
    # SourceTool events
    "SourceToolDefinitionUpdatedDomainEvent",
    "SourceToolDeletedDomainEvent",
    "SourceToolDeprecatedDomainEvent",
    "SourceToolDisabledDomainEvent",
    "SourceToolDiscoveredDomainEvent",
    "SourceToolEnabledDomainEvent",
    "SourceToolRestoredDomainEvent",
    # ToolGroup events (Phase 3)
    "ExplicitToolAddedDomainEvent",
    "ExplicitToolRemovedDomainEvent",
    "SelectorAddedDomainEvent",
    "SelectorRemovedDomainEvent",
    "ToolExcludedDomainEvent",
    "ToolGroupActivatedDomainEvent",
    "ToolGroupCreatedDomainEvent",
    "ToolGroupDeactivatedDomainEvent",
    "ToolGroupUpdatedDomainEvent",
    "ToolIncludedDomainEvent",
    # AccessPolicy events (Phase 4)
    "AccessPolicyActivatedDomainEvent",
    "AccessPolicyDeactivatedDomainEvent",
    "AccessPolicyDefinedDomainEvent",
    "AccessPolicyDeletedDomainEvent",
    "AccessPolicyGroupsUpdatedDomainEvent",
    "AccessPolicyMatchersUpdatedDomainEvent",
    "AccessPolicyPriorityUpdatedDomainEvent",
    "AccessPolicyUpdatedDomainEvent",
    # CircuitBreaker events (Infrastructure)
    "CircuitBreakerClosedDomainEvent",
    "CircuitBreakerHalfOpenedDomainEvent",
    "CircuitBreakerOpenedDomainEvent",
    "CircuitBreakerTransitionReason",
]
