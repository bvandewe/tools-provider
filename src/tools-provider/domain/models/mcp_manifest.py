"""McpManifest parser.

Parses MCP server manifest files (server.json) following the official
Model Context Protocol schema.

Schema reference: https://static.modelcontextprotocol.io/schemas/2025-10-17/server.schema.json
"""

import json
from dataclasses import dataclass, field
from pathlib import Path


class McpManifestError(Exception):
    """Error raised when parsing an MCP manifest fails."""

    pass


@dataclass
class McpEnvVarDefinition:
    """Environment variable definition from server.json.

    Represents a single environment variable that the MCP server
    requires or optionally accepts.
    """

    name: str  # Variable name (e.g., "CML_URL")
    description: str  # Human-readable description
    is_required: bool  # Whether the variable must be provided
    is_secret: bool  # Whether the value is sensitive (should be masked)
    format: str = "string"  # Expected format (string, uri, etc.)

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "is_required": self.is_required,
            "is_secret": self.is_secret,
            "format": self.format,
        }


@dataclass
class McpPackage:
    """Package definition from server.json.

    Represents a single distribution package for an MCP server,
    defining how to install and run the server.
    """

    registry_type: str  # Package registry: pypi, npm, docker
    identifier: str  # Package name/identifier
    version: str  # Package version
    runtime_hint: str | None  # Runtime to use: uvx, npx, docker, python, node
    transport_type: str  # Communication protocol: stdio, sse
    environment_variables: list[McpEnvVarDefinition] = field(default_factory=list)
    args: list[str] = field(default_factory=list)  # Additional command arguments

    def build_command(self) -> list[str]:
        """Build the command to start this MCP server.

        Returns:
            List of command parts to execute the MCP server
        """
        base_command: list[str] = []

        if self.runtime_hint == "uvx":
            base_command = ["uvx", self.identifier]
        elif self.runtime_hint == "npx":
            base_command = ["npx", "-y", self.identifier]
        elif self.runtime_hint == "docker":
            base_command = ["docker", "run", "-i", "--rm", self.identifier]
        elif self.runtime_hint == "node":
            base_command = ["node", self.identifier]
        elif self.runtime_hint == "python":
            # Assume Python module
            module_name = self.identifier.replace("-", "_")
            base_command = ["python", "-m", module_name]
        else:
            # Fallback: try direct execution
            base_command = [self.identifier]

        # Append any additional arguments
        if self.args:
            base_command.extend(self.args)

        return base_command

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "registry_type": self.registry_type,
            "identifier": self.identifier,
            "version": self.version,
            "runtime_hint": self.runtime_hint,
            "transport_type": self.transport_type,
            "environment_variables": [env.to_dict() for env in self.environment_variables],
            "args": self.args,
        }


@dataclass
class McpManifest:
    """Parsed MCP server manifest (server.json).

    This class represents a fully parsed MCP server manifest file,
    containing all metadata and configuration needed to register
    and run an MCP plugin.

    Schema reference: https://static.modelcontextprotocol.io/schemas/2025-10-17/server.schema.json

    Example manifest structure:
    ```json
    {
        "name": "cml-mcp",
        "title": "Cisco Modeling Labs MCP",
        "description": "MCP server for CML network simulation",
        "version": "0.1.0",
        "repository": {"url": "https://github.com/example/cml-mcp"},
        "packages": [
            {
                "registryType": "pypi",
                "identifier": "cml-mcp",
                "runtimeHint": "uvx",
                "transport": {"type": "stdio"},
                "environmentVariables": [
                    {"name": "CML_URL", "description": "CML server URL", "isRequired": true}
                ]
            }
        ]
    }
    ```
    """

    name: str  # Unique identifier for the server
    title: str  # Human-readable display name
    description: str  # Detailed description
    version: str  # Semantic version string
    repository_url: str | None  # Source code repository URL
    packages: list[McpPackage] = field(default_factory=list)  # Distribution packages
    icon_url: str | None = None  # Optional icon URL
    license: str | None = None  # Optional license identifier

    @classmethod
    def parse(cls, manifest_path: str | Path) -> "McpManifest":
        """Parse a server.json manifest file.

        Args:
            manifest_path: Path to the server.json file

        Returns:
            Parsed McpManifest instance

        Raises:
            McpManifestError: If the manifest cannot be parsed or is invalid
            FileNotFoundError: If the manifest file does not exist
        """
        path = Path(manifest_path)

        if not path.exists():
            raise FileNotFoundError(f"MCP manifest not found: {path}")

        if not path.is_file():
            raise McpManifestError(f"MCP manifest path is not a file: {path}")

        try:
            with path.open(encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise McpManifestError(f"Invalid JSON in MCP manifest: {e}") from e

        return cls.from_dict(data)

    @classmethod
    def parse_string(cls, manifest_json: str) -> "McpManifest":
        """Parse a manifest from a JSON string.

        Args:
            manifest_json: JSON string containing the manifest

        Returns:
            Parsed McpManifest instance

        Raises:
            McpManifestError: If the JSON is invalid or manifest is malformed
        """
        try:
            data = json.loads(manifest_json)
        except json.JSONDecodeError as e:
            raise McpManifestError(f"Invalid JSON in MCP manifest: {e}") from e

        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict) -> "McpManifest":
        """Create a manifest from a dictionary.

        Args:
            data: Dictionary containing manifest data

        Returns:
            Parsed McpManifest instance

        Raises:
            McpManifestError: If required fields are missing or invalid
        """
        # Validate required fields
        if not data.get("name"):
            raise McpManifestError("MCP manifest missing required field: 'name'")

        # Parse packages
        packages: list[McpPackage] = []
        for pkg_data in data.get("packages", []):
            env_vars = [
                McpEnvVarDefinition(
                    name=env.get("name", ""),
                    description=env.get("description", ""),
                    is_required=env.get("isRequired", False),
                    is_secret=env.get("isSecret", False),
                    format=env.get("format", "string"),
                )
                for env in pkg_data.get("environmentVariables", [])
            ]

            # Handle transport configuration
            transport_data = pkg_data.get("transport", {})
            transport_type = transport_data.get("type", "stdio") if isinstance(transport_data, dict) else "stdio"

            packages.append(
                McpPackage(
                    registry_type=pkg_data.get("registryType", "pypi"),
                    identifier=pkg_data.get("identifier", ""),
                    version=pkg_data.get("version", data.get("version", "0.0.0")),
                    runtime_hint=pkg_data.get("runtimeHint"),
                    transport_type=transport_type,
                    environment_variables=env_vars,
                    args=pkg_data.get("args", []),
                )
            )

        # Parse repository URL
        repository_data = data.get("repository", {})
        repository_url = repository_data.get("url") if isinstance(repository_data, dict) else None

        return cls(
            name=data.get("name", ""),
            title=data.get("title", data.get("name", "")),
            description=data.get("description", ""),
            version=data.get("version", "0.0.0"),
            repository_url=repository_url,
            packages=packages,
            icon_url=data.get("iconUrl"),
            license=data.get("license"),
        )

    def get_default_package(self) -> McpPackage:
        """Get the first/default package for execution.

        MCP manifests can define multiple packages (e.g., PyPI and NPM),
        but we typically use the first one as the default.

        Returns:
            The first package in the manifest

        Raises:
            McpManifestError: If no packages are defined
        """
        if not self.packages:
            raise McpManifestError(f"MCP manifest '{self.name}' has no packages defined")
        return self.packages[0]

    def get_package_by_registry(self, registry_type: str) -> McpPackage | None:
        """Get a package by registry type.

        Args:
            registry_type: Registry type to look for (pypi, npm, docker)

        Returns:
            The matching package, or None if not found
        """
        for package in self.packages:
            if package.registry_type.lower() == registry_type.lower():
                return package
        return None

    def to_dict(self) -> dict:
        """Serialize to dictionary for storage.

        Returns:
            Dictionary representation of the manifest
        """
        return {
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "version": self.version,
            "repository_url": self.repository_url,
            "packages": [pkg.to_dict() for pkg in self.packages],
            "icon_url": self.icon_url,
            "license": self.license,
        }

    def compute_hash(self) -> str:
        """Compute a hash of the manifest for change detection.

        Used to detect when a manifest has changed during sync.

        Returns:
            SHA-256 hash of the manifest content (first 16 chars)
        """
        import hashlib

        content = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
