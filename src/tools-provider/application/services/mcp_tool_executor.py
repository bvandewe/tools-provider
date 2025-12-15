"""MCP Tool Executor for executing tools via MCP protocol.

This executor handles tool execution for tools with ExecutionMode.MCP_CALL.
It connects to MCP servers and invokes tools via the MCP protocol.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from opentelemetry import trace

from domain.models import McpSourceConfig, ToolDefinition
from infrastructure.mcp import (
    McpConnectionError,
    McpEnvironmentResolver,
    McpProtocolError,
    McpTimeoutError,
    McpTransportError,
    TransportFactory,
)

if TYPE_CHECKING:
    from neuroglia.hosting.web import WebApplicationBuilder

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


@dataclass
class McpExecutionResult:
    """Result of an MCP tool execution.

    Attributes:
        success: Whether the execution succeeded
        content: Content returned by the tool (text, images, etc.)
        is_error: Whether the tool indicated an error in its response
        error: Error message if execution failed
        execution_time_ms: Time taken for execution
        metadata: Additional execution metadata
    """

    success: bool
    content: list[dict[str, Any]]
    is_error: bool = False
    error: str | None = None
    execution_time_ms: float = 0.0
    metadata: dict[str, Any] | None = None

    def get_text(self) -> str:
        """Get combined text from all text content blocks."""
        texts = []
        for item in self.content:
            if item.get("type") == "text":
                texts.append(item.get("text", ""))
        return "\n".join(texts)


class McpToolExecutor:
    """Executor for MCP-based tool calls.

    This executor manages the lifecycle of MCP tool execution:
    1. Gets or creates an MCP transport for the source
    2. Calls the tool via the MCP protocol
    3. Converts the result to a standard format
    4. Handles errors and timeouts

    Usage:
        executor = McpToolExecutor(transport_factory, env_resolver)
        result = await executor.execute(
            tool_id="mcp-source:tool_name",
            definition=tool_definition,
            arguments={"param": "value"},
            mcp_config=source_config,
        )
    """

    def __init__(
        self,
        transport_factory: TransportFactory,
        env_resolver: McpEnvironmentResolver | None = None,
        default_timeout: float = 30.0,
    ):
        """Initialize the MCP tool executor.

        Args:
            transport_factory: Factory for creating/pooling MCP transports
            env_resolver: Resolver for environment variables
            default_timeout: Default timeout for tool execution (seconds)
        """
        self._transport_factory = transport_factory
        self._env_resolver = env_resolver or McpEnvironmentResolver()
        self._default_timeout = default_timeout

    async def execute(
        self,
        tool_id: str,
        definition: ToolDefinition,
        arguments: dict[str, Any],
        mcp_config: McpSourceConfig,
        source_id: str | None = None,
        timeout: float | None = None,
    ) -> McpExecutionResult:
        """Execute a tool via MCP protocol.

        Args:
            tool_id: Unique tool identifier (for logging/tracing)
            definition: Tool definition with execution profile
            arguments: Arguments to pass to the tool
            mcp_config: MCP source configuration
            source_id: Optional source ID for transport pooling
            timeout: Optional timeout override (seconds)

        Returns:
            McpExecutionResult with tool output or error

        Note:
            This method does not raise exceptions for execution failures.
            Instead, it returns a McpExecutionResult with success=False.
        """
        start_time = time.time()
        effective_timeout = timeout or self._default_timeout

        with tracer.start_as_current_span("mcp_execute_tool") as span:
            span.set_attribute("tool.id", tool_id)
            span.set_attribute("tool.name", definition.name)
            span.set_attribute("mcp.transport", mcp_config.transport_type.value)
            span.set_attribute("mcp.is_remote", mcp_config.is_remote)

            if mcp_config.is_remote:
                span.set_attribute("mcp.server_url", mcp_config.server_url or "")
            else:
                span.set_attribute("mcp.plugin_dir", mcp_config.plugin_dir)

            try:
                # For local plugins, resolve environment variables
                # Remote servers don't need local env resolution
                resolved_config: McpSourceConfig
                if mcp_config.is_remote:
                    resolved_config = mcp_config
                else:
                    env_result = self._env_resolver.resolve(mcp_config)
                    if not env_result.is_complete:
                        execution_time_ms = (time.time() - start_time) * 1000
                        error_msg = f"Missing environment variables: {env_result.missing}"
                        logger.error(f"MCP execution failed: {error_msg}")
                        span.set_attribute("mcp.error", error_msg)
                        return McpExecutionResult(
                            success=False,
                            content=[],
                            error=error_msg,
                            execution_time_ms=execution_time_ms,
                        )

                    # Create resolved config with environment
                    resolved_config = McpSourceConfig(
                        manifest_path=mcp_config.manifest_path,
                        plugin_dir=mcp_config.plugin_dir,
                        transport_type=mcp_config.transport_type,
                        lifecycle_mode=mcp_config.lifecycle_mode,
                        runtime_hint=mcp_config.runtime_hint,
                        command=mcp_config.command,
                        environment=env_result.resolved,
                        env_definitions=mcp_config.env_definitions,
                        server_url=mcp_config.server_url,
                    )

                # Get transport from factory
                span.add_event("Getting MCP transport")
                transport = await self._transport_factory.get_transport(
                    resolved_config,
                    source_id=source_id,
                )

                # Ensure connected (factory handles this for singletons)
                if not transport.is_connected:
                    span.add_event("Connecting to MCP server")
                    await transport.connect()

                # Execute the tool
                span.add_event(
                    "Calling MCP tool",
                    {
                        "tool_name": definition.name,
                        "arguments": str(arguments)[:200],  # Truncate for span
                    },
                )

                logger.debug(f"Calling MCP tool '{definition.name}' with arguments: {arguments}")

                result = await transport.call_tool(
                    tool_name=definition.name,
                    arguments=arguments,
                    timeout=effective_timeout,
                )

                execution_time_ms = (time.time() - start_time) * 1000

                # Convert result to response format
                content = [c.to_dict() for c in result.content]

                span.set_attribute("mcp.execution_time_ms", execution_time_ms)
                span.set_attribute("mcp.content_count", len(content))
                span.set_attribute("mcp.is_error", result.is_error)

                logger.info(f"MCP tool '{definition.name}' executed successfully ({len(content)} content blocks, {execution_time_ms:.2f}ms)")

                return McpExecutionResult(
                    success=True,
                    content=content,
                    is_error=result.is_error,
                    execution_time_ms=execution_time_ms,
                    metadata={
                        "source_id": source_id,
                        "plugin_dir": mcp_config.plugin_dir,
                    },
                )

            except McpTimeoutError as e:
                execution_time_ms = (time.time() - start_time) * 1000
                error_msg = f"Tool execution timed out after {effective_timeout}s: {e}"
                logger.error(error_msg)
                span.set_attribute("mcp.error", "timeout")
                return McpExecutionResult(
                    success=False,
                    content=[],
                    error=error_msg,
                    execution_time_ms=execution_time_ms,
                )

            except McpConnectionError as e:
                execution_time_ms = (time.time() - start_time) * 1000
                error_msg = f"MCP connection error: {e}"
                logger.error(error_msg)
                span.set_attribute("mcp.error", "connection_error")
                return McpExecutionResult(
                    success=False,
                    content=[],
                    error=error_msg,
                    execution_time_ms=execution_time_ms,
                )

            except McpProtocolError as e:
                execution_time_ms = (time.time() - start_time) * 1000
                error_msg = f"MCP protocol error: {e}"
                logger.error(error_msg)
                span.set_attribute("mcp.error", "protocol_error")
                return McpExecutionResult(
                    success=False,
                    content=[],
                    error=error_msg,
                    execution_time_ms=execution_time_ms,
                )

            except McpTransportError as e:
                execution_time_ms = (time.time() - start_time) * 1000
                error_msg = f"MCP transport error: {e}"
                logger.error(error_msg)
                span.set_attribute("mcp.error", "transport_error")
                return McpExecutionResult(
                    success=False,
                    content=[],
                    error=error_msg,
                    execution_time_ms=execution_time_ms,
                )

            except Exception as e:
                execution_time_ms = (time.time() - start_time) * 1000
                error_msg = f"Unexpected error during MCP execution: {e}"
                logger.exception(error_msg)
                span.set_attribute("mcp.error", "internal_error")
                return McpExecutionResult(
                    success=False,
                    content=[],
                    error=error_msg,
                    execution_time_ms=execution_time_ms,
                )

    async def health_check(self, mcp_config: McpSourceConfig) -> bool:
        """Check if an MCP plugin is healthy and responding.

        Attempts to connect and list tools to verify the plugin is working.

        Args:
            mcp_config: MCP source configuration

        Returns:
            True if plugin is healthy, False otherwise
        """
        try:
            # Resolve environment
            env_result = self._env_resolver.resolve(mcp_config)
            if not env_result.is_complete:
                return False

            resolved_config = McpSourceConfig(
                manifest_path=mcp_config.manifest_path,
                plugin_dir=mcp_config.plugin_dir,
                transport_type=mcp_config.transport_type,
                lifecycle_mode=mcp_config.lifecycle_mode,
                runtime_hint=mcp_config.runtime_hint,
                command=mcp_config.command,
                environment=env_result.resolved,
                env_definitions=mcp_config.env_definitions,
            )

            # Get transport and try to list tools
            transport = await self._transport_factory.get_transport(resolved_config)
            if not transport.is_connected:
                await transport.connect()

            # List tools as a health check
            await transport.list_tools()
            return True

        except Exception as e:
            logger.warning(f"MCP health check failed: {e}")
            return False

    # =========================================================================
    # CONFIGURATION
    # =========================================================================

    @staticmethod
    def configure(builder: WebApplicationBuilder) -> WebApplicationBuilder:
        """Configure and register the MCP tool executor service.

        This method follows the Neuroglia pattern for service configuration,
        creating a singleton instance and registering it in the DI container.

        Args:
            builder: WebApplicationBuilder instance for service registration

        Returns:
            The builder instance for fluent chaining
        """
        logger.info("🔧 Configuring McpToolExecutor...")

        # Create the transport factory and environment resolver
        transport_factory = TransportFactory()
        env_resolver = McpEnvironmentResolver()

        # Create the executor instance
        mcp_tool_executor = McpToolExecutor(
            transport_factory=transport_factory,
            env_resolver=env_resolver,
            default_timeout=30.0,
        )

        # Register as singleton
        builder.services.add_singleton(McpToolExecutor, singleton=mcp_tool_executor)
        logger.info("✅ McpToolExecutor configured")

        return builder
