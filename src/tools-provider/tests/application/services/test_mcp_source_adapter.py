"""Tests for McpSourceAdapter.

Tests cover:
- Basic adapter functionality
- Tool discovery via MCP protocol
- Conversion of MCP tools to ToolDefinitions
- Error handling
- Inventory hashing
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from application.services.mcp_source_adapter import McpSourceAdapter
from domain.enums import ExecutionMode, McpTransportType, PluginLifecycleMode, SourceType
from domain.models import McpEnvironmentVariable, McpSourceConfig
from infrastructure.mcp import McpEnvironmentResolver, McpTransportError, TransportFactory
from infrastructure.mcp.env_resolver import ResolutionResult
from infrastructure.mcp.models import McpServerInfo, McpToolDefinition

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


def create_sample_mcp_tool() -> McpToolDefinition:
    """Create a sample MCP tool definition."""
    return McpToolDefinition(
        name="get_weather",
        description="Get weather for a location",
        input_schema={
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "City name"},
            },
            "required": ["location"],
        },
    )


def create_server_info() -> McpServerInfo:
    """Create sample MCP server info."""
    return McpServerInfo(
        name="test-plugin",
        version="1.0.0",
        protocol_version="2024-11-05",
    )


# ============================================================================
# ADAPTER BASIC TESTS
# ============================================================================


class TestMcpSourceAdapterBasics:
    """Test basic adapter functionality."""

    def test_adapter_returns_correct_source_type(self) -> None:
        """Test that adapter correctly reports MCP source type."""
        adapter = McpSourceAdapter()
        assert adapter.source_type == SourceType.MCP

    def test_adapter_initializes_with_default_resolver(self) -> None:
        """Test that adapter creates default env resolver."""
        adapter = McpSourceAdapter()
        assert adapter._env_resolver is not None

    def test_adapter_accepts_custom_factory(self) -> None:
        """Test that adapter accepts custom transport factory."""
        mock_factory = MagicMock(spec=TransportFactory)
        adapter = McpSourceAdapter(transport_factory=mock_factory)
        assert adapter._transport_factory is mock_factory


# ============================================================================
# FETCH AND NORMALIZE TESTS
# ============================================================================


class TestMcpFetchAndNormalize:
    """Test tool discovery and normalization."""

    @pytest.fixture
    def mock_factory(self) -> MagicMock:
        """Create mock transport factory."""
        return MagicMock(spec=TransportFactory)

    @pytest.fixture
    def mock_env_resolver(self) -> MagicMock:
        """Create mock environment resolver."""
        return MagicMock(spec=McpEnvironmentResolver)

    @pytest.fixture
    def adapter(self, mock_factory: MagicMock, mock_env_resolver: MagicMock) -> McpSourceAdapter:
        """Create adapter instance with mocks."""
        return McpSourceAdapter(transport_factory=mock_factory, env_resolver=mock_env_resolver)

    @pytest.mark.asyncio
    async def test_fetch_returns_tools(self, adapter: McpSourceAdapter, mock_factory: MagicMock, mock_env_resolver: MagicMock) -> None:
        """Test that fetch_and_normalize returns discovered tools."""
        mcp_config = create_sample_mcp_config()

        mock_env_resolver.resolve.return_value = ResolutionResult(
            resolved={"API_KEY": "test-key"},  # pragma: allowlist secret
            missing=[],
            warnings=[],
        )

        mock_transport = MagicMock()
        mock_transport.connect = AsyncMock(return_value=create_server_info())
        mock_transport.list_tools = AsyncMock(return_value=[create_sample_mcp_tool()])
        mock_transport.disconnect = AsyncMock()
        mock_factory.get_transport = AsyncMock(return_value=mock_transport)

        result = await adapter.fetch_and_normalize(
            url="file:///app/plugins/test-mcp",
            mcp_config=mcp_config,
        )

        assert result.success is True
        assert len(result.tools) == 1
        assert result.tools[0].name == "get_weather"

    @pytest.mark.asyncio
    async def test_fetch_requires_mcp_config(self, adapter: McpSourceAdapter) -> None:
        """Test that fetch fails without mcp_config."""
        result = await adapter.fetch_and_normalize(
            url="file:///app/plugins/test-mcp",
            mcp_config=None,
        )

        assert result.success is False
        assert result.error is not None and "mcp_config" in result.error.lower()

    @pytest.mark.asyncio
    async def test_fetch_fails_on_missing_env_vars(self, adapter: McpSourceAdapter, mock_env_resolver: MagicMock) -> None:
        """Test that fetch fails when required env vars are missing."""
        mcp_config = create_sample_mcp_config()

        mock_env_resolver.resolve.return_value = ResolutionResult(
            resolved={},
            missing=["API_KEY"],
            warnings=[],
        )

        result = await adapter.fetch_and_normalize(
            url="file:///app/plugins/test-mcp",
            mcp_config=mcp_config,
        )

        assert result.success is False
        assert result.error is not None
        assert "environment" in result.error.lower() or "API_KEY" in result.error

    @pytest.mark.asyncio
    async def test_fetch_handles_transport_error(self, adapter: McpSourceAdapter, mock_factory: MagicMock, mock_env_resolver: MagicMock) -> None:
        """Test that transport errors are handled gracefully."""
        mcp_config = create_sample_mcp_config()

        mock_env_resolver.resolve.return_value = ResolutionResult(
            resolved={"API_KEY": "test-key"},  # pragma: allowlist secret,
            missing=[],
            warnings=[],
        )

        mock_factory.get_transport = AsyncMock(side_effect=McpTransportError("Connection refused"))

        result = await adapter.fetch_and_normalize(
            url="file:///app/plugins/test-mcp",
            mcp_config=mcp_config,
        )

        assert result.success is False


# ============================================================================
# TOOL CONVERSION TESTS
# ============================================================================


class TestMcpToolConversion:
    """Test conversion of MCP tools to ToolDefinitions."""

    @pytest.fixture
    def adapter(self) -> McpSourceAdapter:
        """Create adapter instance."""
        return McpSourceAdapter()

    def test_conversion_preserves_name(self, adapter: McpSourceAdapter) -> None:
        """Test that tool name is preserved."""
        mcp_tool = create_sample_mcp_tool()
        mcp_config = create_sample_mcp_config()

        tool_def = adapter._convert_mcp_tool(mcp_tool, mcp_config)

        assert tool_def.name == "get_weather"

    def test_conversion_preserves_description(self, adapter: McpSourceAdapter) -> None:
        """Test that tool description is preserved."""
        mcp_tool = create_sample_mcp_tool()
        mcp_config = create_sample_mcp_config()

        tool_def = adapter._convert_mcp_tool(mcp_tool, mcp_config)

        assert tool_def.description == "Get weather for a location"

    def test_conversion_preserves_input_schema(self, adapter: McpSourceAdapter) -> None:
        """Test that input schema is preserved."""
        mcp_tool = create_sample_mcp_tool()
        mcp_config = create_sample_mcp_config()

        tool_def = adapter._convert_mcp_tool(mcp_tool, mcp_config)

        assert "location" in tool_def.input_schema.get("properties", {})

    def test_conversion_sets_execution_mode_mcp(self, adapter: McpSourceAdapter) -> None:
        """Test that execution mode is set to MCP_CALL."""
        mcp_tool = create_sample_mcp_tool()
        mcp_config = create_sample_mcp_config()

        tool_def = adapter._convert_mcp_tool(mcp_tool, mcp_config)

        assert tool_def.execution_profile.mode == ExecutionMode.MCP_CALL


# ============================================================================
# INVENTORY HASH TESTS
# ============================================================================


class TestMcpInventoryHash:
    """Test inventory hash computation."""

    @pytest.fixture
    def adapter(self) -> McpSourceAdapter:
        """Create adapter instance."""
        return McpSourceAdapter()

    @pytest.fixture
    def mock_factory(self) -> MagicMock:
        """Create mock transport factory."""
        return MagicMock(spec=TransportFactory)

    @pytest.fixture
    def mock_env_resolver(self) -> MagicMock:
        """Create mock environment resolver."""
        return MagicMock(spec=McpEnvironmentResolver)

    @pytest.mark.asyncio
    async def test_inventory_hash_changes_with_tools(self, mock_factory: MagicMock, mock_env_resolver: MagicMock) -> None:
        """Test that inventory hash changes when tools change."""
        adapter = McpSourceAdapter(transport_factory=mock_factory, env_resolver=mock_env_resolver)
        mcp_config = create_sample_mcp_config()

        mock_env_resolver.resolve.return_value = ResolutionResult(
            resolved={"API_KEY": "test-key"},  # pragma: allowlist secret,
            missing=[],
            warnings=[],
        )

        tool1 = create_sample_mcp_tool()
        tool2 = McpToolDefinition(
            name="get_time",
            description="Get current time",
            input_schema={},
        )

        mock_transport = MagicMock()
        mock_transport.connect = AsyncMock(return_value=create_server_info())
        mock_transport.disconnect = AsyncMock()
        mock_factory.get_transport = AsyncMock(return_value=mock_transport)

        # First fetch with one tool
        mock_transport.list_tools = AsyncMock(return_value=[tool1])
        result1 = await adapter.fetch_and_normalize(
            url="file:///app/plugins/test-mcp",
            mcp_config=mcp_config,
        )

        # Second fetch with two tools
        mock_transport.list_tools = AsyncMock(return_value=[tool1, tool2])
        result2 = await adapter.fetch_and_normalize(
            url="file:///app/plugins/test-mcp",
            mcp_config=mcp_config,
        )

        assert result1.inventory_hash != result2.inventory_hash


# ============================================================================
# VALIDATION TESTS
# ============================================================================


class TestMcpValidation:
    """Test URL/config validation."""

    @pytest.fixture
    def adapter(self) -> McpSourceAdapter:
        """Create adapter instance."""
        return McpSourceAdapter()

    @pytest.mark.asyncio
    async def test_validate_url_with_valid_config(self, adapter: McpSourceAdapter) -> None:
        """Test validation with valid MCP config."""
        is_valid = await adapter.validate_url(
            url="file:///app/plugins/test-mcp",
        )

        # Validation should return boolean
        assert isinstance(is_valid, bool)
