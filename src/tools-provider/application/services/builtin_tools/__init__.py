"""Built-in tools submodule.

This module provides modular implementations of built-in tools organized by category:
- base: Shared types (BuiltinToolResult, UserContext) and utilities
- fetch_tools: URL fetching, web search, Wikipedia
- utility_tools: DateTime, calculations, UUID, encoding, regex, JSON, text stats
- file_tools: File read/write, spreadsheet operations
- memory_tools: Key-value storage with Redis/file fallback
- code_tools: Python code execution in sandbox
- human_tools: Human-in-the-loop interactions

All tools are re-exported here for convenient access.
"""

# Base types (required by all tools)
from .base import (
    FETCH_TIMEOUT,
    MAX_CONTENT_SIZE,
    BuiltinToolResult,
    UserContext,
    cleanup_old_files,
    extract_filename,
    get_workspace_dir,
    is_json_content,
    is_text_content,
    sanitize_filename,
)

# Code execution tools
from .code_tools import execute_python

# Fetch and web tools
from .fetch_tools import (
    execute_browser_navigate,
    execute_fetch_url,
    execute_web_search,
    execute_wikipedia_query,
)

# File and spreadsheet tools
from .file_tools import (
    execute_file_reader,
    execute_file_writer,
    execute_spreadsheet_read,
    execute_spreadsheet_write,
)

# Human interaction tools
from .human_tools import execute_ask_human

# Memory tools
from .memory_tools import execute_memory_retrieve, execute_memory_store

# Utility tools
from .utility_tools import (
    execute_calculate,
    execute_encode_decode,
    execute_generate_uuid,
    execute_get_current_datetime,
    execute_json_transform,
    execute_regex_extract,
    execute_text_stats,
)

__all__ = [
    # Base types
    "BuiltinToolResult",
    "UserContext",
    "FETCH_TIMEOUT",
    "MAX_CONTENT_SIZE",
    "get_workspace_dir",
    "cleanup_old_files",
    "is_text_content",
    "is_json_content",
    "extract_filename",
    "sanitize_filename",
    # Fetch tools
    "execute_fetch_url",
    "execute_web_search",
    "execute_wikipedia_query",
    "execute_browser_navigate",
    # Utility tools
    "execute_get_current_datetime",
    "execute_calculate",
    "execute_generate_uuid",
    "execute_encode_decode",
    "execute_regex_extract",
    "execute_json_transform",
    "execute_text_stats",
    # File tools
    "execute_file_writer",
    "execute_file_reader",
    "execute_spreadsheet_read",
    "execute_spreadsheet_write",
    # Memory tools
    "execute_memory_store",
    "execute_memory_retrieve",
    # Code tools
    "execute_python",
    # Human tools
    "execute_ask_human",
]
