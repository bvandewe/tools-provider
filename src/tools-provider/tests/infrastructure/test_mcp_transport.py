"""Tests for MCP transport infrastructure.

Tests cover:
- MCP protocol models (serialization/deserialization)
- IMcpTransport interface contract
- StdioTransport with mocked subprocess
- TransportFactory lifecycle management
- McpEnvironmentResolver resolution logic
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from domain.enums import McpTransportType, PluginLifecycleMode
from domain.models import McpEnvironmentVariable, McpSourceConfig
from infrastructure.mcp.env_resolver import McpEnvironmentResolver, ResolutionResult
from infrastructure.mcp.models import (
    McpContent,
    McpError,
    McpRequest,
    McpResponse,
    McpServerInfo,
    McpToolDefinition,
    McpToolResult,
)
from infrastructure.mcp.stdio_transport import StdioTransport
from infrastructure.mcp.transport import (
    McpConnectionError,
)
from infrastructure.mcp.transport_factory import TransportFactory

# ============================================================================
# SAMPLE DATA FACTORIES
# ============================================================================


def create_sample_mcp_config(
    lifecycle_mode: PluginLifecycleMode = PluginLifecycleMode.TRANSIENT,
) -> McpSourceConfig:
    """Create a sample McpSourceConfig for testing."""
    return McpSourceConfig(
        manifest_path="/app/plugins/test-mcp/server.json",
        plugin_dir="/app/plugins/test-mcp",
        transport_type=McpTransportType.STDIO,
        lifecycle_mode=lifecycle_mode,
        runtime_hint="uvx",
        command=["uvx", "test-mcp"],
        environment={"TEST_VAR": "test-value"},
        env_definitions=[
            McpEnvironmentVariable(
                name="TEST_VAR",
                description="Test variable",
                is_required=False,
                is_secret=False,
            ),
            McpEnvironmentVariable(
                name="API_KEY",
                description="API key",
                is_required=True,
                is_secret=True,
            ),
        ],
    )


# ============================================================================
# MCP PROTOCOL MODELS TESTS
# ============================================================================


class TestMcpRequest:
    """Test McpRequest model."""

    def test_create_request(self) -> None:
        """Test creating an MCP request."""
        request = McpRequest(id=1, method="tools/list", params={"cursor": None})

        assert request.id == 1
        assert request.method == "tools/list"
        assert request.params == {"cursor": None}

    def test_request_to_dict(self) -> None:
        """Test serializing request to JSON-RPC format."""
        request = McpRequest(id=42, method="tools/call", params={"name": "test"})

        serialized = request.to_dict()

        assert serialized["jsonrpc"] == "2.0"
        assert serialized["id"] == 42
        assert serialized["method"] == "tools/call"
        assert serialized["params"] == {"name": "test"}

    def test_request_from_dict(self) -> None:
        """Test deserializing request from dictionary."""
        data = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05"},
        }

        request = McpRequest.from_dict(data)

        assert request.id == 1
        assert request.method == "initialize"
        assert request.params["protocolVersion"] == "2024-11-05"


class TestMcpResponse:
    """Test McpResponse model."""

    def test_create_success_response(self) -> None:
        """Test creating a successful response."""
        response = McpResponse(id=1, result={"tools": []})

        assert response.id == 1
        assert response.result == {"tools": []}
        assert response.error is None
        assert response.is_error() is False

    def test_create_error_response(self) -> None:
        """Test creating an error response."""
        error = McpError(code=-32600, message="Invalid request")
        response = McpResponse(id=1, error=error)

        assert response.is_error() is True
        assert response.error is not None
        assert response.error.code == -32600

    def test_response_to_dict_success(self) -> None:
        """Test serializing successful response."""
        response = McpResponse(id=1, result={"data": "value"})

        serialized = response.to_dict()

        assert serialized["jsonrpc"] == "2.0"
        assert serialized["id"] == 1
        assert serialized["result"] == {"data": "value"}
        assert "error" not in serialized

    def test_response_to_dict_error(self) -> None:
        """Test serializing error response."""
        error = McpError(code=-32601, message="Method not found")
        response = McpResponse(id=1, error=error)

        serialized = response.to_dict()

        assert "error" in serialized
        assert serialized["error"]["code"] == -32601
        assert "result" not in serialized


class TestMcpError:
    """Test McpError model."""

    def test_error_codes(self) -> None:
        """Test standard error code constants."""
        assert McpError.PARSE_ERROR == -32700
        assert McpError.INVALID_REQUEST == -32600
        assert McpError.METHOD_NOT_FOUND == -32601
        assert McpError.INTERNAL_ERROR == -32603

    def test_error_serialization(self) -> None:
        """Test error serialization."""
        error = McpError(code=-32602, message="Invalid params", data={"param": "name"})

        serialized = error.to_dict()

        assert serialized["code"] == -32602
        assert serialized["message"] == "Invalid params"
        assert serialized["data"] == {"param": "name"}


class TestMcpToolResult:
    """Test McpToolResult model."""

    def test_create_text_result(self) -> None:
        """Test creating a text result."""
        content = [McpContent.text_content("Hello, world!")]
        result = McpToolResult(content=content, is_error=False)

        assert len(result.content) == 1
        assert result.get_text() == "Hello, world!"
        assert result.is_error is False

    def test_result_from_dict(self) -> None:
        """Test creating result from response data."""
        data = {
            "content": [{"type": "text", "text": "Result text"}],
            "isError": False,
        }

        result = McpToolResult.from_dict(data)

        assert len(result.content) == 1
        assert result.content[0].type == "text"
        assert result.get_text() == "Result text"

    def test_error_result(self) -> None:
        """Test error result handling."""
        result = McpToolResult(
            content=[McpContent.text_content("Error occurred")],
            is_error=True,
        )

        assert result.is_error is True


class TestMcpToolDefinition:
    """Test McpToolDefinition model."""

    def test_from_dict(self) -> None:
        """Test creating tool definition from API response."""
        data = {
            "name": "get_data",
            "description": "Get some data",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "The ID"},
                    "limit": {"type": "integer", "default": 10},
                },
                "required": ["id"],
            },
        }

        tool = McpToolDefinition.from_dict(data)

        assert tool.name == "get_data"
        assert tool.description == "Get some data"
        assert tool.get_required_params() == ["id"]
        assert "id" in tool.get_properties()


class TestMcpServerInfo:
    """Test McpServerInfo model."""

    def test_from_dict(self) -> None:
        """Test creating server info from initialize response."""
        data = {
            "protocolVersion": "2024-11-05",
            "serverInfo": {
                "name": "test-server",
                "version": "1.0.0",
            },
            "capabilities": {"tools": {}},
        }

        info = McpServerInfo.from_dict(data)

        assert info.name == "test-server"
        assert info.version == "1.0.0"
        assert info.protocol_version == "2024-11-05"


# ============================================================================
# STDIO TRANSPORT TESTS
# ============================================================================


class TestStdioTransport:
    """Test StdioTransport implementation."""

    def test_create_transport(self) -> None:
        """Test creating a transport instance."""
        transport = StdioTransport(
            command=["uvx", "test-mcp"],
            environment={"API_KEY": "test"},  # pragma: allowlist secret
            cwd="/tmp",
        )

        assert transport._command == ["uvx", "test-mcp"]
        assert transport._environment == {"API_KEY": "test"}  # pragma: allowlist secret
        assert transport._cwd == "/tmp"
        assert transport.is_connected is False

    def test_empty_command_raises_error(self) -> None:
        """Test that empty command raises ValueError."""
        with pytest.raises(ValueError, match="Command cannot be empty"):
            StdioTransport(command=[])

    @pytest.mark.asyncio
    async def test_connect_command_not_found(self) -> None:
        """Test that non-existent command raises McpConnectionError."""
        transport = StdioTransport(command=["nonexistent-command-12345"])

        with pytest.raises(McpConnectionError, match="command not found"):
            await transport.connect()

    @pytest.mark.asyncio
    async def test_disconnect_idempotent(self) -> None:
        """Test that disconnect can be called multiple times."""
        transport = StdioTransport(command=["echo"])

        # Should not raise even when not connected
        await transport.disconnect()
        await transport.disconnect()

    def test_repr(self) -> None:
        """Test string representation."""
        transport = StdioTransport(command=["uvx", "my-mcp"])

        repr_str = repr(transport)

        assert "StdioTransport" in repr_str
        assert "uvx my-mcp" in repr_str
        assert "disconnected" in repr_str


class TestStdioTransportWithMockProcess:
    """Test StdioTransport with mocked subprocess."""

    @pytest.fixture
    def mock_process(self) -> MagicMock:
        """Create a mock subprocess."""
        process = MagicMock()
        process.returncode = None
        process.stdin = MagicMock()
        process.stdout = MagicMock()
        process.stderr = MagicMock()
        process.stdin.write = MagicMock()
        process.stdin.drain = AsyncMock()
        process.terminate = MagicMock()
        process.kill = MagicMock()
        process.wait = AsyncMock()
        return process

    @pytest.mark.asyncio
    async def test_list_tools_not_connected(self) -> None:
        """Test that list_tools raises when not connected."""
        transport = StdioTransport(command=["echo"])

        with pytest.raises(McpConnectionError, match="not connected"):
            await transport.list_tools()

    @pytest.mark.asyncio
    async def test_call_tool_not_connected(self) -> None:
        """Test that call_tool raises when not connected."""
        transport = StdioTransport(command=["echo"])

        with pytest.raises(McpConnectionError, match="not connected"):
            await transport.call_tool("test", {})


# ============================================================================
# TRANSPORT FACTORY TESTS
# ============================================================================


class TestTransportFactory:
    """Test TransportFactory functionality."""

    def test_create_factory(self) -> None:
        """Test creating a transport factory."""
        factory = TransportFactory()

        assert factory.active_transports == 0

    @pytest.mark.asyncio
    async def test_create_stdio_transport(self) -> None:
        """Test creating a stdio transport from config."""
        factory = TransportFactory()
        config = create_sample_mcp_config()

        transport = factory._create_transport(config)

        assert isinstance(transport, StdioTransport)
        assert transport._command == ["uvx", "test-mcp"]

    @pytest.mark.asyncio
    async def test_unsupported_transport_type(self) -> None:
        """Test that SSE transport raises not implemented."""
        factory = TransportFactory()
        config = McpSourceConfig(
            manifest_path="/test",
            plugin_dir="/test",
            transport_type=McpTransportType.SSE,
            lifecycle_mode=PluginLifecycleMode.TRANSIENT,
            runtime_hint="node",
            command=["node", "server.js"],
            environment={},
            env_definitions=[],
        )

        with pytest.raises(ValueError, match="SSE transport not yet implemented"):
            factory._create_transport(config)

    @pytest.mark.asyncio
    async def test_pool_status(self) -> None:
        """Test getting pool status."""
        factory = TransportFactory()

        status = factory.get_pool_status()

        assert status["active_transports"] == 0
        assert status["transports"] == {}

    @pytest.mark.asyncio
    async def test_close_all_empty_pool(self) -> None:
        """Test closing all transports with empty pool."""
        factory = TransportFactory()

        # Should not raise
        await factory.close_all()

        assert factory.active_transports == 0

    @pytest.mark.asyncio
    async def test_context_manager(self) -> None:
        """Test factory as async context manager."""
        async with TransportFactory() as factory:
            assert factory.active_transports == 0

        # After exit, close_all should have been called


# ============================================================================
# ENVIRONMENT RESOLVER TESTS
# ============================================================================


class TestMcpEnvironmentResolver:
    """Test McpEnvironmentResolver functionality."""

    def test_create_resolver(self) -> None:
        """Test creating a resolver."""
        resolver = McpEnvironmentResolver()

        assert resolver.loaded_plugins == []

    def test_resolve_from_config(self) -> None:
        """Test resolving variables from config."""
        resolver = McpEnvironmentResolver()
        config = McpSourceConfig(
            manifest_path="/app/test/server.json",
            plugin_dir="/app/test",
            transport_type=McpTransportType.STDIO,
            lifecycle_mode=PluginLifecycleMode.TRANSIENT,
            runtime_hint="uvx",
            command=["uvx", "test"],
            environment={"MY_VAR": "my-value"},
            env_definitions=[
                McpEnvironmentVariable(
                    name="MY_VAR",
                    description="Test",
                    is_required=True,
                    is_secret=False,
                ),
            ],
        )

        result = resolver.resolve(config)

        assert result.is_complete
        assert result.resolved["MY_VAR"] == "my-value"
        assert result.missing == []

    def test_resolve_from_runtime_override(self) -> None:
        """Test that runtime overrides take precedence."""
        resolver = McpEnvironmentResolver()
        config = McpSourceConfig(
            manifest_path="/app/test/server.json",
            plugin_dir="/app/test",
            transport_type=McpTransportType.STDIO,
            lifecycle_mode=PluginLifecycleMode.TRANSIENT,
            runtime_hint="uvx",
            command=["uvx", "test"],
            environment={"MY_VAR": "config-value"},
            env_definitions=[
                McpEnvironmentVariable(
                    name="MY_VAR",
                    description="Test",
                    is_required=True,
                    is_secret=False,
                ),
            ],
        )

        result = resolver.resolve(config, runtime_overrides={"MY_VAR": "runtime-value"})

        assert result.resolved["MY_VAR"] == "runtime-value"

    def test_resolve_missing_required(self) -> None:
        """Test that missing required variables are tracked."""
        resolver = McpEnvironmentResolver(allow_os_env=False)
        config = McpSourceConfig(
            manifest_path="/app/test/server.json",
            plugin_dir="/app/test",
            transport_type=McpTransportType.STDIO,
            lifecycle_mode=PluginLifecycleMode.TRANSIENT,
            runtime_hint="uvx",
            command=["uvx", "test"],
            environment={},
            env_definitions=[
                McpEnvironmentVariable(
                    name="REQUIRED_VAR",
                    description="Required",
                    is_required=True,
                    is_secret=False,
                ),
            ],
        )

        result = resolver.resolve(config)

        assert not result.is_complete
        assert "REQUIRED_VAR" in result.missing

    def test_resolve_optional_missing_ok(self) -> None:
        """Test that missing optional variables are okay."""
        resolver = McpEnvironmentResolver(allow_os_env=False)
        config = McpSourceConfig(
            manifest_path="/app/test/server.json",
            plugin_dir="/app/test",
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
                ),
            ],
        )

        result = resolver.resolve(config)

        assert result.is_complete
        assert result.missing == []

    def test_resolve_to_dict_raises_on_missing(self) -> None:
        """Test that resolve_to_dict raises on missing required vars."""
        resolver = McpEnvironmentResolver(allow_os_env=False)
        config = McpSourceConfig(
            manifest_path="/app/test/server.json",
            plugin_dir="/app/test",
            transport_type=McpTransportType.STDIO,
            lifecycle_mode=PluginLifecycleMode.TRANSIENT,
            runtime_hint="uvx",
            command=["uvx", "test"],
            environment={},
            env_definitions=[
                McpEnvironmentVariable(
                    name="REQUIRED_VAR",
                    description="Required",
                    is_required=True,
                    is_secret=False,
                ),
            ],
        )

        with pytest.raises(ValueError, match="Missing required"):
            resolver.resolve_to_dict(config)

    def test_validate_config(self) -> None:
        """Test validating config for missing variables."""
        resolver = McpEnvironmentResolver(allow_os_env=False)
        config = McpSourceConfig(
            manifest_path="/app/test/server.json",
            plugin_dir="/app/test",
            transport_type=McpTransportType.STDIO,
            lifecycle_mode=PluginLifecycleMode.TRANSIENT,
            runtime_hint="uvx",
            command=["uvx", "test"],
            environment={"VAR1": "value1"},
            env_definitions=[
                McpEnvironmentVariable(name="VAR1", description="", is_required=True, is_secret=False),
                McpEnvironmentVariable(name="VAR2", description="", is_required=True, is_secret=False),
                McpEnvironmentVariable(name="VAR3", description="", is_required=False, is_secret=False),
            ],
        )

        missing = resolver.validate_config(config)

        assert missing == ["VAR2"]


class TestMcpEnvironmentResolverWithSecretsFile:
    """Test McpEnvironmentResolver with secrets file."""

    @pytest.fixture
    def secrets_file(self, tmp_path: Path) -> Path:
        """Create a temporary secrets file."""
        secrets_path = tmp_path / "mcp-plugins.yaml"
        secrets_content = """
plugins:
  test-plugin:
    API_KEY: secret-api-key
    API_URL: https://api.example.com
  another-plugin:
    TOKEN: another-token
"""
        secrets_path.write_text(secrets_content)
        return secrets_path

    def test_load_secrets_from_file(self, secrets_file: Path) -> None:
        """Test loading secrets from YAML file."""
        resolver = McpEnvironmentResolver(secrets_path=secrets_file)

        assert "test-plugin" in resolver.loaded_plugins
        assert "another-plugin" in resolver.loaded_plugins

    def test_resolve_from_secrets(self, secrets_file: Path) -> None:
        """Test resolving variables from secrets file."""
        resolver = McpEnvironmentResolver(secrets_path=secrets_file, allow_os_env=False)
        config = McpSourceConfig(
            manifest_path="/app/test-plugin/server.json",
            plugin_dir="/app/test-plugin",
            transport_type=McpTransportType.STDIO,
            lifecycle_mode=PluginLifecycleMode.TRANSIENT,
            runtime_hint="uvx",
            command=["uvx", "test"],
            environment={},
            env_definitions=[
                McpEnvironmentVariable(
                    name="API_KEY",
                    description="API Key",
                    is_required=True,
                    is_secret=True,
                ),
            ],
        )

        result = resolver.resolve(config)

        assert result.is_complete
        assert result.resolved["API_KEY"] == "secret-api-key"  # pragma: allowlist secret

    def test_get_plugin_secrets(self, secrets_file: Path) -> None:
        """Test getting secrets for a specific plugin."""
        resolver = McpEnvironmentResolver(secrets_path=secrets_file)

        secrets = resolver.get_plugin_secrets("test-plugin")

        assert secrets["API_KEY"] == "secret-api-key"  # pragma: allowlist secret
        assert secrets["API_URL"] == "https://api.example.com"

    def test_has_plugin_secrets(self, secrets_file: Path) -> None:
        """Test checking if plugin has secrets."""
        resolver = McpEnvironmentResolver(secrets_path=secrets_file)

        assert resolver.has_plugin_secrets("test-plugin") is True
        assert resolver.has_plugin_secrets("nonexistent-plugin") is False

    def test_reload_secrets(self, secrets_file: Path) -> None:
        """Test reloading secrets from file."""
        resolver = McpEnvironmentResolver(secrets_path=secrets_file)
        assert len(resolver.loaded_plugins) == 2

        # Modify the file
        secrets_file.write_text("""
plugins:
  new-plugin:
    NEW_VAR: new-value
""")

        resolver.reload()

        assert "new-plugin" in resolver.loaded_plugins
        assert "test-plugin" not in resolver.loaded_plugins


class TestResolutionResult:
    """Test ResolutionResult dataclass."""

    def test_is_complete_true(self) -> None:
        """Test is_complete when no missing vars."""
        result = ResolutionResult(
            resolved={"VAR1": "value1"},
            missing=[],
        )

        assert result.is_complete is True

    def test_is_complete_false(self) -> None:
        """Test is_complete when missing vars exist."""
        result = ResolutionResult(
            resolved={},
            missing=["REQUIRED_VAR"],
        )

        assert result.is_complete is False


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


class TestMcpInfrastructureIntegration:
    """Integration tests for MCP infrastructure components."""

    @pytest.mark.asyncio
    async def test_factory_creates_transport_with_resolved_env(self, tmp_path: Path) -> None:
        """Test that factory uses env resolver when available."""
        # Create secrets file
        secrets_path = tmp_path / "secrets.yaml"
        secrets_path.write_text("""
plugins:
  test-mcp:
    API_KEY: resolved-key
""")

        resolver = McpEnvironmentResolver(secrets_path=secrets_path)
        factory = TransportFactory(env_resolver=resolver)

        config = McpSourceConfig(
            manifest_path=str(tmp_path / "server.json"),
            plugin_dir=str(tmp_path),
            transport_type=McpTransportType.STDIO,
            lifecycle_mode=PluginLifecycleMode.TRANSIENT,
            runtime_hint="uvx",
            command=["uvx", "test-mcp"],
            environment={},
            env_definitions=[
                McpEnvironmentVariable(
                    name="API_KEY",
                    description="API Key",
                    is_required=True,
                    is_secret=True,
                ),
            ],
        )

        # Override plugin_dir name to match secrets
        config = McpSourceConfig(
            manifest_path=str(tmp_path / "test-mcp" / "server.json"),
            plugin_dir=str(tmp_path / "test-mcp"),
            transport_type=McpTransportType.STDIO,
            lifecycle_mode=PluginLifecycleMode.TRANSIENT,
            runtime_hint="uvx",
            command=["uvx", "test-mcp"],
            environment={},
            env_definitions=[
                McpEnvironmentVariable(
                    name="API_KEY",
                    description="API Key",
                    is_required=True,
                    is_secret=True,
                ),
            ],
        )

        transport = factory._create_transport(config)

        # The environment should contain the resolved key
        assert transport._environment.get("API_KEY") == "resolved-key"
