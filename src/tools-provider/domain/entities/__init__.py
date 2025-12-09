"""Domain entities package.

Contains all aggregate roots for the MCP Tools Provider domain.
"""

from .access_policy import AccessPolicy, AccessPolicyState
from .label import Label, LabelState
from .source_tool import SourceTool, SourceToolState
from .task import Task, TaskState
from .tool_group import ToolGroup, ToolGroupState
from .upstream_source import UpstreamSource, UpstreamSourceState

__all__ = [
    # Task aggregate (existing)
    "Task",
    "TaskState",
    # UpstreamSource aggregate (Phase 1)
    "UpstreamSource",
    "UpstreamSourceState",
    # SourceTool aggregate (Phase 1)
    "SourceTool",
    "SourceToolState",
    # ToolGroup aggregate (Phase 3)
    "ToolGroup",
    "ToolGroupState",
    # AccessPolicy aggregate (Phase 4)
    "AccessPolicy",
    "AccessPolicyState",
    # Label aggregate
    "Label",
    "LabelState",
]
