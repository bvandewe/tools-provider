"""Tests for MCP source configuration value objects.

Tests cover:
- McpEnvironmentVariable creation and serialization
- McpSourceConfig creation from manifest
- Environment variable resolution
- Serialization and deserialization
- Ready state checking
"""

import pytest

from domain.enums import McpTransportType, PluginLifecycleMode
from domain.models import (
    McpEnvironmentVariable,
    McpEnvVarDefinition,
    McpManifest,
    McpPackage,
    McpSourceConfig,
)

# ============================================================================
# SAMPLE DATA FACTORIES
# ============================================================================


def create_sample_mcp_config() -> McpSourceConfig:
    """Create a sample McpSourceConfig for testing."""
    return McpSourceConfig(
        manifest_path="/app/plugins/cml-mcp/server.json",
        plugin_dir="/app/plugins/cml-mcp",
        transport_type=McpTransportType.STDIO,
        lifecycle_mode=PluginLifecycleMode.TRANSIENT,
        runtime_hint="uvx",
        command=["uvx", "cml-mcp"],
        environment={"CML_URL": "https://cml.example.com"},
        env_definitions=[
            McpEnvironmentVariable(
                name="CML_URL",
                description="CML server URL",
                is_required=True,
                is_secret=False,
                format="uri",
                value="https://cml.example.com",
            ),
            McpEnvironmentVariable(
                name="CML_TOKEN",
                description="CML API token",
                is_required=True,
                is_secret=True,
                format="string",
                value=None,
            ),
        ],
    )


def create_sample_manifest() -> McpManifest:
    """Create a sample McpManifest for testing."""
    return McpManifest(
        name="cml-mcp",
        title="Cisco Modeling Labs MCP",
        description="MCP server for CML",
        version="0.1.0",
        repository_url="https://github.com/example/cml-mcp",
        packages=[
            McpPackage(
                registry_type="pypi",
                identifier="cml-mcp",
                version="0.1.0",
                runtime_hint="uvx",
                transport_type="stdio",
                environment_variables=[
                    McpEnvVarDefinition(
                        name="CML_URL",
                        description="CML server URL",
                        is_required=True,
                        is_secret=False,
                        format="uri",
                    ),
                    McpEnvVarDefinition(
                        name="CML_TOKEN",
                        description="CML API token",
                        is_required=True,
                        is_secret=True,
                    ),
                ],
            )
        ],
    )


# ============================================================================
# MCP ENVIRONMENT VARIABLE TESTS
# ============================================================================


class TestMcpEnvironmentVariable:
    """Test McpEnvironmentVariable value object."""

    def test_create_environment_variable(self) -> None:
        """Test creating an environment variable definition."""
        env_var = McpEnvironmentVariable(
            name="API_KEY",
            description="API key for authentication",
            is_required=True,
            is_secret=True,
            format="string",
            value="secret-key-123",
        )

        assert env_var.name == "API_KEY"
        assert env_var.description == "API key for authentication"
        assert env_var.is_required is True
        assert env_var.is_secret is True
        assert env_var.format == "string"
        assert env_var.value == "secret-key-123"

    def test_environment_variable_defaults(self) -> None:
        """Test environment variable default values."""
        env_var = McpEnvironmentVariable(
            name="TEST_VAR",
            description="Test variable",
            is_required=False,
            is_secret=False,
        )

        assert env_var.format == "string"
        assert env_var.value is None

    def test_environment_variable_immutability(self) -> None:
        """Test that environment variable is immutable."""
        env_var = McpEnvironmentVariable(
            name="TEST_VAR",
            description="Test",
            is_required=False,
            is_secret=False,
        )

        with pytest.raises(AttributeError):
            env_var.name = "NEW_NAME"  # type: ignore[misc]

    def test_environment_variable_serialization(self) -> None:
        """Test environment variable serialization."""
        env_var = McpEnvironmentVariable(
            name="CML_URL",
            description="CML server URL",
            is_required=True,
            is_secret=False,
            format="uri",
            value="https://cml.example.com",
        )

        serialized = env_var.to_dict()

        assert serialized["name"] == "CML_URL"
        assert serialized["description"] == "CML server URL"
        assert serialized["is_required"] is True
        assert serialized["is_secret"] is False
        assert serialized["format"] == "uri"
        assert serialized["value"] == "https://cml.example.com"

    def test_environment_variable_deserialization(self) -> None:
        """Test environment variable deserialization."""
        data = {
            "name": "CML_URL",
            "description": "CML server URL",
            "is_required": True,
            "is_secret": False,
            "format": "uri",
            "value": "https://cml.example.com",
        }

        env_var = McpEnvironmentVariable.from_dict(data)

        assert env_var.name == "CML_URL"
        assert env_var.is_required is True
        assert env_var.value == "https://cml.example.com"


# ============================================================================
# MCP SOURCE CONFIG TESTS
# ============================================================================


class TestMcpSourceConfig:
    """Test McpSourceConfig value object."""

    def test_create_source_config(self) -> None:
        """Test creating a source configuration."""
        config = create_sample_mcp_config()

        assert config.manifest_path == "/app/plugins/cml-mcp/server.json"
        assert config.plugin_dir == "/app/plugins/cml-mcp"
        assert config.transport_type == McpTransportType.STDIO
        assert config.lifecycle_mode == PluginLifecycleMode.TRANSIENT
        assert config.runtime_hint == "uvx"
        assert config.command == ["uvx", "cml-mcp"]
        assert "CML_URL" in config.environment

    def test_source_config_immutability(self) -> None:
        """Test that source config is immutable."""
        config = create_sample_mcp_config()

        with pytest.raises(AttributeError):
            config.runtime_hint = "npx"  # type: ignore[misc]

    def test_source_config_from_manifest(self) -> None:
        """Test creating config from a manifest."""
        manifest = create_sample_manifest()
        plugin_dir = "/app/plugins/cml-mcp"

        config = McpSourceConfig.from_manifest(manifest, plugin_dir)

        assert config.manifest_path == f"{plugin_dir}/server.json"
        assert config.plugin_dir == plugin_dir
        assert config.transport_type == McpTransportType.STDIO
        assert config.lifecycle_mode == PluginLifecycleMode.TRANSIENT
        assert config.runtime_hint == "uvx"
        assert config.command == ["uvx", "cml-mcp"]
        assert config.environment == {}  # Not resolved yet
        assert len(config.env_definitions) == 2

    def test_source_config_serialization(self) -> None:
        """Test source config serialization."""
        config = create_sample_mcp_config()
        serialized = config.to_dict()

        assert serialized["manifest_path"] == config.manifest_path
        assert serialized["plugin_dir"] == config.plugin_dir
        assert serialized["transport_type"] == "stdio"
        assert serialized["lifecycle_mode"] == "transient"
        assert serialized["runtime_hint"] == "uvx"
        assert serialized["command"] == ["uvx", "cml-mcp"]
        assert len(serialized["env_definitions"]) == 2

    def test_source_config_deserialization(self) -> None:
        """Test source config deserialization."""
        config = create_sample_mcp_config()
        serialized = config.to_dict()

        restored = McpSourceConfig.from_dict(serialized)

        assert restored.manifest_path == config.manifest_path
        assert restored.transport_type == config.transport_type
        assert restored.lifecycle_mode == config.lifecycle_mode
        assert len(restored.env_definitions) == len(config.env_definitions)

    def test_source_config_round_trip(self) -> None:
        """Test that config survives round-trip serialization."""
        original = create_sample_mcp_config()

        serialized = original.to_dict()
        restored = McpSourceConfig.from_dict(serialized)

        assert restored.manifest_path == original.manifest_path
        assert restored.plugin_dir == original.plugin_dir
        assert restored.transport_type == original.transport_type
        assert restored.lifecycle_mode == original.lifecycle_mode
        assert restored.runtime_hint == original.runtime_hint
        assert restored.command == original.command
        assert restored.environment == original.environment


# ============================================================================
# ENVIRONMENT RESOLUTION TESTS
# ============================================================================


class TestMcpSourceConfigEnvironment:
    """Test environment variable resolution in McpSourceConfig."""

    def test_with_resolved_environment(self) -> None:
        """Test creating config with resolved environment."""
        manifest = create_sample_manifest()
        config = McpSourceConfig.from_manifest(manifest, "/app/plugins/test")

        resolved_env = {
            "CML_URL": "https://cml.example.com",
            "CML_TOKEN": "secret-token-123",
        }

        new_config = config.with_resolved_environment(resolved_env)

        # Original should be unchanged (immutability)
        assert config.environment == {}

        # New config should have resolved values
        assert new_config.environment == resolved_env
        assert new_config.env_definitions[0].value == "https://cml.example.com"
        assert new_config.env_definitions[1].value == "secret-token-123"

    def test_get_missing_required_vars_empty(self) -> None:
        """Test getting missing required vars when all are resolved."""
        config = McpSourceConfig(
            manifest_path="/app/server.json",
            plugin_dir="/app",
            transport_type=McpTransportType.STDIO,
            lifecycle_mode=PluginLifecycleMode.TRANSIENT,
            runtime_hint="uvx",
            command=["uvx", "test"],
            environment={"REQUIRED_VAR": "value"},
            env_definitions=[
                McpEnvironmentVariable(
                    name="REQUIRED_VAR",
                    description="Required",
                    is_required=True,
                    is_secret=False,
                    value="value",
                )
            ],
        )

        missing = config.get_missing_required_vars()
        assert missing == []

    def test_get_missing_required_vars_with_missing(self) -> None:
        """Test getting missing required vars when some are missing."""
        config = McpSourceConfig(
            manifest_path="/app/server.json",
            plugin_dir="/app",
            transport_type=McpTransportType.STDIO,
            lifecycle_mode=PluginLifecycleMode.TRANSIENT,
            runtime_hint="uvx",
            command=["uvx", "test"],
            environment={},  # No resolved vars
            env_definitions=[
                McpEnvironmentVariable(
                    name="REQUIRED_VAR",
                    description="Required",
                    is_required=True,
                    is_secret=False,
                ),
                McpEnvironmentVariable(
                    name="OPTIONAL_VAR",
                    description="Optional",
                    is_required=False,
                    is_secret=False,
                ),
            ],
        )

        missing = config.get_missing_required_vars()
        assert missing == ["REQUIRED_VAR"]

    def test_is_ready_true(self) -> None:
        """Test is_ready returns True when all required vars resolved."""
        config = McpSourceConfig(
            manifest_path="/app/server.json",
            plugin_dir="/app",
            transport_type=McpTransportType.STDIO,
            lifecycle_mode=PluginLifecycleMode.TRANSIENT,
            runtime_hint="uvx",
            command=["uvx", "test"],
            environment={"API_KEY": "value"},  # pragma: allowlist secret
            env_definitions=[
                McpEnvironmentVariable(
                    name="API_KEY",
                    description="API Key",
                    is_required=True,
                    is_secret=True,
                )
            ],
        )

        assert config.is_ready() is True

    def test_is_ready_false(self) -> None:
        """Test is_ready returns False when required vars missing."""
        manifest = create_sample_manifest()
        config = McpSourceConfig.from_manifest(manifest, "/app/plugins/test")

        # No environment variables resolved
        assert config.is_ready() is False

    def test_is_ready_with_optional_only(self) -> None:
        """Test is_ready with only optional vars (should be True)."""
        config = McpSourceConfig(
            manifest_path="/app/server.json",
            plugin_dir="/app",
            transport_type=McpTransportType.STDIO,
            lifecycle_mode=PluginLifecycleMode.TRANSIENT,
            runtime_hint="uvx",
            command=["uvx", "test"],
            environment={},
            env_definitions=[
                McpEnvironmentVariable(
                    name="OPTIONAL_VAR",
                    description="Optional",
                    is_required=False,
                    is_secret=False,
                )
            ],
        )

        assert config.is_ready() is True


# ============================================================================
# TRANSPORT TYPE TESTS
# ============================================================================


class TestMcpTransportTypes:
    """Test MCP transport type configurations."""

    def test_stdio_transport(self) -> None:
        """Test STDIO transport configuration."""
        config = McpSourceConfig(
            manifest_path="/app/server.json",
            plugin_dir="/app",
            transport_type=McpTransportType.STDIO,
            lifecycle_mode=PluginLifecycleMode.TRANSIENT,
            runtime_hint="uvx",
            command=["uvx", "test"],
            environment={},
            env_definitions=[],
        )

        assert config.transport_type == McpTransportType.STDIO
        assert config.transport_type.value == "stdio"

    def test_sse_transport(self) -> None:
        """Test SSE transport configuration."""
        config = McpSourceConfig(
            manifest_path="/app/server.json",
            plugin_dir="/app",
            transport_type=McpTransportType.SSE,
            lifecycle_mode=PluginLifecycleMode.SINGLETON,
            runtime_hint="node",
            command=["node", "server.js"],
            environment={},
            env_definitions=[],
        )

        assert config.transport_type == McpTransportType.SSE
        assert config.transport_type.value == "sse"


# ============================================================================
# LIFECYCLE MODE TESTS
# ============================================================================


class TestPluginLifecycleModes:
    """Test plugin lifecycle mode configurations."""

    def test_transient_lifecycle(self) -> None:
        """Test TRANSIENT lifecycle mode."""
        config = McpSourceConfig(
            manifest_path="/app/server.json",
            plugin_dir="/app",
            transport_type=McpTransportType.STDIO,
            lifecycle_mode=PluginLifecycleMode.TRANSIENT,
            runtime_hint="uvx",
            command=["uvx", "test"],
            environment={},
            env_definitions=[],
        )

        assert config.lifecycle_mode == PluginLifecycleMode.TRANSIENT
        assert config.lifecycle_mode.value == "transient"

    def test_singleton_lifecycle(self) -> None:
        """Test SINGLETON lifecycle mode."""
        config = McpSourceConfig(
            manifest_path="/app/server.json",
            plugin_dir="/app",
            transport_type=McpTransportType.STDIO,
            lifecycle_mode=PluginLifecycleMode.SINGLETON,
            runtime_hint="uvx",
            command=["uvx", "test"],
            environment={},
            env_definitions=[],
        )

        assert config.lifecycle_mode == PluginLifecycleMode.SINGLETON
        assert config.lifecycle_mode.value == "singleton"
