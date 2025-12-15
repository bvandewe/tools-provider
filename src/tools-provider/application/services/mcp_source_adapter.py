"""MCP Source Adapter for discovering tools from MCP plugins.

This adapter connects to MCP servers via the transport layer and
converts MCP tool schemas to normalized ToolDefinition objects.

Unlike OpenAPI adapters that parse static specs, MCP adapters
actively communicate with running MCP servers to discover tools.
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

from domain.enums import ExecutionMode, SourceType
from domain.models import ExecutionProfile, McpSourceConfig, ToolDefinition
from domain.models.mcp_manifest import McpManifest
from infrastructure.mcp import (
    HttpTransport,
    McpEnvironmentResolver,
    McpTransportError,
    StdioTransport,
    TransportFactory,
)

from .source_adapter import IngestionResult, SourceAdapter

logger = logging.getLogger(__name__)


class McpSourceAdapter(SourceAdapter):
    """Adapter for discovering tools from MCP plugin servers.

    This adapter:
    1. Spawns or connects to an MCP server process
    2. Performs the MCP initialization handshake
    3. Lists available tools via tools/list
    4. Converts MCP tool schemas to ToolDefinitions
    5. Disconnects from the server

    Unlike OpenAPI adapters which parse static specs, MCP adapters
    actively communicate with running servers.
    """

    def __init__(
        self,
        transport_factory: TransportFactory | None = None,
        env_resolver: McpEnvironmentResolver | None = None,
    ):
        """Initialize the MCP adapter.

        Args:
            transport_factory: Factory for creating MCP transports.
                              If None, creates transports directly.
            env_resolver: Resolver for MCP environment variables.
        """
        self._transport_factory = transport_factory
        self._env_resolver = env_resolver or McpEnvironmentResolver()

    @property
    def source_type(self) -> SourceType:
        """Return the type of source this adapter handles."""
        return SourceType.MCP

    async def fetch_and_normalize(
        self,
        url: str,
        auth_config: Any | None = None,
        default_audience: str | None = None,
        mcp_config: McpSourceConfig | None = None,
    ) -> IngestionResult:
        """Connect to MCP server and discover available tools.

        For MCP sources, the 'url' parameter is the path to the plugin
        directory containing server.json. The actual tool discovery
        happens via the MCP protocol, not HTTP fetching.

        Args:
            url: Path to MCP plugin directory (file:// prefix or absolute path)
            auth_config: Unused for MCP (env vars handle auth)
            default_audience: Unused for MCP
            mcp_config: MCP-specific configuration (required)

        Returns:
            IngestionResult with discovered tools or error information
        """
        if not mcp_config:
            return IngestionResult.failure("mcp_config is required for MCP sources")

        # Log appropriate message based on local vs remote
        if mcp_config.is_remote:
            logger.info(f"Discovering tools from remote MCP server: {mcp_config.server_url}")
        else:
            logger.info(f"Discovering tools from MCP plugin: {mcp_config.plugin_dir}")
        warnings: list[str] = []

        try:
            # Resolve environment variables
            env_result = self._env_resolver.resolve(mcp_config)
            if not env_result.is_complete:
                return IngestionResult.failure(f"Missing required environment variables: {env_result.missing}")
            if env_result.warnings:
                warnings.extend(env_result.warnings)

            # Create config with resolved environment
            resolved_config = McpSourceConfig(
                manifest_path=mcp_config.manifest_path,
                plugin_dir=mcp_config.plugin_dir,
                transport_type=mcp_config.transport_type,
                lifecycle_mode=mcp_config.lifecycle_mode,
                runtime_hint=mcp_config.runtime_hint,
                command=mcp_config.command,
                environment=env_result.resolved,
                env_definitions=mcp_config.env_definitions,
                server_url=mcp_config.server_url,  # Preserve server_url for remote servers
            )

            # Get transport based on local vs remote MCP server
            if resolved_config.is_remote:
                # Remote MCP server - use HTTP transport
                # Convert env vars with MCP_HEADER_ prefix to HTTP headers
                # e.g., MCP_HEADER_X_AUTHORIZATION -> X-Authorization
                http_headers = {}
                for key, value in env_result.resolved.items():
                    if key.startswith("MCP_HEADER_"):
                        header_name = key[11:].replace("_", "-")  # Strip prefix, convert underscores to dashes
                        http_headers[header_name] = value

                # server_url is guaranteed to be set when is_remote is True
                transport = HttpTransport(
                    server_url=resolved_config.server_url,  # type: ignore[arg-type]
                    timeout=30.0,
                    headers=http_headers,
                )
                await transport.connect()
                should_disconnect = True
            elif self._transport_factory:
                # Local plugin with factory
                transport = await self._transport_factory.get_transport(resolved_config)
                should_disconnect = resolved_config.lifecycle_mode.value == "transient"
            else:
                # Local plugin without factory - use stdio directly
                transport = StdioTransport(
                    command=list(resolved_config.command),
                    environment=env_result.resolved,
                    cwd=resolved_config.plugin_dir,
                )
                await transport.connect()
                should_disconnect = True

            try:
                # Discover tools via MCP protocol
                mcp_tools = await transport.list_tools()
                logger.info(f"Discovered {len(mcp_tools)} tools from MCP server")

                # Convert to ToolDefinitions
                tools = [self._convert_mcp_tool(tool, mcp_config) for tool in mcp_tools]

                # Compute inventory hash
                inventory_hash = self._compute_inventory_hash(tools)

                # Get version from manifest if available (local plugins only)
                source_version = None
                if not mcp_config.is_remote and mcp_config.manifest_path:
                    try:
                        manifest = McpManifest.parse(mcp_config.manifest_path)
                        source_version = manifest.version
                    except Exception:  # noqa: S110  # nosec B110
                        pass  # Version extraction is best-effort

                return IngestionResult(
                    tools=tools,
                    inventory_hash=inventory_hash,
                    success=True,
                    source_version=source_version,
                    warnings=warnings,
                )

            finally:
                if should_disconnect:
                    await transport.disconnect()

        except McpTransportError as e:
            logger.error(f"MCP transport error during discovery: {e}")
            return IngestionResult.failure(f"MCP transport error: {e}")
        except Exception as e:
            logger.exception(f"Unexpected error during MCP tool discovery: {e}")
            return IngestionResult.failure(f"Tool discovery failed: {e}")

    async def validate_url(self, url: str, auth_config: Any | None = None) -> bool:
        """Validate that a path points to a valid MCP plugin.

        For MCP sources, validates that:
        1. The path exists
        2. Contains a valid server.json manifest
        3. The manifest can be parsed

        Args:
            url: Path to MCP plugin directory
            auth_config: Unused for MCP

        Returns:
            True if path contains valid MCP plugin
        """
        try:
            # Strip file:// prefix if present
            plugin_path = url
            if plugin_path.startswith("file://"):
                plugin_path = plugin_path[7:]

            plugin_dir = Path(plugin_path)
            if not plugin_dir.exists():
                logger.warning(f"MCP plugin directory not found: {plugin_dir}")
                return False

            manifest_path = plugin_dir / "server.json"
            if not manifest_path.exists():
                logger.warning(f"MCP manifest not found: {manifest_path}")
                return False

            # Try to parse the manifest
            McpManifest.parse(manifest_path)
            return True

        except Exception as e:
            logger.warning(f"MCP plugin validation failed: {e}")
            return False

    def _convert_mcp_tool(
        self,
        mcp_tool: Any,
        config: McpSourceConfig,
    ) -> ToolDefinition:
        """Convert MCP tool schema to ToolDefinition.

        Args:
            mcp_tool: Tool definition from MCP tools/list response
            config: MCP source configuration

        Returns:
            Normalized ToolDefinition
        """
        # MCP tool definitions use McpToolDefinition dataclass from infrastructure
        # but may also come as dicts from the transport layer
        if hasattr(mcp_tool, "name"):
            # McpToolDefinition object
            name = mcp_tool.name
            description = mcp_tool.description or ""
            input_schema = mcp_tool.input_schema or {}
        else:
            # Dict from raw response
            name = mcp_tool.get("name", "")
            description = mcp_tool.get("description", "")
            input_schema = mcp_tool.get("inputSchema", {})

        # Create execution profile for MCP_CALL mode
        execution_profile = ExecutionProfile(
            mode=ExecutionMode.MCP_CALL,
            method="MCP",  # Not HTTP, but field is required
            url_template=f"mcp://{name}",  # MCP protocol pseudo-URL
            content_type="application/json",
        )

        return ToolDefinition(
            name=name,
            description=description,
            input_schema=input_schema,
            execution_profile=execution_profile,
            source_path=f"mcp://{config.plugin_dir}#{name}",
            tags=["mcp"],
        )

    def _compute_inventory_hash(self, tools: list[ToolDefinition]) -> str:
        """Compute a hash of all tools for change detection.

        Args:
            tools: List of discovered tools

        Returns:
            SHA256 hash of the tool inventory
        """
        # Sort tools by name for deterministic hashing
        sorted_tools = sorted(tools, key=lambda t: t.name)

        # Create a stable JSON representation
        inventory_data = [tool.to_dict() for tool in sorted_tools]
        content = json.dumps(inventory_data, sort_keys=True)

        return hashlib.sha256(content.encode()).hexdigest()[:16]
