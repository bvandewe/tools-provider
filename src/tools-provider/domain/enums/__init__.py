"""Domain enumerations package.

This package contains all enumerations used across the domain layer,
organized into logical modules for maintainability.
"""

from .source import (
    AuthMode,
    ClaimOperator,
    ExecutionMode,
    HealthStatus,
    McpTransportType,
    PluginLifecycleMode,
    SourceType,
    ToolStatus,
)
from .task import TaskPriority, TaskStatus

__all__ = [
    # Task enums
    "TaskStatus",
    "TaskPriority",
    # Source/Tool enums
    "SourceType",
    "HealthStatus",
    "ToolStatus",
    "ExecutionMode",
    "ClaimOperator",
    "AuthMode",
    # MCP-specific enums
    "McpTransportType",
    "PluginLifecycleMode",
]
