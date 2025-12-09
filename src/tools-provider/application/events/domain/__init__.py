"""Domain event handlers package.

Contains projection handlers that sync the read model with the write model.
These handlers are automatically discovered by the Mediator.
"""

# AccessPolicy projection handlers
from .access_policy_projection_handlers import (
    AccessPolicyActivatedProjectionHandler,
    AccessPolicyDeactivatedProjectionHandler,
    AccessPolicyDefinedProjectionHandler,
    AccessPolicyDeletedProjectionHandler,
    AccessPolicyGroupsUpdatedProjectionHandler,
    AccessPolicyMatchersUpdatedProjectionHandler,
    AccessPolicyPriorityUpdatedProjectionHandler,
    AccessPolicyUpdatedProjectionHandler,
)

# Admin SSE notification handlers (Admin UI real-time updates)
from .admin_sse_notification_handlers import (
    GroupCreatedNotificationHandler,
    GroupDeactivatedNotificationHandler,
    GroupUpdatedNotificationHandler,
    InventoryIngestedNotificationHandler,
    SourceDeregisteredNotificationHandler,
    SourceRegisteredNotificationHandler,
    ToolDisabledNotificationHandler,
    ToolEnabledNotificationHandler,
)

# Label projection handlers
from .label_projection_handlers import LabelCreatedProjectionHandler, LabelDeletedProjectionHandler, LabelUpdatedProjectionHandler

# UpstreamSource projection handlers
from .source_projection_handlers import (
    InventoryIngestedProjectionHandler,
    SourceDeregisteredProjectionHandler,
    SourceDisabledProjectionHandler,
    SourceEnabledProjectionHandler,
    SourceHealthChangedProjectionHandler,
    SourceRegisteredProjectionHandler,
    SourceSyncFailedProjectionHandler,
)

# SourceTool projection handlers
from .source_tool_projection_handlers import (
    LabelAddedToToolProjectionHandler,
    LabelRemovedFromToolProjectionHandler,
    SourceToolDefinitionUpdatedProjectionHandler,
    SourceToolDeprecatedProjectionHandler,
    SourceToolDisabledProjectionHandler,
    SourceToolDiscoveredProjectionHandler,
    SourceToolEnabledProjectionHandler,
    SourceToolRestoredProjectionHandler,
    SourceToolUpdatedProjectionHandler,
)

# Task projection handlers (existing)
from .task_projection_handlers import (
    TaskAssigneeUpdatedProjectionHandler,
    TaskCreatedProjectionHandler,
    TaskDepartmentUpdatedProjectionHandler,
    TaskDescriptionUpdatedProjectionHandler,
    TaskPriorityUpdatedProjectionHandler,
    TaskStatusUpdatedProjectionHandler,
    TaskTitleUpdatedProjectionHandler,
    TaskUpdatedProjectionHandler,
)

# ToolGroup projection handlers
from .tool_group_projection_handlers import (
    ExplicitToolAddedProjectionHandler,
    ExplicitToolRemovedProjectionHandler,
    SelectorAddedProjectionHandler,
    SelectorRemovedProjectionHandler,
    ToolExcludedProjectionHandler,
    ToolGroupActivatedProjectionHandler,
    ToolGroupCreatedProjectionHandler,
    ToolGroupDeactivatedProjectionHandler,
    ToolGroupUpdatedProjectionHandler,
    ToolIncludedProjectionHandler,
)

# User event handlers (existing)
from .user_auth_events_handler import UserLoggedInDomainEventHandler

__all__ = [
    # User handlers
    "UserLoggedInDomainEventHandler",
    # Task projection handlers
    "TaskCreatedProjectionHandler",
    "TaskTitleUpdatedProjectionHandler",
    "TaskDescriptionUpdatedProjectionHandler",
    "TaskStatusUpdatedProjectionHandler",
    "TaskPriorityUpdatedProjectionHandler",
    "TaskAssigneeUpdatedProjectionHandler",
    "TaskDepartmentUpdatedProjectionHandler",
    "TaskUpdatedProjectionHandler",
    # UpstreamSource projection handlers
    "SourceRegisteredProjectionHandler",
    "InventoryIngestedProjectionHandler",
    "SourceSyncFailedProjectionHandler",
    "SourceHealthChangedProjectionHandler",
    "SourceEnabledProjectionHandler",
    "SourceDisabledProjectionHandler",
    "SourceDeregisteredProjectionHandler",
    # SourceTool projection handlers
    "SourceToolDiscoveredProjectionHandler",
    "SourceToolEnabledProjectionHandler",
    "SourceToolDisabledProjectionHandler",
    "SourceToolDefinitionUpdatedProjectionHandler",
    "SourceToolDeprecatedProjectionHandler",
    "SourceToolRestoredProjectionHandler",
    "SourceToolUpdatedProjectionHandler",
    "LabelAddedToToolProjectionHandler",
    "LabelRemovedFromToolProjectionHandler",
    # ToolGroup projection handlers (Phase 3)
    "ExplicitToolAddedProjectionHandler",
    "ExplicitToolRemovedProjectionHandler",
    "SelectorAddedProjectionHandler",
    "SelectorRemovedProjectionHandler",
    "ToolExcludedProjectionHandler",
    "ToolGroupActivatedProjectionHandler",
    "ToolGroupCreatedProjectionHandler",
    "ToolGroupDeactivatedProjectionHandler",
    "ToolGroupUpdatedProjectionHandler",
    "ToolIncludedProjectionHandler",
    # AccessPolicy projection handlers
    "AccessPolicyDefinedProjectionHandler",
    "AccessPolicyUpdatedProjectionHandler",
    "AccessPolicyMatchersUpdatedProjectionHandler",
    "AccessPolicyGroupsUpdatedProjectionHandler",
    "AccessPolicyPriorityUpdatedProjectionHandler",
    "AccessPolicyActivatedProjectionHandler",
    "AccessPolicyDeactivatedProjectionHandler",
    "AccessPolicyDeletedProjectionHandler",
    # Label projection handlers
    "LabelCreatedProjectionHandler",
    "LabelUpdatedProjectionHandler",
    "LabelDeletedProjectionHandler",
    # Admin SSE notification handlers
    "GroupCreatedNotificationHandler",
    "GroupUpdatedNotificationHandler",
    "GroupDeactivatedNotificationHandler",
    "SourceRegisteredNotificationHandler",
    "SourceDeregisteredNotificationHandler",
    "InventoryIngestedNotificationHandler",
    "ToolEnabledNotificationHandler",
    "ToolDisabledNotificationHandler",
]
