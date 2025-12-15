"""Integration tests for MCP tool discovery and sync.

Tests cover:
- Tool discovery from MCP servers
- Tool schema conversion to ToolDefinition
- Inventory sync for MCP sources
- Error handling during tool discovery
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from application.services import McpSourceAdapter
from domain.enums import ExecutionMode
from infrastructure.mcp import McpEnvironmentResolver, TransportFactory
from infrastructure.mcp.env_resolver import ResolutionResult
from infrastructure.mcp.models import McpServerInfo, McpToolDefinition
from tests.fixtures.factories import McpSourceConfigFactory

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def sample_mcp_tools() -> list[McpToolDefinition]:
    """Create sample MCP tools for testing."""
    return [
        McpToolDefinition(
            name="get_labs",
            description="List all labs in CML",
            input_schema={
                "type": "object",
                "properties": {
                    "show_all": {
                        "type": "boolean",
                        "description": "Include stopped labs",
                    }
                },
                "required": [],
            },
        ),
        McpToolDefinition(
            name="create_lab",
            description="Create a new lab from topology",
            input_schema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Lab name",
                    },
                    "topology": {
                        "type": "string",
                        "description": "YAML topology definition",
                    },
                },
                "required": ["name", "topology"],
            },
        ),
        McpToolDefinition(
            name="get_lab_nodes",
            description="Get nodes in a specific lab",
            input_schema={
                "type": "object",
                "properties": {
                    "lab_id": {
                        "type": "string",
                        "description": "Lab identifier",
                    },
                },
                "required": ["lab_id"],
            },
        ),
    ]


@pytest.fixture
def mock_transport() -> MagicMock:
    """Create a mock MCP transport."""
    mock = MagicMock()
    mock.is_connected = True
    mock.connect = AsyncMock(
        return_value=McpServerInfo(
            name="cml-mcp",
            version="1.0.0",
            protocol_version="2024-11-05",
        )
    )
    mock.disconnect = AsyncMock()
    mock.list_tools = AsyncMock(return_value=[])
    mock.call_tool = AsyncMock(return_value={})
    return mock


@pytest.fixture
def mock_transport_factory(mock_transport: MagicMock) -> MagicMock:
    """Create a mock transport factory."""
    mock = MagicMock(spec=TransportFactory)
    mock.get_transport = AsyncMock(return_value=mock_transport)
    return mock


@pytest.fixture
def mock_env_resolver() -> MagicMock:
    """Create a mock environment resolver."""
    mock = MagicMock(spec=McpEnvironmentResolver)
    mock.resolve = MagicMock(
        return_value=ResolutionResult(
            resolved={"CML_URL": "https://cml.example.com", "CML_TOKEN": "test-token"},
            missing=[],
            warnings=[],
        )
    )
    return mock


# ============================================================================
# TOOL DISCOVERY TESTS
# ============================================================================


class TestMcpToolDiscovery:
    """Integration tests for MCP tool discovery."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_discover_tools_from_mcp_server(
        self,
        mock_transport_factory: MagicMock,
        mock_transport: MagicMock,
        mock_env_resolver: MagicMock,
        sample_mcp_tools: list[McpToolDefinition],
    ) -> None:
        """Test discovering tools from an MCP server."""
        mock_transport.list_tools = AsyncMock(return_value=sample_mcp_tools)

        adapter = McpSourceAdapter(
            transport_factory=mock_transport_factory,
            env_resolver=mock_env_resolver,
        )

        config = McpSourceConfigFactory.create_resolved()
        result = await adapter.fetch_and_normalize(
            url=f"file://{config.plugin_dir}",
            mcp_config=config,
        )

        assert result.success is True
        assert len(result.tools) == 3
        assert result.tools[0].name == "get_labs"
        assert result.tools[1].name == "create_lab"
        assert result.tools[2].name == "get_lab_nodes"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_discovered_tools_have_correct_execution_mode(
        self,
        mock_transport_factory: MagicMock,
        mock_transport: MagicMock,
        mock_env_resolver: MagicMock,
        sample_mcp_tools: list[McpToolDefinition],
    ) -> None:
        """Test that discovered tools have MCP_CALL execution mode."""
        mock_transport.list_tools = AsyncMock(return_value=sample_mcp_tools)

        adapter = McpSourceAdapter(
            transport_factory=mock_transport_factory,
            env_resolver=mock_env_resolver,
        )

        config = McpSourceConfigFactory.create_resolved()
        result = await adapter.fetch_and_normalize(
            url=f"file://{config.plugin_dir}",
            mcp_config=config,
        )

        for tool in result.tools:
            assert tool.execution_profile.mode == ExecutionMode.MCP_CALL

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_discovered_tools_preserve_input_schema(
        self,
        mock_transport_factory: MagicMock,
        mock_transport: MagicMock,
        mock_env_resolver: MagicMock,
        sample_mcp_tools: list[McpToolDefinition],
    ) -> None:
        """Test that tool input schemas are preserved correctly."""
        mock_transport.list_tools = AsyncMock(return_value=sample_mcp_tools)

        adapter = McpSourceAdapter(
            transport_factory=mock_transport_factory,
            env_resolver=mock_env_resolver,
        )

        config = McpSourceConfigFactory.create_resolved()
        result = await adapter.fetch_and_normalize(
            url=f"file://{config.plugin_dir}",
            mcp_config=config,
        )

        create_lab_tool = next(t for t in result.tools if t.name == "create_lab")
        assert "properties" in create_lab_tool.input_schema
        assert "name" in create_lab_tool.input_schema["properties"]
        assert "topology" in create_lab_tool.input_schema["properties"]
        assert create_lab_tool.input_schema.get("required") == ["name", "topology"]


# ============================================================================
# INVENTORY HASH TESTS
# ============================================================================


class TestMcpInventoryHash:
    """Integration tests for MCP inventory hashing."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_inventory_hash_is_generated(
        self,
        mock_transport_factory: MagicMock,
        mock_transport: MagicMock,
        mock_env_resolver: MagicMock,
        sample_mcp_tools: list[McpToolDefinition],
    ) -> None:
        """Test that an inventory hash is generated."""
        mock_transport.list_tools = AsyncMock(return_value=sample_mcp_tools)

        adapter = McpSourceAdapter(
            transport_factory=mock_transport_factory,
            env_resolver=mock_env_resolver,
        )

        config = McpSourceConfigFactory.create_resolved()
        result = await adapter.fetch_and_normalize(
            url=f"file://{config.plugin_dir}",
            mcp_config=config,
        )

        assert result.inventory_hash is not None
        assert len(result.inventory_hash) > 0

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_same_tools_produce_same_hash(
        self,
        mock_transport_factory: MagicMock,
        mock_transport: MagicMock,
        mock_env_resolver: MagicMock,
        sample_mcp_tools: list[McpToolDefinition],
    ) -> None:
        """Test that the same tools produce the same hash."""
        mock_transport.list_tools = AsyncMock(return_value=sample_mcp_tools)

        adapter = McpSourceAdapter(
            transport_factory=mock_transport_factory,
            env_resolver=mock_env_resolver,
        )

        config = McpSourceConfigFactory.create_resolved()

        result1 = await adapter.fetch_and_normalize(
            url=f"file://{config.plugin_dir}",
            mcp_config=config,
        )
        result2 = await adapter.fetch_and_normalize(
            url=f"file://{config.plugin_dir}",
            mcp_config=config,
        )

        assert result1.inventory_hash == result2.inventory_hash

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_different_tools_produce_different_hash(
        self,
        mock_transport_factory: MagicMock,
        mock_transport: MagicMock,
        mock_env_resolver: MagicMock,
        sample_mcp_tools: list[McpToolDefinition],
    ) -> None:
        """Test that different tools produce different hashes."""
        adapter = McpSourceAdapter(
            transport_factory=mock_transport_factory,
            env_resolver=mock_env_resolver,
        )

        config = McpSourceConfigFactory.create_resolved()

        # First fetch with all tools
        mock_transport.list_tools = AsyncMock(return_value=sample_mcp_tools)
        result1 = await adapter.fetch_and_normalize(
            url=f"file://{config.plugin_dir}",
            mcp_config=config,
        )

        # Second fetch with fewer tools
        mock_transport.list_tools = AsyncMock(return_value=sample_mcp_tools[:1])
        result2 = await adapter.fetch_and_normalize(
            url=f"file://{config.plugin_dir}",
            mcp_config=config,
        )

        assert result1.inventory_hash != result2.inventory_hash


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================


class TestMcpToolDiscoveryErrors:
    """Integration tests for MCP tool discovery error handling."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_missing_mcp_config_returns_failure(self) -> None:
        """Test that missing mcp_config returns a failure result."""
        adapter = McpSourceAdapter()

        result = await adapter.fetch_and_normalize(
            url="file:///app/plugins/test-mcp",
            mcp_config=None,
        )

        assert result.success is False
        assert result.error is not None
        assert "mcp_config" in result.error.lower()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_missing_env_vars_returns_failure(
        self,
        mock_transport_factory: MagicMock,
    ) -> None:
        """Test that missing required env vars returns a failure."""
        mock_resolver = MagicMock(spec=McpEnvironmentResolver)
        mock_resolver.resolve = MagicMock(
            return_value=ResolutionResult(
                resolved={},
                missing=["CML_URL", "CML_TOKEN"],
                warnings=[],
            )
        )

        adapter = McpSourceAdapter(
            transport_factory=mock_transport_factory,
            env_resolver=mock_resolver,
        )

        config = McpSourceConfigFactory.create_with_env_vars()
        result = await adapter.fetch_and_normalize(
            url=f"file://{config.plugin_dir}",
            mcp_config=config,
        )

        assert result.success is False
        assert result.error is not None
        assert "environment" in result.error.lower() or "missing" in result.error.lower()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_transport_error_returns_failure(
        self,
        mock_transport_factory: MagicMock,
        mock_env_resolver: MagicMock,
    ) -> None:
        """Test that transport errors are handled gracefully."""
        from infrastructure.mcp import McpTransportError

        mock_transport_factory.get_transport = AsyncMock(side_effect=McpTransportError("Connection refused"))

        adapter = McpSourceAdapter(
            transport_factory=mock_transport_factory,
            env_resolver=mock_env_resolver,
        )

        config = McpSourceConfigFactory.create_resolved()
        result = await adapter.fetch_and_normalize(
            url=f"file://{config.plugin_dir}",
            mcp_config=config,
        )

        assert result.success is False


# ============================================================================
# TOOL CONVERSION TESTS
# ============================================================================


class TestMcpToolConversion:
    """Integration tests for MCP tool to ToolDefinition conversion."""

    @pytest.mark.integration
    def test_convert_mcp_tool_with_required_params(self) -> None:
        """Test converting an MCP tool with required parameters."""
        adapter = McpSourceAdapter()
        config = McpSourceConfigFactory.create()

        mcp_tool = McpToolDefinition(
            name="test_tool",
            description="A test tool",
            input_schema={
                "type": "object",
                "properties": {
                    "required_param": {"type": "string"},
                    "optional_param": {"type": "integer"},
                },
                "required": ["required_param"],
            },
        )

        tool_def = adapter._convert_mcp_tool(mcp_tool, config)

        assert tool_def.name == "test_tool"
        assert tool_def.description == "A test tool"
        assert "required_param" in tool_def.input_schema.get("properties", {})
        assert tool_def.input_schema.get("required") == ["required_param"]

    @pytest.mark.integration
    def test_convert_mcp_tool_without_input_schema(self) -> None:
        """Test converting an MCP tool without input schema."""
        adapter = McpSourceAdapter()
        config = McpSourceConfigFactory.create()

        mcp_tool = McpToolDefinition(
            name="no_params_tool",
            description="A tool with no parameters",
            input_schema={},
        )

        tool_def = adapter._convert_mcp_tool(mcp_tool, config)

        assert tool_def.name == "no_params_tool"
        assert tool_def.input_schema == {}

    @pytest.mark.integration
    def test_convert_mcp_tool_sets_source_path(self) -> None:
        """Test that converted tool has correct source_path."""
        adapter = McpSourceAdapter()
        config = McpSourceConfigFactory.create(plugin_dir="/app/plugins/cml-mcp")

        mcp_tool = McpToolDefinition(
            name="test_tool",
            description="A test tool",
            input_schema={},
        )

        tool_def = adapter._convert_mcp_tool(mcp_tool, config)

        assert "cml-mcp" in tool_def.source_path or "/app/plugins" in tool_def.source_path
