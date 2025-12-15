"""Execute tool command with handler.

This command executes a tool on behalf of an authenticated agent,
handling token exchange, request proxying, and response processing.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, cast

from neuroglia.core import OperationResult
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_bus import CloudEventBus
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import CloudEventPublishingOptions
from neuroglia.mapping import Mapper
from neuroglia.mediation import Command, CommandHandler, Mediator
from neuroglia.observability.tracing import add_span_attributes
from observability import token_exchange_count, token_exchange_errors, tool_execution_count, tool_execution_errors, tool_execution_time
from opentelemetry import trace

from application.commands.command_handler_base import CommandHandlerBase
from application.services.mcp_tool_executor import McpToolExecutor
from application.services.tool_executor import ToolExecutionError, ToolExecutor
from domain.enums import AuthMode, ExecutionMode
from domain.models import McpSourceConfig, ToolDefinition
from domain.repositories import SourceDtoRepository, SourceToolDtoRepository
from infrastructure.secrets import SourceSecretsStore
from integration.models.source_dto import SourceDto
from integration.models.source_tool_dto import SourceToolDto

log = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


@dataclass
class ExecuteToolCommand(Command[OperationResult[dict[str, Any]]]):
    """Command to execute a tool on behalf of an agent.

    This command:
    1. Validates the agent has access to the tool
    2. Loads the tool definition
    3. Validates arguments against the tool's JSON schema
    4. Exchanges the agent's token for an upstream service token
    5. Executes the tool and returns the result
    """

    tool_id: str
    """ID of the tool to execute (format: source_id:operation_id)."""

    arguments: dict[str, Any] = field(default_factory=dict)
    """Arguments to pass to the tool."""

    agent_token: str = ""
    """The agent's JWT access token for identity propagation."""

    validate_schema: bool | None = None
    """Override schema validation setting (None = use tool's setting)."""

    user_info: dict[str, Any] | None = None
    """User information from authentication context."""


@dataclass
class ExecuteToolResult:
    """Result of tool execution for API response.

    Attributes:
        tool_id: ID of the executed tool
        status: Execution status (completed, failed, pending)
        result: Tool execution result data
        error: Error information if failed
        execution_time_ms: Total execution time
        upstream_status: HTTP status from upstream service
    """

    tool_id: str
    status: str
    result: Any | None = None
    error: dict[str, Any] | None = None
    execution_time_ms: float = 0.0
    upstream_status: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "tool_id": self.tool_id,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "upstream_status": self.upstream_status,
        }


class ExecuteToolCommandHandler(
    CommandHandlerBase,
    CommandHandler[ExecuteToolCommand, OperationResult[dict[str, Any]]],
):
    """Handler for executing tools via the proxy.

    This handler:
    1. Loads the tool definition from the read model
    2. Validates the agent has access to the tool
    3. Delegates execution to ToolExecutor or McpToolExecutor based on mode
    4. Returns the result as an OperationResult

    Note: Access validation should be done at the controller level
    before invoking this command.
    """

    def __init__(
        self,
        mediator: Mediator,
        mapper: Mapper,
        cloud_event_bus: CloudEventBus,
        cloud_event_publishing_options: CloudEventPublishingOptions,
        tool_repository: SourceToolDtoRepository,
        tool_executor: ToolExecutor,
        source_dto_repository: SourceDtoRepository,
        source_secrets_store: SourceSecretsStore,
        mcp_tool_executor: McpToolExecutor,
    ):
        super().__init__(
            mediator,
            mapper,
            cloud_event_bus,
            cloud_event_publishing_options,
        )
        self._tool_repository = tool_repository
        self._tool_executor = tool_executor
        self._source_dto_repository = source_dto_repository
        self._secrets_store = source_secrets_store
        self._mcp_tool_executor = mcp_tool_executor

    async def handle_async(self, request: ExecuteToolCommand) -> OperationResult[dict[str, Any]]:
        """Handle the execute tool command."""
        command = request
        start_time = time.time()

        # Add tracing context (only include non-None values for OpenTelemetry compatibility)
        span_attributes: dict[str, str | bool | int | float] = {
            "tool.id": command.tool_id,
            "tool.has_arguments": bool(command.arguments),
        }
        if command.validate_schema is not None:
            span_attributes["tool.validate_schema"] = command.validate_schema
        add_span_attributes(span_attributes)

        with tracer.start_as_current_span("execute_tool_command") as span:
            # Record execution attempt
            tool_execution_count.add(1, {"tool_id": command.tool_id})

            # Step 1: Load tool definition
            span.add_event("Loading tool definition")
            log.debug(f"Loading tool from repository: tool_id={command.tool_id}")
            tool_dto = await self._tool_repository.get_async(command.tool_id)
            log.debug(f"Tool lookup result: tool_dto={tool_dto is not None}")

            if not tool_dto:
                log.warning(f"Tool not found: {command.tool_id}")
                tool_execution_errors.add(1, {"tool_id": command.tool_id, "error": "not_found"})
                return self.not_found(SourceToolDto, command.tool_id)

            if not tool_dto.is_enabled:
                log.warning(f"Tool is disabled: {command.tool_id}")
                tool_execution_errors.add(1, {"tool_id": command.tool_id, "error": "disabled"})
                return self.bad_request(f"Tool '{command.tool_id}' is disabled")

            log.debug(f"Tool is enabled, checking definition: has_definition={tool_dto.definition is not None}")

            # Step 2: Parse tool definition
            if not tool_dto.definition:
                log.error(f"Tool has no definition: {command.tool_id}")
                tool_execution_errors.add(1, {"tool_id": command.tool_id, "error": "no_definition"})
                return self.internal_server_error(f"Tool '{command.tool_id}' has no execution definition")

            log.debug(f"Parsing tool definition, type={type(tool_dto.definition).__name__}")
            try:
                if isinstance(tool_dto.definition, dict):
                    definition = ToolDefinition.from_dict(tool_dto.definition)
                else:
                    definition = tool_dto.definition
                log.debug(f"Tool definition parsed: mode={definition.execution_profile.mode.value}")
            except Exception as e:
                log.error(f"Failed to parse tool definition for {command.tool_id}: {e}")
                tool_execution_errors.add(1, {"tool_id": command.tool_id, "error": "invalid_definition"})
                return self.internal_server_error(f"Invalid tool definition: {e}")

            span.set_attribute("tool.name", definition.name)
            span.set_attribute("tool.source_path", definition.source_path)
            span.set_attribute("tool.execution_mode", definition.execution_profile.mode.value)

            # Step 3.5: Load source from read model for auth mode and audience
            log.debug(f"Loading source: source_id={tool_dto.source_id}")
            source_dto = await self._source_dto_repository.get_async(tool_dto.source_id)
            log.debug(f"Source lookup result: source_dto={source_dto is not None}")
            if not source_dto:
                log.error(f"Source not found for tool {command.tool_id}: {tool_dto.source_id}")
                tool_execution_errors.add(1, {"tool_id": command.tool_id, "error": "source_not_found"})
                return self.internal_server_error(f"Source '{tool_dto.source_id}' not found for tool")

            # Get auth mode from source, but credentials from file-based secrets store
            # Credentials are NOT stored in MongoDB/EventStore - they come from a gitignored YAML file
            # that is mounted as a Kubernetes secret in production
            auth_mode = source_dto.auth_mode
            auth_config = self._secrets_store.get_auth_config(tool_dto.source_id)
            default_audience = source_dto.default_audience

            # Log if credentials are expected but not found
            if auth_mode in (AuthMode.HTTP_BASIC, AuthMode.API_KEY) and not auth_config:
                log.warning(
                    f"Source {tool_dto.source_id} uses {auth_mode.value} but no credentials found in secrets store. Add credentials to secrets/sources.yaml for source ID: {tool_dto.source_id}"
                )

            span.set_attribute("tool.auth_mode", auth_mode.value)

            # Step 4: Execute tool based on execution mode
            try:
                # Check if this is an MCP tool
                log.debug(f"Execution mode: {definition.execution_profile.mode.value}, checking for MCP_CALL")
                if definition.execution_profile.mode == ExecutionMode.MCP_CALL:
                    span.add_event("Executing MCP tool")
                    log.debug("Calling _execute_mcp_tool")
                    result = await self._execute_mcp_tool(
                        command=command,
                        definition=definition,
                        source_dto=source_dto,
                        span=span,
                        start_time=start_time,
                    )
                    if result is not None:
                        return result
                    # If result is None, fall through to standard execution
                    # (this shouldn't happen for properly configured MCP tools)

                # Standard HTTP-based execution
                span.add_event("Executing tool")
                token_exchange_count.add(1, {"audience": default_audience or "none"})

                result = await self._tool_executor.execute(
                    tool_id=command.tool_id,
                    definition=definition,
                    arguments=command.arguments,
                    agent_token=command.agent_token,
                    source_id=tool_dto.source_id,
                    auth_mode=auth_mode,
                    auth_config=auth_config,
                    default_audience=default_audience,
                    validate_schema=command.validate_schema,
                )

                # Record success metrics
                processing_time_ms = (time.time() - start_time) * 1000
                tool_execution_time.record(processing_time_ms, {"tool_id": command.tool_id, "status": result.status})

                span.set_attribute("tool.status", result.status)
                span.set_attribute("tool.upstream_status", result.upstream_status or 0)

                # Build response
                response = ExecuteToolResult(
                    tool_id=command.tool_id,
                    status=result.status,
                    result=result.result,
                    execution_time_ms=result.execution_time_ms,
                    upstream_status=result.upstream_status,
                )

                log.info(f"Tool execution completed: tool={command.tool_id}, status={result.status}, time={processing_time_ms:.2f}ms")

                return self.ok(response.to_dict())

            except ToolExecutionError as e:
                processing_time_ms = (time.time() - start_time) * 1000
                tool_execution_errors.add(1, {"tool_id": command.tool_id, "error": e.error_code})

                if e.error_code == "token_exchange_failed":
                    token_exchange_errors.add(1, {"error": e.details.get("exchange_error", "unknown")})

                span.set_attribute("tool.error", e.error_code)

                log.warning(f"Tool execution failed: tool={command.tool_id}, error={e.error_code}, message={e.message}")

                # Build error response
                response = ExecuteToolResult(
                    tool_id=command.tool_id,
                    status="failed",
                    error=e.to_dict(),
                    execution_time_ms=processing_time_ms,
                    upstream_status=e.upstream_status,
                )

                # Return appropriate HTTP status based on error type
                if e.error_code == "validation_error":
                    return self.bad_request_with_data(response.to_dict(), e.message)
                elif e.error_code == "token_exchange_failed":
                    return self.unauthorized_with_data(response.to_dict(), e.message)
                elif e.error_code in ("upstream_timeout", "upstream_connection_error"):
                    return self.service_unavailable_with_data(response.to_dict(), e.message)
                else:
                    return self.internal_error_with_data(response.to_dict(), e.message)

            except Exception as e:
                processing_time_ms = (time.time() - start_time) * 1000
                tool_execution_errors.add(1, {"tool_id": command.tool_id, "error": "unexpected"})

                span.set_attribute("tool.error", str(e))
                log.exception(f"Unexpected error executing tool {command.tool_id}")

                response = ExecuteToolResult(
                    tool_id=command.tool_id,
                    status="failed",
                    error={
                        "message": "An unexpected error occurred",
                        "error_code": "internal_error",
                    },
                    execution_time_ms=processing_time_ms,
                )

                return self.internal_error_with_data(response.to_dict(), str(e))

    async def _execute_mcp_tool(
        self,
        command: ExecuteToolCommand,
        source_dto: SourceDto,
        definition: ToolDefinition,
        span: trace.Span,
        start_time: float,
    ) -> OperationResult[dict[str, Any]]:
        """Execute a tool via MCP protocol.

        Args:
            command: The execute tool command
            source_dto: The source containing MCP configuration
            definition: The tool definition
            span: The tracing span
            start_time: When execution started

        Returns:
            OperationResult containing the execution result
        """
        log.debug(f"_execute_mcp_tool: mcp_tool_executor={self._mcp_tool_executor is not None}")
        if not self._mcp_tool_executor:
            log.error("MCP tool executor not configured")
            return self.internal_error_with_data(
                {"tool_id": command.tool_id, "status": "failed", "error": {"message": "MCP executor not configured", "error_code": "configuration_error"}},
                "MCP tool executor is not available",
            )

        log.debug(f"_execute_mcp_tool: source has mcp_config={source_dto.mcp_config is not None}")
        if not source_dto.mcp_config:
            return self.bad_request_with_data(
                {"tool_id": command.tool_id, "status": "failed", "error": {"message": "Source missing MCP configuration", "error_code": "configuration_error"}},
                f"Source {source_dto.id} does not have MCP configuration",
            )

        # Convert dict to McpSourceConfig if needed
        mcp_config: McpSourceConfig
        if isinstance(source_dto.mcp_config, dict):
            mcp_config = McpSourceConfig.from_dict(source_dto.mcp_config)
        else:
            mcp_config = source_dto.mcp_config

        span.set_attribute("mcp.plugin_dir", mcp_config.plugin_dir)
        span.set_attribute("mcp.transport_type", mcp_config.transport_type.value)

        # Execute via MCP
        mcp_result = await self._mcp_tool_executor.execute(
            tool_id=command.tool_id,
            definition=definition,
            arguments=command.arguments or {},
            mcp_config=mcp_config,
            source_id=str(source_dto.id),
            timeout=30.0,  # Default timeout for MCP tool execution
        )

        processing_time_ms = (time.time() - start_time) * 1000

        # Build response from MCP result
        if mcp_result.success and not mcp_result.is_error:
            span.set_attribute("tool.status", "success")
            tool_execution_count.add(1, {"tool_id": command.tool_id, "source_id": str(source_dto.id), "status": "success"})

            # Convert content list to result dict
            result_data: dict[str, Any] = {"content": mcp_result.content}
            if mcp_result.metadata:
                result_data["metadata"] = mcp_result.metadata

            response = ExecuteToolResult(
                tool_id=command.tool_id,
                status="success",
                result=result_data,
                execution_time_ms=processing_time_ms,
            )
            return self.ok(response.to_dict())
        else:
            span.set_attribute("tool.status", "failed")
            error_message = mcp_result.error or "MCP execution failed"
            span.set_attribute("tool.error", error_message)

            # Determine error type from metadata if available
            error_type = "mcp_error"
            if mcp_result.metadata:
                error_type = mcp_result.metadata.get("error_type", "mcp_error")

            tool_execution_errors.add(1, {"tool_id": command.tool_id, "error": error_type})

            response = ExecuteToolResult(
                tool_id=command.tool_id,
                status="failed",
                error={
                    "message": error_message,
                    "error_code": error_type,
                },
                execution_time_ms=processing_time_ms,
            )

            # Map MCP error types to HTTP status codes
            if error_type == "timeout":
                return self.service_unavailable_with_data(response.to_dict(), error_message)
            elif error_type == "connection_error":
                return self.service_unavailable_with_data(response.to_dict(), error_message)
            elif error_type in ("validation_error", "tool_not_found"):
                return self.bad_request_with_data(response.to_dict(), error_message)
            else:
                return self.internal_error_with_data(response.to_dict(), error_message)

    # Helper methods for returning errors with data payload
    def bad_request_with_data(self, data: dict[str, Any], message: str) -> OperationResult[dict[str, Any]]:
        """Return bad request with data payload."""
        result: OperationResult[dict[str, Any]] = OperationResult("Bad Request", 400, detail=message, type="https://www.w3.org/Protocols/HTTP/HTRESP.html#:~:text=Bad%20Request")
        result.data = data
        return cast(OperationResult[dict[str, Any]], result)

    def unauthorized_with_data(self, data: dict[str, Any], message: str) -> OperationResult[dict[str, Any]]:
        """Return unauthorized with data payload."""
        result: OperationResult[dict[str, Any]] = OperationResult("Unauthorized", 401, detail=message, type="https://www.w3.org/Protocols/HTTP/HTRESP.html#:~:text=Unauthorized")
        result.data = data
        return cast(OperationResult[dict[str, Any]], result)

    def service_unavailable_with_data(self, data: dict[str, Any], message: str) -> OperationResult[dict[str, Any]]:
        """Return service unavailable with data payload."""
        result: OperationResult[dict[str, Any]] = OperationResult("Service Unavailable", 503, detail=message, type="https://www.w3.org/Protocols/HTTP/HTRESP.html#:~:text=Service%20Unavailable")
        result.data = data
        return cast(OperationResult[dict[str, Any]], result)

    def internal_error_with_data(self, data: dict[str, Any], message: str) -> OperationResult[dict[str, Any]]:
        """Return internal error with data payload."""
        result: OperationResult[dict[str, Any]] = OperationResult("Internal Server Error", 500, detail=message, type="https://www.w3.org/Protocols/HTTP/HTRESP.html#:~:text=Internal%20Error")
        result.data = data
        return cast(OperationResult[dict[str, Any]], result)
