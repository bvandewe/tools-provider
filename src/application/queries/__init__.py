"""Application queries package."""

# Task queries
# Source queries
from .get_source_tools_query import (GetSourceToolsQuery, GetSourceToolsQueryHandler, GetToolByIdQuery, GetToolByIdQueryHandler, GetToolSummariesQuery, GetToolSummariesQueryHandler, SearchToolsQuery,
                                     SearchToolsQueryHandler)
from .get_sources_query import GetSourceByIdQuery, GetSourceByIdQueryHandler, GetSourcesQuery, GetSourcesQueryHandler
from .get_task_by_id_query import GetTaskByIdQuery, GetTaskByIdQueryHandler
from .get_tasks_query import GetTasksQuery, GetTasksQueryHandler
from .get_tool_groups_query import GetToolGroupByIdQuery, GetToolGroupByIdQueryHandler, GetToolGroupsQuery, GetToolGroupsQueryHandler

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
    # Source tool queries
    "GetSourceToolsQuery",
    "GetSourceToolsQueryHandler",
    "GetToolByIdQuery",
    "GetToolByIdQueryHandler",
    "SearchToolsQuery",
    "SearchToolsQueryHandler",
    "GetToolSummariesQuery",
    "GetToolSummariesQueryHandler",
    # ToolGroup queries (Phase 3)
    "GetToolGroupsQuery",
    "GetToolGroupsQueryHandler",
    "GetToolGroupByIdQuery",
    "GetToolGroupByIdQueryHandler",
]
