"""McpSourceConfig value object.

MCP-specific configuration for UpstreamSource when source_type is MCP.
This value object captures all settings needed to connect to and manage
an MCP (Model Context Protocol) plugin server.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from domain.enums import McpTransportType, PluginLifecycleMode

if TYPE_CHECKING:
    from domain.models.mcp_manifest import McpManifest


@dataclass(frozen=True)
class McpEnvironmentVariable:
    """Environment variable definition from an MCP server manifest.

    Represents a single environment variable that the MCP plugin requires
    or optionally accepts for configuration.

    This is an immutable value object used within McpSourceConfig.
    """

    name: str  # Variable name (e.g., "CML_URL")
    description: str  # Human-readable description
    is_required: bool  # Whether the variable must be provided
    is_secret: bool  # Whether the value should be treated as sensitive
    format: str = "string"  # Expected format (string, uri, etc.)
    value: str | None = None  # Resolved value (None if not yet resolved)

    def to_dict(self) -> dict:
        """Serialize to dictionary for storage."""
        return {
            "name": self.name,
            "description": self.description,
            "is_required": self.is_required,
            "is_secret": self.is_secret,
            "format": self.format,
            "value": self.value,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "McpEnvironmentVariable":
        """Deserialize from dictionary."""
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            is_required=data.get("is_required", False),
            is_secret=data.get("is_secret", False),
            format=data.get("format", "string"),
            value=data.get("value"),
        )


@dataclass(frozen=True)
class McpSourceConfig:
    """MCP-specific configuration for an UpstreamSource.

    Stored as a sub-document in UpstreamSource for sources with
    source_type == SourceType.MCP.

    This configuration is derived from parsing the MCP server manifest
    (server.json) and contains all information needed to:
    - Start the MCP server subprocess
    - Communicate with the server via the specified transport
    - Manage the server lifecycle
    - Pass required environment variables

    This is an immutable value object.
    """

    manifest_path: str  # Absolute path to server.json
    plugin_dir: str  # Directory containing the plugin
    transport_type: McpTransportType  # Communication protocol (stdio/sse)
    lifecycle_mode: PluginLifecycleMode  # Subprocess management mode
    runtime_hint: str  # Runtime to use (uvx, npx, docker, python, etc.)
    command: list[str] = field(default_factory=list)  # Command to start the server
    environment: dict[str, str] = field(default_factory=dict)  # Resolved env vars
    env_definitions: list[McpEnvironmentVariable] = field(default_factory=list)  # Original definitions

    def to_dict(self) -> dict:
        """Serialize to dictionary for storage."""
        return {
            "manifest_path": self.manifest_path,
            "plugin_dir": self.plugin_dir,
            "transport_type": self.transport_type.value,
            "lifecycle_mode": self.lifecycle_mode.value,
            "runtime_hint": self.runtime_hint,
            "command": list(self.command),
            "environment": dict(self.environment),
            "env_definitions": [env.to_dict() for env in self.env_definitions],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "McpSourceConfig":
        """Deserialize from dictionary."""
        return cls(
            manifest_path=data["manifest_path"],
            plugin_dir=data["plugin_dir"],
            transport_type=McpTransportType(data["transport_type"]),
            lifecycle_mode=PluginLifecycleMode(data["lifecycle_mode"]),
            runtime_hint=data["runtime_hint"],
            command=data.get("command", []),
            environment=data.get("environment", {}),
            env_definitions=[McpEnvironmentVariable.from_dict(env) for env in data.get("env_definitions", [])],
        )

    @classmethod
    def from_manifest(cls, manifest: "McpManifest", plugin_dir: str) -> "McpSourceConfig":
        """Create config from a parsed MCP manifest.

        This is the primary factory method used during MCP source registration.

        Args:
            manifest: Parsed McpManifest from server.json
            plugin_dir: Directory containing the plugin files

        Returns:
            McpSourceConfig populated from manifest data
        """
        package = manifest.get_default_package()

        return cls(
            manifest_path=f"{plugin_dir}/server.json",
            plugin_dir=plugin_dir,
            transport_type=McpTransportType(package.transport_type),
            lifecycle_mode=PluginLifecycleMode.TRANSIENT,  # Default to transient
            runtime_hint=package.runtime_hint or "uvx",
            command=package.build_command(),
            environment={},  # To be resolved later by env resolver
            env_definitions=[
                McpEnvironmentVariable(
                    name=env.name,
                    description=env.description,
                    is_required=env.is_required,
                    is_secret=env.is_secret,
                    format=env.format,
                )
                for env in package.environment_variables
            ],
        )

    def with_resolved_environment(self, resolved_env: dict[str, str]) -> "McpSourceConfig":
        """Create a new config with resolved environment variables.

        Since McpSourceConfig is immutable, this returns a new instance
        with the environment field populated.

        Args:
            resolved_env: Dictionary of resolved environment variable values

        Returns:
            New McpSourceConfig with environment populated
        """
        # Also update the value field in env_definitions
        updated_definitions = [
            McpEnvironmentVariable(
                name=env.name,
                description=env.description,
                is_required=env.is_required,
                is_secret=env.is_secret,
                format=env.format,
                value=resolved_env.get(env.name),
            )
            for env in self.env_definitions
        ]

        return McpSourceConfig(
            manifest_path=self.manifest_path,
            plugin_dir=self.plugin_dir,
            transport_type=self.transport_type,
            lifecycle_mode=self.lifecycle_mode,
            runtime_hint=self.runtime_hint,
            command=self.command,
            environment=resolved_env,
            env_definitions=updated_definitions,
        )

    def get_missing_required_vars(self) -> list[str]:
        """Get list of required environment variables that are not resolved.

        Returns:
            List of variable names that are required but have no value
        """
        return [env.name for env in self.env_definitions if env.is_required and not self.environment.get(env.name)]

    def is_ready(self) -> bool:
        """Check if all required environment variables are resolved.

        Returns:
            True if the config is ready to start the MCP server
        """
        return len(self.get_missing_required_vars()) == 0
