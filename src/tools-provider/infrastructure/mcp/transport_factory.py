"""MCP Transport Factory.

Creates and manages MCP transport instances based on configuration.
Supports transport pooling for singleton lifecycle mode.
"""

import asyncio
import logging
from typing import Any

from domain.enums import McpTransportType, PluginLifecycleMode
from domain.models import McpSourceConfig

from .env_resolver import McpEnvironmentResolver
from .http_transport import HttpTransport
from .stdio_transport import StdioTransport
from .transport import IMcpTransport, McpConnectionError

logger = logging.getLogger(__name__)


class TransportFactory:
    """Factory for creating and managing MCP transport instances.

    Handles transport creation based on McpSourceConfig and manages
    transport lifecycle (transient vs singleton).

    For singleton mode, maintains a pool of connected transports that
    are reused across requests. For transient mode, creates a new
    transport for each request.

    Usage:
        factory = TransportFactory(env_resolver)

        # Get a transport (may be new or pooled)
        async with await factory.get_transport(config) as transport:
            tools = await transport.list_tools()

        # For singleton mode, release when done
        await factory.release_transport(config)

        # Cleanup all transports
        await factory.close_all()
    """

    def __init__(
        self,
        env_resolver: McpEnvironmentResolver | None = None,
        default_timeout: float = 30.0,
    ):
        """Initialize the transport factory.

        Args:
            env_resolver: Resolver for environment variables.
                         If None, environment is used as-is from config.
            default_timeout: Default timeout for transport operations.
        """
        self._env_resolver = env_resolver
        self._default_timeout = default_timeout

        # Pool of singleton transports: {source_id: transport}
        self._singleton_pool: dict[str, IMcpTransport] = {}
        self._pool_lock = asyncio.Lock()

    async def get_transport(
        self,
        config: McpSourceConfig,
        source_id: str | None = None,
    ) -> IMcpTransport:
        """Get a transport for the given configuration.

        For TRANSIENT lifecycle: Creates a new transport (caller must connect)
        For SINGLETON lifecycle: Returns pooled transport or creates new one

        Args:
            config: MCP source configuration
            source_id: Optional source ID for pooling key (uses manifest_path if None)

        Returns:
            IMcpTransport instance (may or may not be connected)

        Raises:
            McpConnectionError: If transport creation fails
            ValueError: If transport type is not supported
        """
        pool_key = source_id or config.manifest_path

        if config.lifecycle_mode == PluginLifecycleMode.SINGLETON:
            return await self._get_singleton_transport(config, pool_key)
        else:
            return self._create_transport(config)

    async def _get_singleton_transport(
        self,
        config: McpSourceConfig,
        pool_key: str,
    ) -> IMcpTransport:
        """Get or create a singleton transport from the pool.

        Singleton transports are kept alive and reused across requests.
        """
        async with self._pool_lock:
            # Check if we have a connected transport
            if pool_key in self._singleton_pool:
                transport = self._singleton_pool[pool_key]
                if transport.is_connected:
                    logger.debug(f"Reusing pooled transport for {pool_key}")
                    return transport
                else:
                    # Transport died, remove from pool
                    logger.warning(f"Pooled transport for {pool_key} is disconnected, recreating")
                    del self._singleton_pool[pool_key]

            # Create and connect new transport
            transport = self._create_transport(config)
            try:
                await transport.connect()
                self._singleton_pool[pool_key] = transport
                logger.info(f"Created new pooled transport for {pool_key}")
                return transport
            except Exception as e:
                await transport.disconnect()
                raise McpConnectionError(f"Failed to connect singleton transport: {e}", e) from e

    def _create_transport(self, config: McpSourceConfig) -> IMcpTransport:
        """Create a new transport instance based on configuration.

        Args:
            config: MCP source configuration

        Returns:
            New transport instance (not connected)

        Raises:
            ValueError: If transport type is not supported
        """
        # Resolve environment variables if resolver available
        environment = dict(config.environment)
        if self._env_resolver and config.env_definitions:
            try:
                result = self._env_resolver.resolve(config)
                environment.update(result.resolved)
                if result.missing:
                    logger.warning(f"Missing environment variables: {result.missing}")
            except Exception as e:
                logger.warning(f"Failed to resolve some environment variables: {e}")

        if config.transport_type == McpTransportType.STDIO:
            return StdioTransport(
                command=list(config.command),
                environment=environment,
                cwd=config.plugin_dir,
                timeout=self._default_timeout,
            )
        elif config.transport_type == McpTransportType.STREAMABLE_HTTP:
            if not config.server_url:
                raise ValueError("STREAMABLE_HTTP transport requires server_url in config")

            # Convert MCP_HEADER_* env vars to HTTP headers
            # e.g., MCP_HEADER_X_AUTHORIZATION -> X-Authorization
            headers: dict[str, str] = {}
            for key, value in environment.items():
                if key.startswith("MCP_HEADER_"):
                    # Remove prefix and convert underscores to hyphens for header name
                    header_name = key[len("MCP_HEADER_") :].replace("_", "-")
                    headers[header_name] = value

            logger.debug(f"Creating HttpTransport for {config.server_url} with headers: {list(headers.keys())}")
            return HttpTransport(
                server_url=config.server_url,
                timeout=self._default_timeout,
                headers=headers if headers else None,
            )
        elif config.transport_type == McpTransportType.SSE:
            # SSE transport not yet implemented
            raise ValueError("SSE transport not yet implemented. Use STDIO transport.")
        else:
            raise ValueError(f"Unsupported transport type: {config.transport_type}")

    async def release_transport(
        self,
        source_id: str,
        force: bool = False,
    ) -> None:
        """Release a singleton transport from the pool.

        Args:
            source_id: Source ID or pool key for the transport
            force: If True, disconnect even if transport is healthy
        """
        async with self._pool_lock:
            if source_id in self._singleton_pool:
                transport = self._singleton_pool[source_id]
                if force or not transport.is_connected:
                    await transport.disconnect()
                    del self._singleton_pool[source_id]
                    logger.debug(f"Released transport for {source_id}")

    async def close_all(self) -> None:
        """Close all pooled transports.

        Should be called during application shutdown.
        """
        async with self._pool_lock:
            for pool_key, transport in list(self._singleton_pool.items()):
                try:
                    await transport.disconnect()
                    logger.debug(f"Closed transport for {pool_key}")
                except Exception as e:
                    logger.warning(f"Error closing transport for {pool_key}: {e}")

            self._singleton_pool.clear()
            logger.info("All MCP transports closed")

    @property
    def active_transports(self) -> int:
        """Get number of active pooled transports."""
        return len(self._singleton_pool)

    def get_pool_status(self) -> dict[str, Any]:
        """Get status of the transport pool.

        Returns:
            Dictionary with pool statistics
        """
        return {
            "active_transports": len(self._singleton_pool),
            "transports": {
                key: {
                    "connected": transport.is_connected,
                    "server": transport.server_info.name if transport.server_info else None,
                }
                for key, transport in self._singleton_pool.items()
            },
        }

    async def __aenter__(self) -> "TransportFactory":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit - closes all transports."""
        await self.close_all()
