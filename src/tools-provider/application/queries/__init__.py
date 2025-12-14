"""Application queries package.

This package organizes queries into semantic submodules by entity:
- task/: Task retrieval queries
- source/: Source retrieval queries
- tool/: Tool search and sync status queries
- tool_group/: ToolGroup retrieval queries
- access_policy/: Access policy retrieval queries
- agent/: Agent tools manifest queries
- label/: Label retrieval queries

All queries are re-exported here for backward compatibility and
Neuroglia framework auto-discovery.
"""

# Task queries
# AccessPolicy queries
from .access_policy import (
    GetAccessPoliciesQuery,
    GetAccessPoliciesQueryHandler,
    GetAccessPolicyByIdQuery,
    GetAccessPolicyByIdQueryHandler,
)

# Agent queries
from .agent import (
    GetAgentToolsQuery,
    GetAgentToolsQueryHandler,
    ToolManifestEntry,
)

# Label queries
from .label import (
    GetLabelByIdQuery,
    GetLabelByIdQueryHandler,
    GetLabelsQuery,
    GetLabelsQueryHandler,
    GetLabelSummariesQuery,
    GetLabelSummariesQueryHandler,
)

# Source queries
from .source import (
    GetSourceByIdQuery,
    GetSourceByIdQueryHandler,
    GetSourcesQuery,
    GetSourcesQueryHandler,
)
from .task import (
    GetTaskByIdQuery,
    GetTaskByIdQueryHandler,
    GetTasksQuery,
    GetTasksQueryHandler,
)

# Tool queries
from .tool import (
    CheckToolSyncStatusQuery,
    CheckToolSyncStatusQueryHandler,
    GetSourceToolsQuery,
    GetSourceToolsQueryHandler,
    GetToolByIdQuery,
    GetToolByIdQueryHandler,
    GetToolSummariesQuery,
    GetToolSummariesQueryHandler,
    SearchToolsQuery,
    SearchToolsQueryHandler,
    ToolSyncStatus,
)

# ToolGroup queries
from .tool_group import (
    GetGroupToolsQuery,
    GetGroupToolsQueryHandler,
    GetToolGroupByIdQuery,
    GetToolGroupByIdQueryHandler,
    GetToolGroupsQuery,
    GetToolGroupsQueryHandler,
)

__all__ = [
    # Task queries
    "GetTaskByIdQuery",
    "GetTaskByIdQueryHandler",
    "GetTasksQuery",
    "GetTasksQueryHandler",
    # Source queries
    "GetSourcesQuery",
    "GetSourcesQueryHandler",
    "GetSourceByIdQuery",
    "GetSourceByIdQueryHandler",
    # Tool queries
    "GetSourceToolsQuery",
    "GetSourceToolsQueryHandler",
    "GetToolByIdQuery",
    "GetToolByIdQueryHandler",
    "SearchToolsQuery",
    "SearchToolsQueryHandler",
    "GetToolSummariesQuery",
    "GetToolSummariesQueryHandler",
    "CheckToolSyncStatusQuery",
    "CheckToolSyncStatusQueryHandler",
    "ToolSyncStatus",
    # ToolGroup queries
    "GetGroupToolsQuery",
    "GetGroupToolsQueryHandler",
    "GetToolGroupsQuery",
    "GetToolGroupsQueryHandler",
    "GetToolGroupByIdQuery",
    "GetToolGroupByIdQueryHandler",
    # AccessPolicy queries
    "GetAccessPoliciesQuery",
    "GetAccessPoliciesQueryHandler",
    "GetAccessPolicyByIdQuery",
    "GetAccessPolicyByIdQueryHandler",
    # Agent queries
    "GetAgentToolsQuery",
    "GetAgentToolsQueryHandler",
    "ToolManifestEntry",
    # Label queries
    "GetLabelsQuery",
    "GetLabelsQueryHandler",
    "GetLabelByIdQuery",
    "GetLabelByIdQueryHandler",
    "GetLabelSummariesQuery",
    "GetLabelSummariesQueryHandler",
]
