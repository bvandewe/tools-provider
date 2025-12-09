"""ToolDefinition value object.

The normalized representation of a tool from an upstream source.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from .execution_profile import ExecutionProfile


@dataclass(frozen=True)
class ToolDefinition:
    """The normalized representation of a tool from an upstream source.

    This is the core value object that represents a callable tool,
    regardless of whether it came from OpenAPI, a workflow engine, etc.

    This is an immutable value object discovered during inventory sync
    and stored within SourceTool aggregates.
    """

    name: str  # Unique tool name within source
    description: str  # Human-readable description for AI agents
    input_schema: dict  # JSON Schema for tool arguments
    execution_profile: ExecutionProfile  # How to execute the tool
    source_path: str  # Original path (e.g., "/api/v1/users")

    # Optional metadata
    tags: List[str] = field(default_factory=list)
    version: Optional[str] = None
    deprecated: bool = False

    def to_dict(self) -> dict:
        """Serialize to dictionary for storage."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": dict(self.input_schema),
            "execution_profile": self.execution_profile.to_dict(),
            "source_path": self.source_path,
            "tags": list(self.tags),
            "version": self.version,
            "deprecated": self.deprecated,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ToolDefinition":
        """Deserialize from dictionary."""
        return cls(
            name=data["name"],
            description=data["description"],
            input_schema=data["input_schema"],
            execution_profile=ExecutionProfile.from_dict(data["execution_profile"]),
            source_path=data["source_path"],
            tags=data.get("tags", []),
            version=data.get("version"),
            deprecated=data.get("deprecated", False),
        )

    def compute_hash(self) -> str:
        """Compute a hash of the tool definition for change detection.

        Used to detect when a tool's definition has changed during inventory sync.
        """
        import hashlib
        import json

        # Create a deterministic string representation
        content = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
