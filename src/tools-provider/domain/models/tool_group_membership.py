"""ToolGroupMembership value object.

Tracks explicit tool membership in a ToolGroup, including audit information.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ToolGroupMembership:
    """Tracks a tool's explicit membership in a ToolGroup.

    This value object records when and by whom a tool was explicitly
    added to a group (as opposed to being matched by a selector).

    This is an immutable value object used within ToolGroup aggregate.
    """

    tool_id: str  # Format: "{source_id}:{operation_id}"
    added_at: datetime
    added_by: str | None

    def to_dict(self) -> dict:
        """Serialize to dictionary for storage."""
        return {
            "tool_id": self.tool_id,
            "added_at": self.added_at.isoformat(),
            "added_by": self.added_by,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ToolGroupMembership":
        """Deserialize from dictionary."""
        added_at = data["added_at"]
        if isinstance(added_at, str):
            # Parse ISO format string
            added_at = datetime.fromisoformat(added_at.replace("Z", "+00:00"))

        return cls(
            tool_id=data["tool_id"],
            added_at=added_at,
            added_by=data.get("added_by"),
        )


@dataclass(frozen=True)
class ToolExclusion:
    """Tracks a tool's exclusion from a ToolGroup.

    Excluded tools are never included in the group, even if they
    match a selector pattern.

    This is an immutable value object used within ToolGroup aggregate.
    """

    tool_id: str  # Format: "{source_id}:{operation_id}"
    excluded_at: datetime
    excluded_by: str | None
    reason: str | None

    def to_dict(self) -> dict:
        """Serialize to dictionary for storage."""
        return {
            "tool_id": self.tool_id,
            "excluded_at": self.excluded_at.isoformat(),
            "excluded_by": self.excluded_by,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ToolExclusion":
        """Deserialize from dictionary."""
        excluded_at = data["excluded_at"]
        if isinstance(excluded_at, str):
            # Parse ISO format string
            excluded_at = datetime.fromisoformat(excluded_at.replace("Z", "+00:00"))

        return cls(
            tool_id=data["tool_id"],
            excluded_at=excluded_at,
            excluded_by=data.get("excluded_by"),
            reason=data.get("reason"),
        )
