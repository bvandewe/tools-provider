"""Built-in Source Adapter for utility tools.

This adapter provides built-in utility tools that are executed locally
by the tools-provider, without proxying to external services.

Built-in tools are useful for:
- Fetching/downloading content from URLs
- Date/time operations
- Data transformations
- Text processing
- Basic calculations
- Code execution
- File read/write in the agent workspace
- Persistent memory storage/retrieval
- Human interaction

These tools follow the same authorization model as external tools:
- Registered as a source with policies
- Access controlled via JWT claims
- Full audit trail via event sourcing

Design Principles:
- Tools are defined in code but registered like any other source
- Execution happens locally (no HTTP proxy)
- Same security model as external tools
"""

import hashlib
import json
import logging

from domain.enums import ExecutionMode, SourceType
from domain.models import AuthConfig, ExecutionProfile, ToolDefinition

from .source_adapter import IngestionResult, SourceAdapter

logger = logging.getLogger(__name__)


# =============================================================================
# Built-in Tool Definitions
# =============================================================================


def _create_fetch_url_tool() -> ToolDefinition:
    """Create the fetch_url tool definition."""
    return ToolDefinition(
        name="fetch_url",
        description="""Fetch content from a URL. Downloads and reads files, web pages, or API responses.
Supports text content (HTML, JSON, plain text, CSV, Markdown) and returns the content as text.
For binary files (images, PDFs), returns metadata about the file.

Use cases:
- Reading generated reports or files from download links
- Fetching JSON data from APIs
- Reading web page content
- Downloading CSV or text files

Security: Only HTTP/HTTPS URLs allowed. Size limited to 10MB. Timeout: 30 seconds.""",
        input_schema={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to fetch content from. Must be http:// or https://",
                },
                "extract_text": {
                    "type": "boolean",
                    "description": "If true and content is HTML, extract plain text from the page. Default: true for HTML.",
                    "default": True,
                },
            },
            "required": ["url"],
        },
        execution_profile=ExecutionProfile(
            mode=ExecutionMode.SYNC_HTTP,
            method="POST",
            url_template="builtin://fetch_url",
            headers_template={},
            body_template=None,
            content_type="application/json",
        ),
        source_path="/builtin/fetch_url",
        tags=["utility", "web", "download"],
    )


def _create_get_current_datetime_tool() -> ToolDefinition:
    """Create the get_current_datetime tool definition."""
    return ToolDefinition(
        name="get_current_datetime",
        description="""Get the current date and time. Returns the current timestamp in various formats.

Use cases:
- Getting today's date for queries
- Calculating relative dates
- Timezone-aware datetime operations

Returns: Current datetime in ISO format, Unix timestamp, and human-readable format.""",
        input_schema={
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": "IANA timezone name (e.g., 'America/New_York', 'Europe/London', 'UTC'). Default: UTC",
                    "default": "UTC",
                },
                "format": {
                    "type": "string",
                    "description": "Output format: 'iso' (ISO 8601), 'unix' (timestamp), 'human' (readable), or 'all' (all formats). Default: 'all'",
                    "enum": ["iso", "unix", "human", "all"],
                    "default": "all",
                },
            },
            "required": [],
        },
        execution_profile=ExecutionProfile(
            mode=ExecutionMode.SYNC_HTTP,
            method="POST",
            url_template="builtin://get_current_datetime",
            headers_template={},
            body_template=None,
            content_type="application/json",
        ),
        source_path="/builtin/get_current_datetime",
        tags=["utility", "datetime"],
    )


def _create_calculate_tool() -> ToolDefinition:
    """Create the calculate tool definition."""
    return ToolDefinition(
        name="calculate",
        description="""Perform mathematical calculations safely. Evaluates mathematical expressions
with support for basic arithmetic, powers, roots, and common math functions.

Supported operations:
- Basic: +, -, *, /, // (floor div), % (modulo), ** (power)
- Functions: sqrt, abs, round, floor, ceil, sin, cos, tan, log, log10, exp
- Constants: pi, e

Examples:
- "2 + 2" → 4
- "sqrt(16) + 10" → 14.0
- "sin(pi/2)" → 1.0
- "round(3.14159, 2)" → 3.14

Security: Only mathematical expressions allowed, no code execution.""",
        input_schema={
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "The mathematical expression to evaluate",
                },
                "precision": {
                    "type": "integer",
                    "description": "Number of decimal places for the result. Default: 10",
                    "default": 10,
                },
            },
            "required": ["expression"],
        },
        execution_profile=ExecutionProfile(
            mode=ExecutionMode.SYNC_HTTP,
            method="POST",
            url_template="builtin://calculate",
            headers_template={},
            body_template=None,
            content_type="application/json",
        ),
        source_path="/builtin/calculate",
        tags=["utility", "math"],
    )


def _create_generate_uuid_tool() -> ToolDefinition:
    """Create the generate_uuid tool definition."""
    return ToolDefinition(
        name="generate_uuid",
        description="""Generate a universally unique identifier (UUID).

Use cases:
- Creating unique IDs for new records
- Generating correlation IDs
- Creating random identifiers

Returns: A new UUID v4 (random) string.""",
        input_schema={
            "type": "object",
            "properties": {
                "count": {
                    "type": "integer",
                    "description": "Number of UUIDs to generate (1-100). Default: 1",
                    "minimum": 1,
                    "maximum": 100,
                    "default": 1,
                },
                "format": {
                    "type": "string",
                    "description": "Output format: 'standard' (with hyphens), 'hex' (no hyphens), 'urn' (urn:uuid: prefix). Default: 'standard'",
                    "enum": ["standard", "hex", "urn"],
                    "default": "standard",
                },
            },
            "required": [],
        },
        execution_profile=ExecutionProfile(
            mode=ExecutionMode.SYNC_HTTP,
            method="POST",
            url_template="builtin://generate_uuid",
            headers_template={},
            body_template=None,
            content_type="application/json",
        ),
        source_path="/builtin/generate_uuid",
        tags=["utility", "id"],
    )


def _create_encode_decode_tool() -> ToolDefinition:
    """Create the encode_decode tool definition."""
    return ToolDefinition(
        name="encode_decode",
        description="""Encode or decode text using various encoding schemes.

Supported encodings:
- base64: Base64 encoding/decoding
- url: URL encoding/decoding (percent-encoding)
- html: HTML entity encoding/decoding
- hex: Hexadecimal encoding/decoding

Use cases:
- Encoding data for API requests
- Decoding received data
- Escaping special characters""",
        input_schema={
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to encode or decode",
                },
                "encoding": {
                    "type": "string",
                    "description": "The encoding scheme to use",
                    "enum": ["base64", "url", "html", "hex"],
                },
                "operation": {
                    "type": "string",
                    "description": "Whether to encode or decode",
                    "enum": ["encode", "decode"],
                },
            },
            "required": ["text", "encoding", "operation"],
        },
        execution_profile=ExecutionProfile(
            mode=ExecutionMode.SYNC_HTTP,
            method="POST",
            url_template="builtin://encode_decode",
            headers_template={},
            body_template=None,
            content_type="application/json",
        ),
        source_path="/builtin/encode_decode",
        tags=["utility", "encoding"],
    )


def _create_regex_extract_tool() -> ToolDefinition:
    """Create the regex_extract tool definition."""
    return ToolDefinition(
        name="regex_extract",
        description="""Extract data from text using regular expressions.

Use cases:
- Extracting emails, URLs, phone numbers from text
- Parsing structured data from unstructured text
- Finding patterns in log files or documents

Returns all matches with their captured groups.""",
        input_schema={
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to search in",
                },
                "pattern": {
                    "type": "string",
                    "description": "The regular expression pattern",
                },
                "flags": {
                    "type": "string",
                    "description": "Regex flags: 'i' (ignore case), 'm' (multiline), 's' (dotall). Combine as needed, e.g., 'im'",
                    "default": "",
                },
                "max_matches": {
                    "type": "integer",
                    "description": "Maximum number of matches to return (1-1000). Default: 100",
                    "minimum": 1,
                    "maximum": 1000,
                    "default": 100,
                },
            },
            "required": ["text", "pattern"],
        },
        execution_profile=ExecutionProfile(
            mode=ExecutionMode.SYNC_HTTP,
            method="POST",
            url_template="builtin://regex_extract",
            headers_template={},
            body_template=None,
            content_type="application/json",
        ),
        source_path="/builtin/regex_extract",
        tags=["utility", "text", "regex"],
    )


def _create_json_transform_tool() -> ToolDefinition:
    """Create the json_transform tool definition."""
    return ToolDefinition(
        name="json_transform",
        description="""Transform and query JSON data using JSONPath expressions.

Use cases:
- Extracting specific fields from complex JSON
- Filtering JSON arrays
- Restructuring JSON data

Supports standard JSONPath expressions like $.store.book[*].author""",
        input_schema={
            "type": "object",
            "properties": {
                "data": {
                    "description": "The JSON data to transform (object, array, or JSON string)",
                    "anyOf": [
                        {"type": "object"},
                        {"type": "array", "items": {}},
                        {"type": "string"},
                    ],
                },
                "path": {
                    "type": "string",
                    "description": "JSONPath expression to apply (e.g., '$.users[*].name')",
                },
            },
            "required": ["data", "path"],
        },
        execution_profile=ExecutionProfile(
            mode=ExecutionMode.SYNC_HTTP,
            method="POST",
            url_template="builtin://json_transform",
            headers_template={},
            body_template=None,
            content_type="application/json",
        ),
        source_path="/builtin/json_transform",
        tags=["utility", "json", "data"],
    )


def _create_text_stats_tool() -> ToolDefinition:
    """Create the text_stats tool definition."""
    return ToolDefinition(
        name="text_stats",
        description="""Analyze text and return statistics.

Returns:
- Character count (with and without spaces)
- Word count
- Sentence count
- Paragraph count
- Average word length
- Reading time estimate
- Most common words

Use cases:
- Document analysis
- Content length validation
- Readability assessment""",
        input_schema={
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to analyze",
                },
                "include_word_frequency": {
                    "type": "boolean",
                    "description": "Include top 10 most common words. Default: false",
                    "default": False,
                },
            },
            "required": ["text"],
        },
        execution_profile=ExecutionProfile(
            mode=ExecutionMode.SYNC_HTTP,
            method="POST",
            url_template="builtin://text_stats",
            headers_template={},
            body_template=None,
            content_type="application/json",
        ),
        source_path="/builtin/text_stats",
        tags=["utility", "text", "analysis"],
    )


# =============================================================================
# Web & Search Tools
# =============================================================================


def _create_web_search_tool() -> ToolDefinition:
    """Create the web_search tool definition."""
    return ToolDefinition(
        name="web_search",
        description="""Search the web using DuckDuckGo. Returns a list of search results with titles, URLs, and snippets.

Use cases:
- Finding current information on topics
- Researching facts or news
- Finding relevant websites or documentation

Returns up to 10 results per query. For more detailed content, use fetch_url on the result URLs.""",
        input_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return (1-10, default: 5)",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 10,
                },
                "region": {
                    "type": "string",
                    "description": "Region for results (e.g., 'us-en', 'uk-en', 'de-de'). Default: 'wt-wt' (no region)",
                    "default": "wt-wt",
                },
            },
            "required": ["query"],
        },
        execution_profile=ExecutionProfile(
            mode=ExecutionMode.SYNC_HTTP,
            method="POST",
            url_template="builtin://web_search",
            headers_template={},
            body_template=None,
            content_type="application/json",
        ),
        source_path="/builtin/web_search",
        tags=["utility", "web", "search"],
    )


def _create_browser_navigate_tool() -> ToolDefinition:
    """Create the browser_navigate tool definition."""
    return ToolDefinition(
        name="browser_navigate",
        description="""Navigate to a URL using a headless browser and return the fully rendered page content.
Unlike fetch_url, this executes JavaScript and waits for dynamic content to load.

Use cases:
- Scraping JavaScript-rendered pages (SPAs, React apps)
- Getting content that requires JS execution
- Extracting data from dynamic web applications

Note: Slower than fetch_url. Use fetch_url for static pages.""",
        input_schema={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to navigate to. Must be http:// or https://",
                },
                "wait_for": {
                    "type": "string",
                    "description": "CSS selector to wait for before capturing content (optional)",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Maximum time to wait in seconds (default: 30, max: 60)",
                    "default": 30,
                    "maximum": 60,
                },
                "extract_text": {
                    "type": "boolean",
                    "description": "If true, extract plain text only. If false, return HTML. Default: true",
                    "default": True,
                },
            },
            "required": ["url"],
        },
        execution_profile=ExecutionProfile(
            mode=ExecutionMode.SYNC_HTTP,
            method="POST",
            url_template="builtin://browser_navigate",
            headers_template={},
            body_template=None,
            content_type="application/json",
        ),
        source_path="/builtin/browser_navigate",
        tags=["utility", "web", "browser", "scraping"],
    )


def _create_wikipedia_query_tool() -> ToolDefinition:
    """Create the wikipedia_query tool definition."""
    return ToolDefinition(
        name="wikipedia_query",
        description="""Query Wikipedia for factual information. Returns article summaries and key facts.

Use cases:
- Getting factual summaries on topics
- Quick lookups of people, places, events
- Reliable encyclopedic information

Returns the article summary, categories, and links to related topics.""",
        input_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The topic or search term to look up",
                },
                "language": {
                    "type": "string",
                    "description": "Wikipedia language code (default: 'en')",
                    "default": "en",
                },
                "sentences": {
                    "type": "integer",
                    "description": "Number of sentences in summary (1-10, default: 5)",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 10,
                },
            },
            "required": ["query"],
        },
        execution_profile=ExecutionProfile(
            mode=ExecutionMode.SYNC_HTTP,
            method="POST",
            url_template="builtin://wikipedia_query",
            headers_template={},
            body_template=None,
            content_type="application/json",
        ),
        source_path="/builtin/wikipedia_query",
        tags=["utility", "knowledge", "wikipedia"],
    )


# =============================================================================
# Code Execution Tools
# =============================================================================


def _create_execute_python_tool() -> ToolDefinition:
    """Create the execute_python tool definition."""
    return ToolDefinition(
        name="execute_python",
        description="""Execute Python code in a secure sandbox. Returns stdout, stderr, and any returned value.

Capabilities:
- Standard library modules (math, json, datetime, re, collections, itertools, etc.)
- Data processing (calculations, transformations, parsing)
- No network access, no file system access, no subprocess

Limitations:
- 30 second timeout
- 100MB memory limit
- No external packages (no numpy, pandas, etc.)
- Cannot import os, sys, subprocess, socket, etc.

Use for: Complex calculations, data transformations, parsing, algorithms.""",
        input_schema={
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute. Use print() for output or return a value from a function.",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Maximum execution time in seconds (default: 30, max: 30)",
                    "default": 30,
                    "maximum": 30,
                },
            },
            "required": ["code"],
        },
        execution_profile=ExecutionProfile(
            mode=ExecutionMode.SYNC_HTTP,
            method="POST",
            url_template="builtin://execute_python",
            headers_template={},
            body_template=None,
            content_type="application/json",
        ),
        source_path="/builtin/execute_python",
        tags=["utility", "code", "python", "execution"],
    )


# =============================================================================
# File Tools
# =============================================================================


def _create_file_writer_tool() -> ToolDefinition:
    """Create the file_writer tool definition."""
    return ToolDefinition(
        name="file_writer",
        description="""Write content to a file in the agent's workspace. Creates deliverables like reports, code files, or data exports.

The file is stored in a secure workspace associated with the current session.
Files can be downloaded by the user or used by subsequent tool calls.

Supported formats: .txt, .md, .json, .csv, .py, .js, .html, .css, .xml, .yaml

Security: Files are sandboxed per-session. Maximum file size: 5MB.""",
        input_schema={
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Name of the file to create (e.g., 'report.md', 'data.json')",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file",
                },
                "mode": {
                    "type": "string",
                    "description": "Write mode: 'overwrite' (default) or 'append'",
                    "enum": ["overwrite", "append"],
                    "default": "overwrite",
                },
            },
            "required": ["filename", "content"],
        },
        execution_profile=ExecutionProfile(
            mode=ExecutionMode.SYNC_HTTP,
            method="POST",
            url_template="builtin://file_writer",
            headers_template={},
            body_template=None,
            content_type="application/json",
        ),
        source_path="/builtin/file_writer",
        tags=["utility", "file", "write"],
    )


def _create_file_reader_tool() -> ToolDefinition:
    """Create the file_reader tool definition."""
    return ToolDefinition(
        name="file_reader",
        description="""Read content from a file in the agent's workspace. Access files created by file_writer or uploaded by the user.

Returns the file content as text. For binary files, returns base64-encoded content.

Security: Can only access files in the current session's workspace.""",
        input_schema={
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Name of the file to read",
                },
                "encoding": {
                    "type": "string",
                    "description": "Text encoding (default: 'utf-8')",
                    "default": "utf-8",
                },
            },
            "required": ["filename"],
        },
        execution_profile=ExecutionProfile(
            mode=ExecutionMode.SYNC_HTTP,
            method="POST",
            url_template="builtin://file_reader",
            headers_template={},
            body_template=None,
            content_type="application/json",
        ),
        source_path="/builtin/file_reader",
        tags=["utility", "file", "read"],
    )


# =============================================================================
# Spreadsheet Tools
# =============================================================================


def _create_spreadsheet_read_tool() -> ToolDefinition:
    """Create the spreadsheet_read tool definition."""
    return ToolDefinition(
        name="spreadsheet_read",
        description="""Read and analyze Excel (.xlsx) spreadsheets. Parses the file and returns structured data.

Use cases:
- Reading generated reports downloaded via fetch_url
- Analyzing Excel data (summaries, statistics)
- Extracting specific sheets, rows, or columns
- Converting spreadsheet data to other formats

Returns sheet names, headers, row data, and optional summary statistics.
Supports large files by limiting rows returned (use offset/limit for pagination).""",
        input_schema={
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "The filename of the spreadsheet in the agent workspace",
                },
                "sheet_name": {
                    "type": "string",
                    "description": "Name of the sheet to read. If not provided, reads the first sheet.",
                },
                "include_stats": {
                    "type": "boolean",
                    "description": "Include summary statistics (row count, column types, min/max values). Default: true",
                    "default": True,
                },
                "max_rows": {
                    "type": "integer",
                    "description": "Maximum rows to return (default: 100, max: 1000). Use for large files.",
                    "default": 100,
                    "maximum": 1000,
                },
                "offset": {
                    "type": "integer",
                    "description": "Row offset for pagination (0-based). Default: 0",
                    "default": 0,
                },
                "columns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of column names to include. If not provided, returns all columns.",
                },
            },
            "required": ["filename"],
        },
        execution_profile=ExecutionProfile(
            mode=ExecutionMode.SYNC_HTTP,
            method="POST",
            url_template="builtin://spreadsheet_read",
            headers_template={},
            body_template=None,
            content_type="application/json",
        ),
        source_path="/builtin/spreadsheet_read",
        tags=["utility", "file", "spreadsheet", "excel"],
    )


def _create_spreadsheet_write_tool() -> ToolDefinition:
    """Create the spreadsheet_write tool definition."""
    return ToolDefinition(
        name="spreadsheet_write",
        description="""Create or modify Excel (.xlsx) spreadsheets.

Use cases:
- Creating new spreadsheets from analyzed data
- Adding sheets to existing workbooks
- Appending rows to existing data
- Generating reports with multiple sheets

Operations:
- 'create': Create new workbook (overwrites if exists)
- 'add_sheet': Add a new sheet to existing workbook
- 'append_rows': Add rows to an existing sheet
- 'update_cell': Update specific cell(s)

Returns the filename and path of the created/modified file.""",
        input_schema={
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "The filename for the spreadsheet (will be saved in agent workspace)",
                },
                "operation": {
                    "type": "string",
                    "enum": ["create", "add_sheet", "append_rows", "update_cell"],
                    "description": "The operation to perform. Default: 'create'",
                    "default": "create",
                },
                "sheet_name": {
                    "type": "string",
                    "description": "Name of the sheet. Required for all operations. Default: 'Sheet1'",
                    "default": "Sheet1",
                },
                "headers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Column headers (for 'create' and 'add_sheet' operations)",
                },
                "data": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {},
                    },
                    "description": "Row data as array of arrays. Each inner array is a row.",
                },
                "cell_updates": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "cell": {"type": "string", "description": "Cell reference (e.g., 'A1', 'B2')"},
                            "value": {"description": "Value to set in the cell"},
                        },
                        "required": ["cell", "value"],
                    },
                    "description": "For 'update_cell' operation: list of cell updates",
                },
            },
            "required": ["filename"],
        },
        execution_profile=ExecutionProfile(
            mode=ExecutionMode.SYNC_HTTP,
            method="POST",
            url_template="builtin://spreadsheet_write",
            headers_template={},
            body_template=None,
            content_type="application/json",
        ),
        source_path="/builtin/spreadsheet_write",
        tags=["utility", "file", "spreadsheet", "excel"],
    )


# =============================================================================
# Memory Tools
# =============================================================================


def _create_memory_store_tool() -> ToolDefinition:
    """Create the memory_store tool definition."""
    return ToolDefinition(
        name="memory_store",
        description="""Store a key-value pair in persistent memory. Use for remembering facts, preferences, or context across conversations.

Examples:
- User preferences: "preferred_language" -> "Python"
- Learned facts: "user_timezone" -> "America/New_York"
- Task context: "current_project" -> "MCP Tools Provider"

Memory persists across sessions for the same user.""",
        input_schema={
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "The key to store (use descriptive snake_case names)",
                },
                "value": {
                    "type": "string",
                    "description": "The value to store (will be stored as string)",
                },
                "ttl_days": {
                    "type": "integer",
                    "description": "Time-to-live in days (default: 30, max: 365). Set to 0 for no expiration.",
                    "default": 30,
                    "maximum": 365,
                },
            },
            "required": ["key", "value"],
        },
        execution_profile=ExecutionProfile(
            mode=ExecutionMode.SYNC_HTTP,
            method="POST",
            url_template="builtin://memory_store",
            headers_template={},
            body_template=None,
            content_type="application/json",
        ),
        source_path="/builtin/memory_store",
        tags=["utility", "memory", "storage"],
    )


def _create_memory_retrieve_tool() -> ToolDefinition:
    """Create the memory_retrieve tool definition."""
    return ToolDefinition(
        name="memory_retrieve",
        description="""Retrieve a value from persistent memory by key, or list all stored keys.

Use to recall previously stored facts, preferences, or context.""",
        input_schema={
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "The key to retrieve. If omitted, returns all stored keys.",
                },
                "default": {
                    "type": "string",
                    "description": "Default value if key not found (optional)",
                },
            },
            "required": [],
        },
        execution_profile=ExecutionProfile(
            mode=ExecutionMode.SYNC_HTTP,
            method="POST",
            url_template="builtin://memory_retrieve",
            headers_template={},
            body_template=None,
            content_type="application/json",
        ),
        source_path="/builtin/memory_retrieve",
        tags=["utility", "memory", "retrieval"],
    )


# =============================================================================
# Human Interaction Tools
# =============================================================================


def _create_ask_human_tool() -> ToolDefinition:
    """Create the ask_human tool definition."""
    return ToolDefinition(
        name="ask_human",
        description="""Pause execution and explicitly request input or clarification from the user.

Use when:
- You need to make a decision but lack sufficient information
- Multiple valid options exist and user preference matters
- Confirmation is needed before a significant action
- You want to present options for the user to choose from

This signals to the system that user input is required before proceeding.""",
        input_schema={
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The question or prompt for the user",
                },
                "context": {
                    "type": "string",
                    "description": "Additional context to help the user respond (optional)",
                },
                "options": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of suggested options/choices for the user",
                },
                "input_type": {
                    "type": "string",
                    "description": "Expected input type: 'text' (default), 'choice', 'confirmation'",
                    "enum": ["text", "choice", "confirmation"],
                    "default": "text",
                },
            },
            "required": ["question"],
        },
        execution_profile=ExecutionProfile(
            mode=ExecutionMode.SYNC_HTTP,
            method="POST",
            url_template="builtin://ask_human",
            headers_template={},
            body_template=None,
            content_type="application/json",
        ),
        source_path="/builtin/ask_human",
        tags=["utility", "human", "interaction"],
    )


# Registry of all built-in tools
def get_builtin_tools() -> list[ToolDefinition]:
    """Get all built-in tool definitions."""
    return [
        # Original tools
        _create_fetch_url_tool(),
        _create_get_current_datetime_tool(),
        _create_calculate_tool(),
        _create_generate_uuid_tool(),
        _create_encode_decode_tool(),
        _create_regex_extract_tool(),
        _create_json_transform_tool(),
        _create_text_stats_tool(),
        # Web & Search tools
        _create_web_search_tool(),
        # _create_browser_navigate_tool(),  # Commented out - requires Playwright (~500MB)
        _create_wikipedia_query_tool(),
        # Code execution
        _create_execute_python_tool(),
        # File tools
        _create_file_writer_tool(),
        _create_file_reader_tool(),
        _create_spreadsheet_read_tool(),
        _create_spreadsheet_write_tool(),
        # Memory tools
        _create_memory_store_tool(),
        _create_memory_retrieve_tool(),
        # Human interaction
        _create_ask_human_tool(),
    ]


# =============================================================================
# Built-in Source Adapter
# =============================================================================


class BuiltinSourceAdapter(SourceAdapter):
    """Adapter for built-in utility tools.

    Unlike other adapters, this one doesn't fetch from external URLs.
    Instead, it provides a fixed set of utility tools that are executed
    locally by the tools-provider.

    The URL parameter is ignored - built-in tools are always the same.
    """

    # Source ID for the built-in tools source (constant)
    BUILTIN_SOURCE_ID = "builtin-utility-tools"
    BUILTIN_SOURCE_NAME = "Utility Tools"
    BUILTIN_SOURCE_DESCRIPTION = "Built-in utility tools for common operations"
    BUILTIN_SOURCE_URL = "builtin://utility-tools"

    @property
    def source_type(self) -> SourceType:
        """Return the type of source this adapter handles."""
        return SourceType.BUILTIN

    async def fetch_and_normalize(
        self,
        url: str,
        auth_config: AuthConfig | None = None,
        default_audience: str | None = None,
    ) -> IngestionResult:
        """Return the built-in tool definitions.

        For built-in sources, the URL is ignored. The tools are defined
        in code and always returned the same way.

        Args:
            url: Ignored for built-in sources
            auth_config: Ignored for built-in sources
            default_audience: Ignored for built-in sources

        Returns:
            IngestionResult with built-in tool definitions
        """
        logger.info("Loading built-in utility tools")

        try:
            tools = get_builtin_tools()

            # Compute hash based on tool definitions for change detection
            tools_json = json.dumps([t.to_dict() for t in tools], sort_keys=True)
            inventory_hash = hashlib.sha256(tools_json.encode()).hexdigest()

            logger.info(f"Loaded {len(tools)} built-in tools")

            return IngestionResult(
                tools=tools,
                inventory_hash=inventory_hash,
                success=True,
                source_version="1.0.0",
                warnings=[],
            )
        except Exception as e:
            logger.exception("Failed to load built-in tools")
            return IngestionResult.failure(f"Failed to load built-in tools: {e}")

    async def validate_url(self, url: str, auth_config: AuthConfig | None = None) -> bool:
        """Validate URL for built-in source.

        Always returns True for built-in sources since they don't
        depend on external URLs.
        """
        return url.startswith("builtin://") or url == self.BUILTIN_SOURCE_URL


def is_builtin_source(source_id: str) -> bool:
    """Check if a source ID is the built-in tools source."""
    return source_id == BuiltinSourceAdapter.BUILTIN_SOURCE_ID


def is_builtin_tool_url(url: str) -> bool:
    """Check if a URL is a built-in tool execution URL."""
    return url.startswith("builtin://")
