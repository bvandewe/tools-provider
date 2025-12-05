"""Domain entities package.

Contains all aggregate roots for the MCP Tools Provider domain.
"""

from .source_tool import SourceTool, SourceToolState
from .task import Task, TaskState
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
]
