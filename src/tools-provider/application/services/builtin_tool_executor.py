"""Built-in Tool Executor for local tool execution.

This module handles the execution of built-in utility tools that run
locally within the tools-provider, without proxying to external services.

The executor delegates to modular tool implementations in the builtin_tools submodule:
- fetch_tools: URL fetching, web search, Wikipedia
- utility_tools: DateTime, calculations, UUID, encoding, regex, JSON, text stats
- file_tools: File read/write, spreadsheet operations
- memory_tools: Key-value storage with Redis/file fallback
- code_tools: Python code execution in sandbox
- human_tools: Human-in-the-loop interactions

Security Considerations:
- URL fetching is restricted to HTTP/HTTPS
- Size limits prevent memory exhaustion
- Timeouts prevent hanging
- Math evaluation is sandboxed
- Python execution uses RestrictedPython
"""

import logging
from typing import Any

from opentelemetry import trace

from .builtin_tools import (
    BuiltinToolResult,
    UserContext,
    execute_ask_human,
    execute_calculate,
    execute_encode_decode,
    execute_fetch_url,
    execute_file_reader,
    execute_file_writer,
    execute_generate_uuid,
    execute_get_current_datetime,
    execute_json_transform,
    execute_memory_retrieve,
    execute_memory_store,
    execute_python,
    execute_regex_extract,
    execute_spreadsheet_read,
    execute_spreadsheet_write,
    execute_text_stats,
    execute_web_search,
    execute_wikipedia_query,
)

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


# Re-export for backward compatibility
__all__ = ["BuiltinToolExecutor", "BuiltinToolResult", "UserContext"]


class BuiltinToolExecutor:
    """Executes built-in utility tools locally.

    This executor handles tools registered with the BuiltinSourceAdapter.
    Tools are executed in-process without HTTP proxying.

    The executor delegates to modular tool implementations, passing user context
    for operations that require user isolation (memory, files).
    """

    def __init__(self) -> None:
        """Initialize the executor with tool mappings."""
        self._current_user_context: UserContext | None = None

        # Mapping of tool names to execution functions
        # Each function takes (arguments, user_context) and returns BuiltinToolResult
        self._executors: dict[str, Any] = {
            # Original tools
            "fetch_url": execute_fetch_url,
            "get_current_datetime": execute_get_current_datetime,
            "calculate": execute_calculate,
            "generate_uuid": execute_generate_uuid,
            "encode_decode": execute_encode_decode,
            "regex_extract": execute_regex_extract,
            "json_transform": execute_json_transform,
            "text_stats": execute_text_stats,
            # Web & Search tools
            "web_search": execute_web_search,
            # "browser_navigate": execute_browser_navigate,  # Commented out - requires Playwright (~500MB)
            "wikipedia_query": execute_wikipedia_query,
            # Code execution
            "execute_python": execute_python,
            # File tools
            "file_writer": execute_file_writer,
            "file_reader": execute_file_reader,
            "spreadsheet_read": execute_spreadsheet_read,
            "spreadsheet_write": execute_spreadsheet_write,
            # Memory tools
            "memory_store": execute_memory_store,
            "memory_retrieve": execute_memory_retrieve,
            # Human interaction
            "ask_human": execute_ask_human,
        }
        logger.info(f"BuiltinToolExecutor initialized with {len(self._executors)} tools")

    async def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        user_context: UserContext | None = None,
    ) -> BuiltinToolResult:
        """Execute a built-in tool.

        Args:
            tool_name: Name of the tool to execute
            arguments: Arguments for the tool
            user_context: Optional user context for scoping operations (memory, files)

        Returns:
            BuiltinToolResult with execution outcome
        """
        # Store user context for backward compatibility
        self._current_user_context = user_context

        with tracer.start_as_current_span(f"builtin_tool.{tool_name}") as span:
            span.set_attribute("tool.name", tool_name)
            if user_context:
                span.set_attribute("user.id", user_context.user_id)

            executor = self._executors.get(tool_name)
            if not executor:
                return BuiltinToolResult(
                    success=False,
                    error=f"Unknown built-in tool: {tool_name}",
                )

            try:
                # All tool functions take (arguments, user_context) signature
                return await executor(arguments, user_context)
            except Exception as e:
                logger.exception(f"Built-in tool execution failed: {tool_name}")
                span.set_attribute("tool.error", str(e))
                return BuiltinToolResult(
                    success=False,
                    error=f"Execution failed: {str(e)}",
                )

    def is_builtin_tool(self, tool_name: str) -> bool:
        """Check if a tool name is a built-in tool."""
        return tool_name in self._executors
