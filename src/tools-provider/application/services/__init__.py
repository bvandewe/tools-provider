"""Application services package.

Contains domain services and adapters for external integrations.
"""

from .builtin_source_adapter import BuiltinSourceAdapter, get_builtin_tools, is_builtin_source, is_builtin_tool_url
from .builtin_tool_executor import BuiltinToolExecutor, BuiltinToolResult, UserContext
from .logger import configure_logging
from .mcp_source_adapter import McpSourceAdapter
from .mcp_tool_executor import McpExecutionResult, McpToolExecutor
from .openapi_source_adapter import OpenAPISourceAdapter
from .source_adapter import IngestionResult, SourceAdapter, get_adapter_for_type
from .tool_executor import ToolExecutionError, ToolExecutionResult, ToolExecutor

__all__ = [
    "configure_logging",
    # Source adapters
    "SourceAdapter",
    "IngestionResult",
    "OpenAPISourceAdapter",
    "BuiltinSourceAdapter",
    "McpSourceAdapter",
    "get_adapter_for_type",
    "get_builtin_tools",
    "is_builtin_source",
    "is_builtin_tool_url",
    # Tool executors
    "ToolExecutor",
    "ToolExecutionResult",
    "ToolExecutionError",
    "BuiltinToolExecutor",
    "BuiltinToolResult",
    "UserContext",
    "McpToolExecutor",
    "McpExecutionResult",
]
