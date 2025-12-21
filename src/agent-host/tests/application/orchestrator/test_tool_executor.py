"""Unit tests for ToolExecutor.

Tests cover:
- Tool execution with valid client and token
- Tool execution without client
- Tool execution without access token
- Error handling during execution
- Successful and failed tool results
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from application.agents import ToolExecutionRequest
from application.orchestrator.agent.tool_executor import ToolExecutor


@pytest.fixture
def mock_tool_provider_client():
    """Create a mock ToolProviderClient."""
    client = MagicMock()
    client.execute_tool = AsyncMock(return_value={"data": "result"})
    return client


@pytest.fixture
def executor(mock_tool_provider_client):
    """Create a ToolExecutor with mocked client."""
    return ToolExecutor(mock_tool_provider_client)


@pytest.fixture
def sample_request():
    """Create a sample ToolExecutionRequest."""
    return ToolExecutionRequest(
        call_id="call-123",
        tool_name="get_weather",
        arguments={"city": "Seattle"},
    )


class TestToolExecutorBasicExecution:
    """Test basic tool execution scenarios."""

    @pytest.mark.asyncio
    async def test_execute_tool_success(self, executor, sample_request, mock_tool_provider_client):
        """Test successful tool execution."""
        execute_fn = executor.create_executor(access_token="test-token")

        results = []
        async for result in execute_fn(sample_request):
            results.append(result)

        assert len(results) == 1
        assert results[0].success is True
        assert results[0].result == {"data": "result"}
        assert results[0].call_id == "call-123"
        assert results[0].tool_name == "get_weather"
        assert results[0].error is None

    @pytest.mark.asyncio
    async def test_execute_tool_calls_client(self, executor, sample_request, mock_tool_provider_client):
        """Test that tool execution calls the client correctly."""
        execute_fn = executor.create_executor(access_token="my-token")

        async for _ in execute_fn(sample_request):
            pass

        mock_tool_provider_client.execute_tool.assert_called_once_with(
            tool_name="get_weather",
            arguments={"city": "Seattle"},
            access_token="my-token",
        )


class TestToolExecutorNoClient:
    """Test tool execution without client configured."""

    @pytest.mark.asyncio
    async def test_execute_without_client_fails(self, sample_request):
        """Test that execution fails gracefully without client."""
        executor = ToolExecutor(tool_provider_client=None)
        execute_fn = executor.create_executor(access_token="token")

        results = []
        async for result in execute_fn(sample_request):
            results.append(result)

        assert len(results) == 1
        assert results[0].success is False
        assert "not configured" in results[0].error


class TestToolExecutorNoToken:
    """Test tool execution without access token."""

    @pytest.mark.asyncio
    async def test_execute_without_token_fails(self, executor, sample_request):
        """Test that execution fails without access token."""
        execute_fn = executor.create_executor(access_token=None)

        results = []
        async for result in execute_fn(sample_request):
            results.append(result)

        assert len(results) == 1
        assert results[0].success is False
        assert "no access token" in results[0].error

    @pytest.mark.asyncio
    async def test_execute_with_empty_token_fails(self, executor, sample_request):
        """Test that execution fails with empty access token."""
        execute_fn = executor.create_executor(access_token="")

        results = []
        async for result in execute_fn(sample_request):
            results.append(result)

        assert len(results) == 1
        assert results[0].success is False


class TestToolExecutorErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    async def test_client_exception_handled(self, executor, sample_request, mock_tool_provider_client):
        """Test that client exceptions are caught and returned as errors."""
        mock_tool_provider_client.execute_tool.side_effect = Exception("Network error")
        execute_fn = executor.create_executor(access_token="token")

        results = []
        async for result in execute_fn(sample_request):
            results.append(result)

        assert len(results) == 1
        assert results[0].success is False
        assert "Network error" in results[0].error

    @pytest.mark.asyncio
    async def test_client_returns_failure(self, executor, sample_request, mock_tool_provider_client):
        """Test handling of failure result from client."""
        mock_tool_provider_client.execute_tool.return_value = {
            "success": False,
            "error": "Tool not found",
        }
        execute_fn = executor.create_executor(access_token="token")

        results = []
        async for result in execute_fn(sample_request):
            results.append(result)

        assert len(results) == 1
        assert results[0].success is False
        assert results[0].error == "Tool not found"


class TestToolExecutorExecutionTime:
    """Test execution time tracking."""

    @pytest.mark.asyncio
    async def test_execution_time_tracked(self, executor, sample_request, mock_tool_provider_client):
        """Test that execution time is tracked."""
        execute_fn = executor.create_executor(access_token="token")

        results = []
        async for result in execute_fn(sample_request):
            results.append(result)

        assert results[0].execution_time_ms > 0

    @pytest.mark.asyncio
    async def test_execution_time_on_error(self, sample_request):
        """Test that execution time is tracked even on errors."""
        executor = ToolExecutor(tool_provider_client=None)
        execute_fn = executor.create_executor(access_token="token")

        results = []
        async for result in execute_fn(sample_request):
            results.append(result)

        assert results[0].execution_time_ms >= 0


class TestToolExecutorMultipleExecutions:
    """Test multiple tool executions."""

    @pytest.mark.asyncio
    async def test_multiple_executions_independent(self, executor, mock_tool_provider_client):
        """Test that multiple executions are independent."""
        execute_fn = executor.create_executor(access_token="token")

        request1 = ToolExecutionRequest(
            call_id="call-1",
            tool_name="tool_a",
            arguments={"arg": "1"},
        )
        request2 = ToolExecutionRequest(
            call_id="call-2",
            tool_name="tool_b",
            arguments={"arg": "2"},
        )

        results1 = [r async for r in execute_fn(request1)]
        results2 = [r async for r in execute_fn(request2)]

        assert results1[0].call_id == "call-1"
        assert results2[0].call_id == "call-2"
        assert mock_tool_provider_client.execute_tool.call_count == 2
