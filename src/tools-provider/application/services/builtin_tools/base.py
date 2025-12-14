"""Base types and utilities for built-in tools.

This module provides shared infrastructure for all built-in tool implementations:
- Result types (BuiltinToolResult)
- User context for scoped operations
- Configuration constants
- Common helper functions
"""

import logging
import os
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol
from urllib.parse import urlparse

from opentelemetry import trace

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


# =============================================================================
# Configuration
# =============================================================================

# Maximum content size to fetch (10MB)
MAX_CONTENT_SIZE = 10 * 1024 * 1024

# Request timeout for fetch_url
FETCH_TIMEOUT = 30.0

# Workspace directory for file operations
WORKSPACE_BASE_DIR = "/tmp/tools-provider-workspace"  # nosec B108 - controlled temp directory for workspace files

# Maximum file age in workspace (24 hours)
MAX_FILE_AGE_SECONDS = 86400


# =============================================================================
# Result Type
# =============================================================================


@dataclass
class BuiltinToolResult:
    """Result of executing a built-in tool.

    Attributes:
        success: Whether execution succeeded
        result: Result data (on success)
        error: Error message (on failure)
        metadata: Additional execution metadata
    """

    success: bool
    result: Any = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class UserContext:
    """User context for scoping built-in tool operations.

    This ensures memory and file operations are isolated per user.

    Attributes:
        user_id: Unique user identifier (from JWT 'sub' claim)
        username: Human-readable username (optional, for logging)
    """

    user_id: str
    username: str | None = None


# =============================================================================
# Tool Protocol
# =============================================================================


class BuiltinTool(Protocol):
    """Protocol for built-in tool implementations."""

    async def execute(self, arguments: dict[str, Any], user_context: UserContext | None = None) -> BuiltinToolResult:
        """Execute the tool with given arguments."""
        ...


# =============================================================================
# Helper Functions
# =============================================================================


def get_workspace_dir(user_context: UserContext | None = None) -> str:
    """Get workspace directory path, creating if needed.

    If user_context is provided, creates a user-specific subdirectory.
    """
    if user_context:
        workspace_dir = os.path.join(WORKSPACE_BASE_DIR, user_context.user_id)
    else:
        workspace_dir = os.path.join(WORKSPACE_BASE_DIR, "anonymous")

    os.makedirs(workspace_dir, exist_ok=True)
    return workspace_dir


def cleanup_old_files(workspace_dir: str, max_age_seconds: int = MAX_FILE_AGE_SECONDS) -> None:
    """Remove files older than max_age_seconds from the workspace directory."""
    if not os.path.exists(workspace_dir):
        return

    now = datetime.now(UTC).timestamp()
    for filename in os.listdir(workspace_dir):
        file_path = os.path.join(workspace_dir, filename)
        if os.path.isfile(file_path):
            try:
                file_age = now - os.path.getmtime(file_path)
                if file_age > max_age_seconds:
                    os.remove(file_path)
                    logger.debug(f"Cleaned up old file: {filename}")
            except OSError as e:
                logger.warning(f"Failed to clean up file {filename}: {e}")


def is_text_content(content_type: str) -> bool:
    """Check if content type indicates text content."""
    text_types = [
        "text/",
        "application/xml",
        "application/xhtml",
        "application/javascript",
        "application/ecmascript",
    ]
    return any(content_type.startswith(t) for t in text_types)


def is_json_content(content_type: str) -> bool:
    """Check if content type indicates JSON content."""
    return "json" in content_type or content_type.endswith("+json")


def extract_filename(response: Any, url: str) -> str:
    """Extract a filename from response headers or URL."""
    # Try Content-Disposition header first
    content_disposition = response.headers.get("content-disposition", "")
    if "filename=" in content_disposition:
        match = re.search(r'filename[*]?=["\']?([^"\';]+)', content_disposition)
        if match:
            return match.group(1)

    # Extract from URL path
    parsed = urlparse(url)
    path = parsed.path
    if path and "/" in path:
        filename = path.split("/")[-1]
        if filename:
            return filename

    # Default filename with extension based on content type
    content_type = response.headers.get("content-type", "").split(";")[0].strip()
    ext_map = {
        "application/pdf": ".pdf",
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/gif": ".gif",
        "application/zip": ".zip",
        "application/octet-stream": ".bin",
    }
    ext = ext_map.get(content_type, ".bin")
    return f"downloaded_file{ext}"


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename to prevent path traversal and other issues."""
    # Remove path separators and null bytes
    filename = filename.replace("/", "_").replace("\\", "_").replace("\x00", "")
    # Remove leading dots
    filename = filename.lstrip(".")
    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[: 255 - len(ext)] + ext
    return filename or "unnamed_file"
