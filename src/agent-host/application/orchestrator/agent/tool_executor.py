"""Tool execution for agent operations.

This module provides the ToolExecutor class which creates tool executor
functions that agents use to execute tools via the Tools Provider service.
"""

import logging
import time
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any, Protocol

from application.agents import ToolExecutionRequest, ToolExecutionResult

if TYPE_CHECKING:
    pass

log = logging.getLogger(__name__)


class ToolProviderClientProtocol(Protocol):
    """Protocol for Tool Provider client interface."""

    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        access_token: str,
    ) -> Any:
        """Execute a tool and return the result."""
        ...


class ToolExecutor:
    """Creates tool executor functions for agent use.

    The ToolExecutor wraps the ToolProviderClient and creates async generator
    functions that agents use to execute tools. Each execution yields a
    ToolExecutionResult with success/failure status.

    Example:
        >>> executor = ToolExecutor(tool_provider_client)
        >>> execute_fn = executor.create_executor(access_token="...")
        >>> async for result in execute_fn(request):
        ...     print(result.success)
    """

    def __init__(
        self,
        tool_provider_client: ToolProviderClientProtocol | None = None,
    ) -> None:
        """Initialize the ToolExecutor.

        Args:
            tool_provider_client: Client for calling the Tools Provider service.
                                  If None, tool execution will fail gracefully.
        """
        self._tool_provider_client = tool_provider_client

    def create_executor(
        self,
        access_token: str | None = None,
    ):
        """Create a tool executor function for agent use.

        Returns an async generator function that the agent uses to execute
        tools by calling the Tools Provider service.

        Args:
            access_token: OAuth2 access token for authenticating tool calls

        Returns:
            An async generator function for tool execution
        """

        async def execute_tool(request: ToolExecutionRequest) -> AsyncIterator[ToolExecutionResult]:
            """Execute a tool via the Tools Provider service.

            Args:
                request: The tool execution request

            Yields:
                ToolExecutionResult with the tool's output or error
            """
            start_time = time.time()

            log.info(f"🔧 Tool execution requested: {request.tool_name}({request.arguments})")

            # Check if we have the required client and access token
            if not self._tool_provider_client:
                log.error("ToolProviderClient not configured - cannot execute tools")
                yield ToolExecutionResult(
                    call_id=request.call_id,
                    tool_name=request.tool_name,
                    success=False,
                    result=None,
                    error="Tool execution not available - ToolProviderClient not configured",
                    execution_time_ms=(time.time() - start_time) * 1000,
                )
                return

            if not access_token:
                log.error("No access token available - cannot execute tools")
                yield ToolExecutionResult(
                    call_id=request.call_id,
                    tool_name=request.tool_name,
                    success=False,
                    result=None,
                    error="Tool execution not available - no access token",
                    execution_time_ms=(time.time() - start_time) * 1000,
                )
                return

            try:
                # Call the Tools Provider service
                result = await self._tool_provider_client.execute_tool(
                    tool_name=request.tool_name,
                    arguments=request.arguments,
                    access_token=access_token,
                )

                execution_time_ms = (time.time() - start_time) * 1000

                # Check if the result indicates an error
                if isinstance(result, dict) and result.get("success") is False:
                    log.warning(f"🔧 Tool execution failed: {request.tool_name} - {result.get('error')}")
                    yield ToolExecutionResult(
                        call_id=request.call_id,
                        tool_name=request.tool_name,
                        success=False,
                        result=None,
                        error=result.get("error", "Unknown error"),
                        execution_time_ms=execution_time_ms,
                    )
                else:
                    log.info(f"🔧 Tool executed successfully: {request.tool_name} in {execution_time_ms:.2f}ms")
                    yield ToolExecutionResult(
                        call_id=request.call_id,
                        tool_name=request.tool_name,
                        success=True,
                        result=result,
                        error=None,
                        execution_time_ms=execution_time_ms,
                    )

            except Exception as e:
                execution_time_ms = (time.time() - start_time) * 1000
                log.error(f"🔧 Tool execution error: {request.tool_name} - {e}")
                yield ToolExecutionResult(
                    call_id=request.call_id,
                    tool_name=request.tool_name,
                    success=False,
                    result=None,
                    error=str(e),
                    execution_time_ms=execution_time_ms,
                )

        return execute_tool
