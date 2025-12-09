"""ToolSelector value object.

Rules for including tools in a ToolGroup.
"""

import fnmatch
import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ToolSelector:
    """Rules for including tools in a ToolGroup via pattern matching.

    All criteria are AND'd together (all must match for tool to be included).
    Use multiple selectors in a ToolGroup for OR logic.

    Pattern syntax:
    - Standard glob patterns: * (any chars), ? (single char)
    - Regex patterns: prefix with "regex:" (e.g., "regex:^create_.*")

    This is an immutable value object used within ToolGroup aggregate.
    """

    id: str  # Unique identifier for this selector
    source_pattern: str = "*"  # Pattern for source name matching
    name_pattern: str = "*"  # Pattern for tool name matching
    path_pattern: str | None = None  # Pattern for source path matching
    method_pattern: str | None = None  # Pattern for HTTP method matching (GET, POST, etc.)

    # Tag filtering
    required_tags: list[str] = field(default_factory=list)  # ALL must be present
    excluded_tags: list[str] = field(default_factory=list)  # NONE must be present

    # Label filtering
    required_label_ids: list[str] = field(default_factory=list)  # ALL must be present

    def matches(
        self,
        source_name: str,
        tool_name: str,
        source_path: str,
        tags: list[str],
        method: str = "",
        label_ids: list[str] | None = None,
    ) -> bool:
        """Check if a tool matches this selector's criteria.

        Args:
            source_name: Name of the upstream source
            tool_name: Name of the tool
            source_path: Original path from the source spec
            tags: List of tags associated with the tool
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            label_ids: List of label IDs associated with the tool

        Returns:
            True if all criteria match, False otherwise
        """
        # Check source pattern
        if not self._matches_pattern(self.source_pattern, source_name):
            return False

        # Check name pattern
        if not self._matches_pattern(self.name_pattern, tool_name):
            return False

        # Check path pattern (if specified)
        if self.path_pattern and not self._matches_pattern(self.path_pattern, source_path):
            return False

        # Check method pattern (if specified)
        if self.method_pattern and not self._matches_pattern(self.method_pattern, method):
            return False

        # Check required tags (all must be present)
        if self.required_tags:
            tag_set = set(tags)
            if not all(tag in tag_set for tag in self.required_tags):
                return False

        # Check excluded tags (none must be present)
        if self.excluded_tags:
            tag_set = set(tags)
            if any(tag in tag_set for tag in self.excluded_tags):
                return False

        # Check required label IDs (all must be present)
        if self.required_label_ids:
            tool_label_set = set(label_ids or [])
            if not all(label_id in tool_label_set for label_id in self.required_label_ids):
                return False

        return True

    def _matches_pattern(self, pattern: str, value: str) -> bool:
        """Check if value matches the pattern.

        Supports glob patterns (default) or regex (prefix with "regex:").
        Pattern matching is case-insensitive for better UX.
        """
        if pattern == "*":
            return True

        if pattern.startswith("regex:"):
            regex_pattern = pattern[6:]  # Remove "regex:" prefix
            return bool(re.match(regex_pattern, value, re.IGNORECASE))

        # Use fnmatch for glob-style matching (case-insensitive)
        return fnmatch.fnmatch(value.lower(), pattern.lower())

    def to_dict(self) -> dict:
        """Serialize to dictionary for storage."""
        return {
            "id": self.id,
            "source_pattern": self.source_pattern,
            "name_pattern": self.name_pattern,
            "path_pattern": self.path_pattern,
            "method_pattern": self.method_pattern,
            "required_tags": list(self.required_tags),
            "excluded_tags": list(self.excluded_tags),
            "required_label_ids": list(self.required_label_ids),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ToolSelector":
        """Deserialize from dictionary."""
        return cls(
            id=data["id"],
            source_pattern=data.get("source_pattern", "*"),
            name_pattern=data.get("name_pattern", "*"),
            path_pattern=data.get("path_pattern"),
            method_pattern=data.get("method_pattern"),
            required_tags=data.get("required_tags", []),
            excluded_tags=data.get("excluded_tags", []),
            required_label_ids=data.get("required_label_ids", []),
        )

    @classmethod
    def match_all(cls, selector_id: str) -> "ToolSelector":
        """Factory method for a selector that matches all tools."""
        return cls(id=selector_id)

    @classmethod
    def by_source(cls, selector_id: str, source_pattern: str) -> "ToolSelector":
        """Factory method for a selector that matches tools from specific sources."""
        return cls(id=selector_id, source_pattern=source_pattern)

    @classmethod
    def by_name(cls, selector_id: str, name_pattern: str) -> "ToolSelector":
        """Factory method for a selector that matches tools by name."""
        return cls(id=selector_id, name_pattern=name_pattern)

    @classmethod
    def by_tags(
        cls,
        selector_id: str,
        required_tags: list[str] | None = None,
        excluded_tags: list[str] | None = None,
    ) -> "ToolSelector":
        """Factory method for a selector that matches tools by tags."""
        return cls(
            id=selector_id,
            required_tags=required_tags or [],
            excluded_tags=excluded_tags or [],
        )
