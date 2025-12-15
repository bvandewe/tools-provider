"""Integration tests for MCP source registration.

Tests cover:
- Registering MCP sources via the command handler
- MCP source configuration validation
- MCP manifest parsing and tool discovery
- Error handling for invalid MCP sources
"""

import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from application.commands import RegisterSourceCommand
from domain.enums import HealthStatus, McpTransportType, PluginLifecycleMode, SourceType
from domain.models import McpSourceConfig
from integration.models.source_dto import SourceDto
from tests.fixtures.factories import McpSourceConfigFactory, UpstreamSourceFactory

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def sample_mcp_manifest_json() -> str:
    """Create a sample MCP server.json manifest content."""
    return """{
    "name": "test-mcp-server",
    "title": "Test MCP Server",
    "description": "A test MCP server for integration testing",
    "version": "1.0.0",
    "repository": {
        "type": "git",
        "url": "https://github.com/example/test-mcp"
    },
    "packages": [
        {
            "registryType": "pypi",
            "identifier": "test-mcp-server",
            "version": "1.0.0",
            "runtimeHint": "uvx",
            "transport": {
                "type": "stdio"
            },
            "environmentVariables": [
                {
                    "name": "TEST_API_KEY",
                    "description": "API key for test service",
                    "isRequired": true,
                    "isSecret": true
                },
                {
                    "name": "TEST_URL",
                    "description": "URL of the test service",
                    "isRequired": false,
                    "isSecret": false,
                    "format": "uri"
                }
            ]
        }
    ]
}"""


@pytest.fixture
def temp_plugin_dir(sample_mcp_manifest_json: str) -> Generator[Path, None, None]:
    """Create a temporary plugin directory with a manifest file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        plugin_dir = Path(tmpdir)
        manifest_path = plugin_dir / "server.json"
        manifest_path.write_text(sample_mcp_manifest_json)
        yield plugin_dir


@pytest.fixture
def mock_source_repository() -> MagicMock:
    """Create mock source repository."""
    mock = MagicMock()
    mock.add_async = AsyncMock()
    mock.get_async = AsyncMock(return_value=None)
    mock.update_async = AsyncMock()
    return mock


@pytest.fixture
def mock_source_dto_repository() -> MagicMock:
    """Create mock source DTO repository."""
    mock = MagicMock()
    mock.add_async = AsyncMock()
    mock.get_async = AsyncMock(return_value=None)
    mock.update_async = AsyncMock()
    return mock


@pytest.fixture
def mock_mediator() -> MagicMock:
    """Create mock mediator."""
    mock = MagicMock()
    mock.execute_async = AsyncMock()
    return mock


@pytest.fixture
def mock_mapper() -> MagicMock:
    """Create mock mapper."""
    mock = MagicMock()
    mock.map = MagicMock(side_effect=lambda obj, target_type: _mock_map_to_dto(obj))
    return mock


def _mock_map_to_dto(source: Any) -> SourceDto:
    """Mock mapping function for UpstreamSource to SourceDto."""
    return SourceDto(
        id=str(source.id) if hasattr(source, "id") else "test-id",
        name=source.state.name if hasattr(source, "state") else "Test",
        url=source.state.url if hasattr(source, "state") else "https://test.com",
        source_type=SourceType(source.state.source_type.value) if hasattr(source, "state") else SourceType.MCP,
        health_status=HealthStatus.UNKNOWN,
        is_enabled=True,
        inventory_count=0,
    )


# ============================================================================
# MCP SOURCE REGISTRATION TESTS
# ============================================================================


class TestMcpSourceRegistration:
    """Integration tests for MCP source registration."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_register_mcp_source_command_fields(self) -> None:
        """Test that RegisterSourceCommand accepts MCP-specific fields."""
        command = RegisterSourceCommand(
            name="test-mcp",
            url="file:///app/plugins/test-mcp",
            source_type="mcp",
            user_info={"sub": "user123"},
            mcp_plugin_dir="/app/plugins/test-mcp",
            mcp_manifest_path="/app/plugins/test-mcp/server.json",
            mcp_transport_type="stdio",
            mcp_lifecycle_mode="transient",
            mcp_runtime_hint="uvx",
            mcp_command="uvx test-mcp",
            mcp_args=[],
            mcp_env_vars={"TEST_VAR": "test_value"},
        )

        assert command.source_type == "mcp"
        assert command.mcp_plugin_dir == "/app/plugins/test-mcp"
        assert command.mcp_transport_type == "stdio"
        assert command.mcp_lifecycle_mode == "transient"
        assert command.mcp_runtime_hint == "uvx"
        assert command.mcp_env_vars == {"TEST_VAR": "test_value"}

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_mcp_source_config_from_command(self) -> None:
        """Test building McpSourceConfig from command fields."""
        config = McpSourceConfig(
            manifest_path="/app/plugins/test-mcp/server.json",
            plugin_dir="/app/plugins/test-mcp",
            transport_type=McpTransportType.STDIO,
            lifecycle_mode=PluginLifecycleMode.TRANSIENT,
            runtime_hint="uvx",
            command=["uvx", "test-mcp"],
            environment={"TEST_VAR": "test_value"},
            env_definitions=[],
        )

        assert config.transport_type == McpTransportType.STDIO
        assert config.lifecycle_mode == PluginLifecycleMode.TRANSIENT
        assert config.runtime_hint == "uvx"
        assert config.command == ["uvx", "test-mcp"]
        assert config.environment == {"TEST_VAR": "test_value"}

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_mcp_source_config_serialization(self) -> None:
        """Test that McpSourceConfig can be serialized and deserialized."""
        original = McpSourceConfigFactory.create_with_env_vars()
        serialized = original.to_dict()
        deserialized = McpSourceConfig.from_dict(serialized)

        assert deserialized.manifest_path == original.manifest_path
        assert deserialized.plugin_dir == original.plugin_dir
        assert deserialized.transport_type == original.transport_type
        assert deserialized.lifecycle_mode == original.lifecycle_mode
        assert deserialized.runtime_hint == original.runtime_hint
        assert deserialized.command == original.command


# ============================================================================
# MCP MANIFEST PARSING TESTS
# ============================================================================


class TestMcpManifestParsing:
    """Integration tests for MCP manifest parsing."""

    @pytest.mark.integration
    def test_parse_manifest_from_file(self, temp_plugin_dir: Path) -> None:
        """Test parsing an MCP manifest from a file."""
        from domain.models.mcp_manifest import McpManifest

        manifest_path = temp_plugin_dir / "server.json"
        manifest = McpManifest.parse(str(manifest_path))

        assert manifest.name == "test-mcp-server"
        assert manifest.title == "Test MCP Server"
        assert manifest.version == "1.0.0"
        assert len(manifest.packages) == 1

        package = manifest.get_default_package()
        assert package.identifier == "test-mcp-server"
        assert package.runtime_hint == "uvx"
        assert package.transport_type == "stdio"
        assert len(package.environment_variables) == 2

    @pytest.mark.integration
    def test_parse_manifest_extracts_env_vars(self, temp_plugin_dir: Path) -> None:
        """Test that manifest parsing extracts environment variable definitions."""
        from domain.models.mcp_manifest import McpManifest

        manifest_path = temp_plugin_dir / "server.json"
        manifest = McpManifest.parse(str(manifest_path))

        package = manifest.get_default_package()
        env_vars = {ev.name: ev for ev in package.environment_variables}

        assert "TEST_API_KEY" in env_vars
        assert env_vars["TEST_API_KEY"].is_required is True
        assert env_vars["TEST_API_KEY"].is_secret is True

        assert "TEST_URL" in env_vars
        assert env_vars["TEST_URL"].is_required is False
        assert env_vars["TEST_URL"].is_secret is False

    @pytest.mark.integration
    def test_manifest_not_found_raises_error(self) -> None:
        """Test that parsing non-existent manifest raises FileNotFoundError."""
        from domain.models.mcp_manifest import McpManifest

        with pytest.raises(FileNotFoundError):
            McpManifest.parse("/nonexistent/path/server.json")

    @pytest.mark.integration
    def test_create_config_from_manifest(self, temp_plugin_dir: Path) -> None:
        """Test creating McpSourceConfig from a parsed manifest."""
        from domain.models.mcp_manifest import McpManifest

        manifest_path = temp_plugin_dir / "server.json"
        manifest = McpManifest.parse(str(manifest_path))
        config = McpSourceConfig.from_manifest(manifest, str(temp_plugin_dir))

        assert config.manifest_path == f"{temp_plugin_dir}/server.json"
        assert config.plugin_dir == str(temp_plugin_dir)
        assert config.transport_type == McpTransportType.STDIO
        assert config.runtime_hint == "uvx"
        assert len(config.env_definitions) == 2


# ============================================================================
# MCP SOURCE VALIDATION TESTS
# ============================================================================


class TestMcpSourceValidation:
    """Integration tests for MCP source validation."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_validate_valid_mcp_plugin_dir(self, temp_plugin_dir: Path) -> None:
        """Test validating a directory with a valid MCP manifest."""
        from application.services import McpSourceAdapter

        adapter = McpSourceAdapter()
        is_valid = await adapter.validate_url(f"file://{temp_plugin_dir}")

        assert is_valid is True

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_validate_invalid_mcp_plugin_dir(self) -> None:
        """Test validating a directory without a manifest."""
        from application.services import McpSourceAdapter

        with tempfile.TemporaryDirectory() as tmpdir:
            adapter = McpSourceAdapter()
            is_valid = await adapter.validate_url(f"file://{tmpdir}")

            assert is_valid is False

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_validate_nonexistent_path(self) -> None:
        """Test validating a non-existent path."""
        from application.services import McpSourceAdapter

        adapter = McpSourceAdapter()
        is_valid = await adapter.validate_url("file:///nonexistent/path")

        assert is_valid is False


# ============================================================================
# MCP SOURCE TYPE INTEGRATION TESTS
# ============================================================================


class TestMcpSourceTypeIntegration:
    """Integration tests for MCP as a source type."""

    @pytest.mark.integration
    def test_source_type_enum_includes_mcp(self) -> None:
        """Test that SourceType enum includes MCP."""
        assert SourceType.MCP.value == "mcp"
        assert SourceType("mcp") == SourceType.MCP

    @pytest.mark.integration
    def test_mcp_transport_type_enum(self) -> None:
        """Test McpTransportType enum values."""
        assert McpTransportType.STDIO.value == "stdio"
        assert McpTransportType.SSE.value == "sse"

    @pytest.mark.integration
    def test_plugin_lifecycle_mode_enum(self) -> None:
        """Test PluginLifecycleMode enum values."""
        assert PluginLifecycleMode.TRANSIENT.value == "transient"
        assert PluginLifecycleMode.SINGLETON.value == "singleton"

    @pytest.mark.integration
    def test_mcp_source_factory_creates_valid_source(self) -> None:
        """Test that UpstreamSourceFactory creates valid MCP sources."""
        source = UpstreamSourceFactory.create_mcp()

        assert source.state.source_type == SourceType.MCP
        assert source.state.mcp_config is not None
