"""Execute tool command with handler.

This command executes a tool on behalf of an authenticated agent,
handling token exchange, request proxying, and response processing.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, cast

from neuroglia.core import OperationResult
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_bus import CloudEventBus
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import CloudEventPublishingOptions
from neuroglia.mapping import Mapper
from neuroglia.mediation import Command, CommandHandler, Mediator
from neuroglia.observability.tracing import add_span_attributes
from opentelemetry import trace

from application.commands.command_handler_base import CommandHandlerBase
from application.services.tool_executor import ToolExecutionError, ToolExecutor
from domain.models import ToolDefinition
from domain.repositories import SourceToolDtoRepository
from integration.models.source_tool_dto import SourceToolDto
from observability import token_exchange_count, token_exchange_errors, tool_execution_count, tool_execution_errors, tool_execution_time

log = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


@dataclass
class ExecuteToolCommand(Command[OperationResult[Dict[str, Any]]]):
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

    arguments: Dict[str, Any] = field(default_factory=dict)
    """Arguments to pass to the tool."""

    agent_token: str = ""
    """The agent's JWT access token for identity propagation."""

    validate_schema: Optional[bool] = None
    """Override schema validation setting (None = use tool's setting)."""

    user_info: Optional[Dict[str, Any]] = None
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
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    execution_time_ms: float = 0.0
    upstream_status: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
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
    CommandHandler[ExecuteToolCommand, OperationResult[Dict[str, Any]]],
):
    """Handler for executing tools via the proxy.

    This handler:
    1. Loads the tool definition from the read model
    2. Validates the agent has access to the tool
    3. Delegates execution to ToolExecutor service
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
    ):
        super().__init__(
            mediator,
            mapper,
            cloud_event_bus,
            cloud_event_publishing_options,
        )
        self._tool_repository = tool_repository
        self._tool_executor = tool_executor

    async def handle_async(self, request: ExecuteToolCommand) -> OperationResult[Dict[str, Any]]:
        """Handle the execute tool command."""
        command = request
        start_time = time.time()

        # Add tracing context
        add_span_attributes(
            {
                "tool.id": command.tool_id,
                "tool.has_arguments": bool(command.arguments),
                "tool.validate_schema": command.validate_schema,
            }
        )

        with tracer.start_as_current_span("execute_tool_command") as span:
            # Record execution attempt
            tool_execution_count.add(1, {"tool_id": command.tool_id})

            # Step 1: Load tool definition
            span.add_event("Loading tool definition")
            tool_dto = await self._tool_repository.get_async(command.tool_id)

            if not tool_dto:
                log.warning(f"Tool not found: {command.tool_id}")
                tool_execution_errors.add(1, {"tool_id": command.tool_id, "error": "not_found"})
                return self.not_found(SourceToolDto, command.tool_id)

            if not tool_dto.is_enabled:
                log.warning(f"Tool is disabled: {command.tool_id}")
                tool_execution_errors.add(1, {"tool_id": command.tool_id, "error": "disabled"})
                return self.bad_request(f"Tool '{command.tool_id}' is disabled")

            # Step 2: Parse tool definition
            if not tool_dto.definition:
                log.error(f"Tool has no definition: {command.tool_id}")
                tool_execution_errors.add(1, {"tool_id": command.tool_id, "error": "no_definition"})
                return self.internal_server_error(f"Tool '{command.tool_id}' has no execution definition")

            try:
                if isinstance(tool_dto.definition, dict):
                    definition = ToolDefinition.from_dict(tool_dto.definition)
                else:
                    definition = tool_dto.definition
            except Exception as e:
                log.error(f"Failed to parse tool definition for {command.tool_id}: {e}")
                tool_execution_errors.add(1, {"tool_id": command.tool_id, "error": "invalid_definition"})
                return self.internal_server_error(f"Invalid tool definition: {e}")

            span.set_attribute("tool.name", definition.name)
            span.set_attribute("tool.source_path", definition.source_path)
            span.set_attribute("tool.execution_mode", definition.execution_profile.mode.value)

            # Step 3: Execute tool
            try:
                span.add_event("Executing tool")
                token_exchange_count.add(1, {"audience": definition.execution_profile.required_audience or "none"})

                result = await self._tool_executor.execute(
                    tool_id=command.tool_id,
                    definition=definition,
                    arguments=command.arguments,
                    agent_token=command.agent_token,
                    source_id=tool_dto.source_id,
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

                log.info(f"Tool execution completed: tool={command.tool_id}, " f"status={result.status}, time={processing_time_ms:.2f}ms")

                return self.ok(response.to_dict())

            except ToolExecutionError as e:
                processing_time_ms = (time.time() - start_time) * 1000
                tool_execution_errors.add(1, {"tool_id": command.tool_id, "error": e.error_code})

                if e.error_code == "token_exchange_failed":
                    token_exchange_errors.add(1, {"error": e.details.get("exchange_error", "unknown")})

                span.set_attribute("tool.error", e.error_code)

                log.warning(f"Tool execution failed: tool={command.tool_id}, " f"error={e.error_code}, message={e.message}")

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

    # Helper methods for returning errors with data payload
    def bad_request_with_data(self, data: Dict[str, Any], message: str) -> OperationResult[Dict[str, Any]]:
        """Return bad request with data payload."""
        result: OperationResult[Dict[str, Any]] = OperationResult("Bad Request", 400, detail=message, type="https://www.w3.org/Protocols/HTTP/HTRESP.html#:~:text=Bad%20Request")
        result.data = data
        return cast(OperationResult[Dict[str, Any]], result)

    def unauthorized_with_data(self, data: Dict[str, Any], message: str) -> OperationResult[Dict[str, Any]]:
        """Return unauthorized with data payload."""
        result: OperationResult[Dict[str, Any]] = OperationResult("Unauthorized", 401, detail=message, type="https://www.w3.org/Protocols/HTTP/HTRESP.html#:~:text=Unauthorized")
        result.data = data
        return cast(OperationResult[Dict[str, Any]], result)

    def service_unavailable_with_data(self, data: Dict[str, Any], message: str) -> OperationResult[Dict[str, Any]]:
        """Return service unavailable with data payload."""
        result: OperationResult[Dict[str, Any]] = OperationResult("Service Unavailable", 503, detail=message, type="https://www.w3.org/Protocols/HTTP/HTRESP.html#:~:text=Service%20Unavailable")
        result.data = data
        return cast(OperationResult[Dict[str, Any]], result)

    def internal_error_with_data(self, data: Dict[str, Any], message: str) -> OperationResult[Dict[str, Any]]:
        """Return internal error with data payload."""
        result: OperationResult[Dict[str, Any]] = OperationResult("Internal Server Error", 500, detail=message, type="https://www.w3.org/Protocols/HTTP/HTRESP.html#:~:text=Internal%20Error")
        result.data = data
        return cast(OperationResult[Dict[str, Any]], result)
