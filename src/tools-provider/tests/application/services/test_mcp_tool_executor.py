"""Tests for McpToolExecutor.

Tests cover:
- Tool execution via MCP protocol
- Error handling (timeout, connection, validation)
- Health check functionality
- Result mapping
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from application.services import McpExecutionResult
from application.services.mcp_tool_executor import McpToolExecutor
from domain.enums import ExecutionMode, McpTransportType, PluginLifecycleMode
from domain.models import ExecutionProfile, McpEnvironmentVariable, McpSourceConfig, ToolDefinition
from infrastructure.mcp import McpEnvironmentResolver, TransportFactory
from infrastructure.mcp.env_resolver import ResolutionResult
from infrastructure.mcp.models import McpContent, McpServerInfo, McpToolResult
from infrastructure.mcp.transport import McpProtocolError

# ============================================================================
# SAMPLE DATA FACTORIES
# ============================================================================


def create_sample_mcp_config() -> McpSourceConfig:
    """Create a sample McpSourceConfig for testing."""
    return McpSourceConfig(
        manifest_path="/app/plugins/test-mcp/plugin.json",
        plugin_dir="/app/plugins/test-mcp",
        transport_type=McpTransportType.STDIO,
        lifecycle_mode=PluginLifecycleMode.TRANSIENT,
        runtime_hint="python",
        command=["python", "-m", "test_plugin"],
        env_definitions=[
            McpEnvironmentVariable(
                name="API_KEY",
                description="API key for the plugin",
                is_required=True,
                is_secret=True,
            ),
        ],
    )


def create_sample_tool_definition() -> ToolDefinition:
    """Create a sample ToolDefinition for testing."""
    return ToolDefinition(
        name="get_weather",
        description="Get weather for a location",
        input_schema={
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "City name"},
            },
            "required": ["location"],
        },
        execution_profile=ExecutionProfile(
            mode=ExecutionMode.MCP_CALL,
            method="MCP",
            url_template="mcp://test-plugin/get_weather",
        ),
        source_path="mcp://test-plugin",
    )


def create_successful_tool_result() -> McpToolResult:
    """Create a successful MCP tool result."""
    return McpToolResult(
        content=[
            McpContent(
                type="text",
                text='{"temperature": 22.5, "conditions": "sunny"}',
            )
        ],
        is_error=False,
    )


def create_error_tool_result() -> McpToolResult:
    """Create an error MCP tool result."""
    return McpToolResult(
        content=[
            McpContent(
                type="text",
                text="Location not found",
            )
        ],
        is_error=True,
    )


def create_server_info() -> McpServerInfo:
    """Create sample MCP server info."""
    return McpServerInfo(
        name="test-plugin",
        version="1.0.0",
        protocol_version="2024-11-05",
    )


# ============================================================================
# EXECUTOR BASIC TESTS
# ============================================================================


class TestMcpToolExecutorBasics:
    """Test basic executor functionality."""

    def test_executor_initializes_with_factory(self) -> None:
        """Test that executor initializes correctly with factory."""
        mock_factory = MagicMock(spec=TransportFactory)
        executor = McpToolExecutor(transport_factory=mock_factory)
        assert executor._transport_factory is mock_factory

    def test_executor_creates_default_env_resolver(self) -> None:
        """Test that executor creates env resolver if not provided."""
        mock_factory = MagicMock(spec=TransportFactory)
        executor = McpToolExecutor(transport_factory=mock_factory)
        assert executor._env_resolver is not None


# ============================================================================
# TOOL EXECUTION TESTS
# ============================================================================


class TestMcpToolExecution:
    """Test MCP tool execution."""

    @pytest.fixture
    def mock_factory(self) -> MagicMock:
        """Create mock transport factory."""
        return MagicMock(spec=TransportFactory)

    @pytest.fixture
    def mock_env_resolver(self) -> MagicMock:
        """Create mock environment resolver."""
        return MagicMock(spec=McpEnvironmentResolver)

    @pytest.fixture
    def executor(self, mock_factory: MagicMock, mock_env_resolver: MagicMock) -> McpToolExecutor:
        """Create executor instance with mocks."""
        return McpToolExecutor(transport_factory=mock_factory, env_resolver=mock_env_resolver)

    @pytest.mark.asyncio
    async def test_execute_tool_successfully(self, executor: McpToolExecutor, mock_factory: MagicMock, mock_env_resolver: MagicMock) -> None:
        """Test successful tool execution."""
        mcp_config = create_sample_mcp_config()
        definition = create_sample_tool_definition()

        mock_env_resolver.resolve.return_value = ResolutionResult(
            resolved={"API_KEY": "test-key"},  # pragma: allowlist secret
            missing=[],
            warnings=[],
        )

        mock_transport = MagicMock()
        mock_transport.connect = AsyncMock(return_value=create_server_info())
        mock_transport.call_tool = AsyncMock(return_value=create_successful_tool_result())
        mock_transport.disconnect = AsyncMock()
        mock_factory.get_transport = AsyncMock(return_value=mock_transport)

        result = await executor.execute(
            tool_id="test-source:get_weather",
            definition=definition,
            arguments={"location": "New York"},
            mcp_config=mcp_config,
        )

        assert result.success is True
        assert result.content is not None

    @pytest.mark.asyncio
    async def test_execute_returns_tool_error(self, executor: McpToolExecutor, mock_factory: MagicMock, mock_env_resolver: MagicMock) -> None:
        """Test that tool errors are properly returned."""
        mcp_config = create_sample_mcp_config()
        definition = create_sample_tool_definition()

        mock_env_resolver.resolve.return_value = ResolutionResult(
            resolved={"API_KEY": "test-key"},  # pragma: allowlist secret,
            missing=[],
            warnings=[],
        )

        mock_transport = MagicMock()
        mock_transport.connect = AsyncMock(return_value=create_server_info())
        mock_transport.call_tool = AsyncMock(return_value=create_error_tool_result())
        mock_transport.disconnect = AsyncMock()
        mock_factory.get_transport = AsyncMock(return_value=mock_transport)

        result = await executor.execute(
            tool_id="test-source:get_weather",
            definition=definition,
            arguments={"location": "InvalidPlace"},
            mcp_config=mcp_config,
        )

        # When MCP tool returns is_error=True, result should indicate it
        assert result.is_error is True or result.success is False

    @pytest.mark.asyncio
    async def test_execute_fails_on_missing_env_vars(self, executor: McpToolExecutor, mock_env_resolver: MagicMock) -> None:
        """Test that execution fails when required env vars are missing."""
        mcp_config = create_sample_mcp_config()
        definition = create_sample_tool_definition()

        mock_env_resolver.resolve.return_value = ResolutionResult(
            resolved={},
            missing=["API_KEY"],
            warnings=[],
        )

        result = await executor.execute(
            tool_id="test-source:get_weather",
            definition=definition,
            arguments={"location": "New York"},
            mcp_config=mcp_config,
        )

        assert result.success is False
        assert "environment" in (result.error or "").lower() or "missing" in (result.error or "").lower()


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================


class TestMcpErrorHandling:
    """Test error handling in MCP executor."""

    @pytest.fixture
    def mock_factory(self) -> MagicMock:
        """Create mock transport factory."""
        return MagicMock(spec=TransportFactory)

    @pytest.fixture
    def mock_env_resolver(self) -> MagicMock:
        """Create mock environment resolver."""
        return MagicMock(spec=McpEnvironmentResolver)

    @pytest.fixture
    def executor(self, mock_factory: MagicMock, mock_env_resolver: MagicMock) -> McpToolExecutor:
        """Create executor instance with mocks."""
        return McpToolExecutor(transport_factory=mock_factory, env_resolver=mock_env_resolver)

    @pytest.mark.asyncio
    async def test_handles_connection_error(self, executor: McpToolExecutor, mock_factory: MagicMock, mock_env_resolver: MagicMock) -> None:
        """Test handling of transport connection errors."""
        mcp_config = create_sample_mcp_config()
        definition = create_sample_tool_definition()

        mock_env_resolver.resolve.return_value = ResolutionResult(
            resolved={"API_KEY": "test-key"},  # pragma: allowlist secret,
            missing=[],
            warnings=[],
        )

        mock_factory.get_transport = AsyncMock(side_effect=Exception("Connection refused"))

        result = await executor.execute(
            tool_id="test-source:get_weather",
            definition=definition,
            arguments={"location": "New York"},
            mcp_config=mcp_config,
        )

        assert result.success is False

    @pytest.mark.asyncio
    async def test_handles_timeout(self, executor: McpToolExecutor, mock_factory: MagicMock, mock_env_resolver: MagicMock) -> None:
        """Test handling of execution timeout."""
        mcp_config = create_sample_mcp_config()
        definition = create_sample_tool_definition()

        mock_env_resolver.resolve.return_value = ResolutionResult(
            resolved={"API_KEY": "test-key"},  # pragma: allowlist secret,
            missing=[],
            warnings=[],
        )

        mock_transport = MagicMock()
        mock_transport.connect = AsyncMock(return_value=create_server_info())
        mock_transport.call_tool = AsyncMock(side_effect=TimeoutError("Timed out"))
        mock_transport.disconnect = AsyncMock()
        mock_factory.get_transport = AsyncMock(return_value=mock_transport)

        result = await executor.execute(
            tool_id="test-source:slow_operation",
            definition=definition,
            arguments={},
            mcp_config=mcp_config,
            timeout=1.0,
        )

        assert result.success is False

    @pytest.mark.asyncio
    async def test_handles_protocol_error(self, executor: McpToolExecutor, mock_factory: MagicMock, mock_env_resolver: MagicMock) -> None:
        """Test handling of MCP protocol errors."""
        mcp_config = create_sample_mcp_config()
        definition = create_sample_tool_definition()

        mock_env_resolver.resolve.return_value = ResolutionResult(
            resolved={"API_KEY": "test-key"},  # pragma: allowlist secret,
            missing=[],
            warnings=[],
        )

        mock_transport = MagicMock()
        mock_transport.connect = AsyncMock(return_value=create_server_info())
        mock_transport.call_tool = AsyncMock(side_effect=McpProtocolError("Invalid params"))
        mock_transport.disconnect = AsyncMock()
        mock_factory.get_transport = AsyncMock(return_value=mock_transport)

        result = await executor.execute(
            tool_id="test-source:bad_tool",
            definition=definition,
            arguments={"invalid": "params"},
            mcp_config=mcp_config,
        )

        assert result.success is False


# ============================================================================
# HEALTH CHECK TESTS
# ============================================================================


class TestMcpHealthCheck:
    """Test MCP plugin health check."""

    @pytest.fixture
    def mock_factory(self) -> MagicMock:
        """Create mock transport factory."""
        return MagicMock(spec=TransportFactory)

    @pytest.fixture
    def mock_env_resolver(self) -> MagicMock:
        """Create mock environment resolver."""
        return MagicMock(spec=McpEnvironmentResolver)

    @pytest.fixture
    def executor(self, mock_factory: MagicMock, mock_env_resolver: MagicMock) -> McpToolExecutor:
        """Create executor instance with mocks."""
        return McpToolExecutor(transport_factory=mock_factory, env_resolver=mock_env_resolver)

    @pytest.mark.asyncio
    async def test_health_check_success(self, executor: McpToolExecutor, mock_factory: MagicMock, mock_env_resolver: MagicMock) -> None:
        """Test successful health check."""
        mcp_config = create_sample_mcp_config()

        mock_env_resolver.resolve.return_value = ResolutionResult(
            resolved={"API_KEY": "test-key"},  # pragma: allowlist secret,
            missing=[],
            warnings=[],
        )

        mock_transport = MagicMock()
        mock_transport.is_connected = True
        mock_transport.connect = AsyncMock(return_value=create_server_info())
        mock_transport.list_tools = AsyncMock(return_value=[])
        mock_transport.disconnect = AsyncMock()
        mock_factory.get_transport = AsyncMock(return_value=mock_transport)

        is_healthy = await executor.health_check(mcp_config)

        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, executor: McpToolExecutor, mock_factory: MagicMock, mock_env_resolver: MagicMock) -> None:
        """Test health check failure when plugin is unavailable."""
        mcp_config = create_sample_mcp_config()

        mock_env_resolver.resolve.return_value = ResolutionResult(
            resolved={"API_KEY": "test-key"},  # pragma: allowlist secret,
            missing=[],
            warnings=[],
        )

        mock_factory.get_transport = AsyncMock(side_effect=Exception("Plugin not available"))

        is_healthy = await executor.health_check(mcp_config)

        assert is_healthy is False


# ============================================================================
# RESULT MAPPING TESTS
# ============================================================================


class TestMcpResultMapping:
    """Test result mapping from MCP responses."""

    @pytest.fixture
    def mock_factory(self) -> MagicMock:
        """Create mock transport factory."""
        return MagicMock(spec=TransportFactory)

    @pytest.fixture
    def mock_env_resolver(self) -> MagicMock:
        """Create mock environment resolver."""
        return MagicMock(spec=McpEnvironmentResolver)

    @pytest.fixture
    def executor(self, mock_factory: MagicMock, mock_env_resolver: MagicMock) -> McpToolExecutor:
        """Create executor instance with mocks."""
        return McpToolExecutor(transport_factory=mock_factory, env_resolver=mock_env_resolver)

    @pytest.mark.asyncio
    async def test_json_result_is_returned(self, executor: McpToolExecutor, mock_factory: MagicMock, mock_env_resolver: MagicMock) -> None:
        """Test that JSON content is properly returned."""
        mcp_config = create_sample_mcp_config()
        definition = create_sample_tool_definition()

        json_result = McpToolResult(
            content=[
                McpContent(
                    type="text",
                    text='{"key": "value", "nested": {"a": 1}}',
                )
            ],
            is_error=False,
        )

        mock_env_resolver.resolve.return_value = ResolutionResult(
            resolved={"API_KEY": "test-key"},  # pragma: allowlist secret,
            missing=[],
            warnings=[],
        )

        mock_transport = MagicMock()
        mock_transport.connect = AsyncMock(return_value=create_server_info())
        mock_transport.call_tool = AsyncMock(return_value=json_result)
        mock_transport.disconnect = AsyncMock()
        mock_factory.get_transport = AsyncMock(return_value=mock_transport)

        result = await executor.execute(
            tool_id="test-source:json_tool",
            definition=definition,
            arguments={},
            mcp_config=mcp_config,
        )

        assert result.success is True
        assert result.content is not None
        assert len(result.content) > 0

    @pytest.mark.asyncio
    async def test_text_result_is_preserved(self, executor: McpToolExecutor, mock_factory: MagicMock, mock_env_resolver: MagicMock) -> None:
        """Test that plain text content is preserved."""
        mcp_config = create_sample_mcp_config()
        definition = create_sample_tool_definition()

        text_result = McpToolResult(
            content=[
                McpContent(
                    type="text",
                    text="Hello, this is a plain text response!",
                )
            ],
            is_error=False,
        )

        mock_env_resolver.resolve.return_value = ResolutionResult(
            resolved={"API_KEY": "test-key"},  # pragma: allowlist secret,
            missing=[],
            warnings=[],
        )

        mock_transport = MagicMock()
        mock_transport.connect = AsyncMock(return_value=create_server_info())
        mock_transport.call_tool = AsyncMock(return_value=text_result)
        mock_transport.disconnect = AsyncMock()
        mock_factory.get_transport = AsyncMock(return_value=mock_transport)

        result = await executor.execute(
            tool_id="test-source:text_tool",
            definition=definition,
            arguments={},
            mcp_config=mcp_config,
        )

        assert result.success is True
        assert result.content is not None


# ============================================================================
# EXECUTION RESULT DATACLASS TESTS
# ============================================================================


class TestMcpExecutionResult:
    """Test McpExecutionResult dataclass."""

    def test_success_result(self) -> None:
        """Test creating a success result."""
        result = McpExecutionResult(
            success=True,
            content=[{"type": "text", "text": "Hello"}],
        )
        assert result.success is True
        assert len(result.content) == 1

    def test_failure_result(self) -> None:
        """Test creating a failure result."""
        result = McpExecutionResult(
            success=False,
            content=[],
            error="Failed to connect to plugin",
        )
        assert result.success is False
        assert "connect" in (result.error or "").lower()

    def test_result_with_execution_time(self) -> None:
        """Test result includes execution time."""
        result = McpExecutionResult(
            success=True,
            content=[{"type": "text", "text": "data"}],
            execution_time_ms=150.5,
        )
        assert result.execution_time_ms == 150.5

    def test_get_text_combines_content(self) -> None:
        """Test that get_text combines all text content."""
        result = McpExecutionResult(
            success=True,
            content=[
                {"type": "text", "text": "Line 1"},
                {"type": "text", "text": "Line 2"},
            ],
        )
        text = result.get_text()
        assert "Line 1" in text
        assert "Line 2" in text
