"""Domain event handlers package.

Contains projection handlers that sync the read model with the write model.
These handlers are automatically discovered by the Mediator.
"""

# UpstreamSource projection handlers (Phase 1)
from .source_projection_handlers import (InventoryIngestedProjectionHandler, SourceDeregisteredProjectionHandler, SourceDisabledProjectionHandler, SourceEnabledProjectionHandler,
                                         SourceHealthChangedProjectionHandler, SourceRegisteredProjectionHandler, SourceSyncFailedProjectionHandler)
# SourceTool projection handlers (Phase 1)
from .source_tool_projection_handlers import (SourceToolDefinitionUpdatedProjectionHandler, SourceToolDeprecatedProjectionHandler, SourceToolDisabledProjectionHandler,
                                              SourceToolDiscoveredProjectionHandler, SourceToolEnabledProjectionHandler, SourceToolRestoredProjectionHandler)
# Task projection handlers (existing)
from .task_projection_handlers import (TaskAssigneeUpdatedProjectionHandler, TaskCreatedProjectionHandler, TaskDepartmentUpdatedProjectionHandler, TaskDescriptionUpdatedProjectionHandler,
                                       TaskPriorityUpdatedProjectionHandler, TaskStatusUpdatedProjectionHandler, TaskTitleUpdatedProjectionHandler, TaskUpdatedProjectionHandler)
# ToolGroup projection handlers (Phase 3)
from .tool_group_projection_handlers import (ExplicitToolAddedProjectionHandler, ExplicitToolRemovedProjectionHandler, SelectorAddedProjectionHandler, SelectorRemovedProjectionHandler,
                                             ToolExcludedProjectionHandler, ToolGroupActivatedProjectionHandler, ToolGroupCreatedProjectionHandler, ToolGroupDeactivatedProjectionHandler,
                                             ToolGroupUpdatedProjectionHandler, ToolIncludedProjectionHandler)
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
]
