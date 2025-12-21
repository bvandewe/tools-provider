"""Unit tests for AgentRunner.

Tests cover:
- Building agent context
- Running agent stream
- Tool call/result handling
- Event processing (all AgentEventType cases)
- Error handling
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from application.orchestrator.agent.agent_runner import AgentRunner
from application.orchestrator.context import ConversationContext


@pytest.fixture
def mock_agent():
    """Create a mock Agent."""
    agent = MagicMock()
    agent.run_stream = AsyncMock()
    return agent


@pytest.fixture
def mock_mediator():
    """Create a mock Mediator."""
    mediator = MagicMock()
    mediator.execute_async = AsyncMock(return_value=MagicMock(is_success=True, data=[]))
    return mediator


@pytest.fixture
def mock_connection_manager():
    """Create a mock ConnectionManager."""
    manager = MagicMock()
    manager.send_to_connection = AsyncMock(return_value=True)
    return manager


@pytest.fixture
def mock_llm_provider_factory():
    """Create a mock LlmProviderFactory."""
    factory = MagicMock()
    factory.get_provider = MagicMock(return_value=MagicMock())
    return factory


@pytest.fixture
def mock_tool_executor():
    """Create a mock ToolExecutor."""
    executor = MagicMock()
    executor.create_executor = MagicMock(return_value=AsyncMock())
    return executor


@pytest.fixture
def mock_send_chat_enabled():
    """Create a mock send_chat_input_enabled function."""
    return AsyncMock()


@pytest.fixture
def mock_send_error():
    """Create a mock send_error function."""
    return AsyncMock()


@pytest.fixture
def mock_connection():
    """Create a mock Connection."""
    conn = MagicMock()
    conn.connection_id = "test-conn-123"
    return conn


@pytest.fixture
def sample_context():
    """Create a sample ConversationContext."""
    return ConversationContext(
        connection_id="test-conn-123",
        conversation_id="conv-456",
        user_id="user-789",
        access_token="test-token",
    )


@pytest.fixture
def agent_runner(
    mock_agent,
    mock_mediator,
    mock_connection_manager,
    mock_llm_provider_factory,
    mock_tool_executor,
    mock_send_chat_enabled,
    mock_send_error,
):
    """Create an AgentRunner with mocked dependencies."""
    return AgentRunner(
        agent=mock_agent,
        mediator=mock_mediator,
        connection_manager=mock_connection_manager,
        llm_provider_factory=mock_llm_provider_factory,
        tool_executor=mock_tool_executor,
        send_chat_input_enabled=mock_send_chat_enabled,
        send_error=mock_send_error,
    )


class TestAgentRunnerBuildContext:
    """Test building agent context."""

    @pytest.mark.asyncio
    async def test_build_context_creates_run_context(self, agent_runner, sample_context, mock_mediator):
        """Test that build context creates an AgentRunContext."""
        context = await agent_runner._build_agent_context(sample_context, "Hello agent")

        assert context is not None
        assert context.user_message == "Hello agent"

    @pytest.mark.asyncio
    async def test_build_context_loads_history(self, agent_runner, sample_context, mock_mediator):
        """Test that context loading queries conversation history."""
        await agent_runner._build_agent_context(sample_context, "Hi")

        # Should execute query to get conversation history
        mock_mediator.execute_async.assert_called()


class TestAgentRunnerStreamEvents:
    """Test agent stream event handling."""

    @pytest.mark.asyncio
    async def test_run_stream_returns_content(self, agent_runner, mock_connection, sample_context, mock_agent):
        """Test that run_stream returns accumulated content."""

        # Create a proper async generator
        async def mock_stream(context):
            from application.agents import AgentEventType

            yield MagicMock(
                type=AgentEventType.LLM_RESPONSE_CHUNK,
                data={"content": "Hello"},
            )
            yield MagicMock(
                type=AgentEventType.RUN_COMPLETED,
                data={"content": "Hello"},
            )

        mock_agent.run_stream = mock_stream

        result = await agent_runner.run_stream(mock_connection, sample_context, "Hi")

        assert result is not None
        assert "Hello" in result

    @pytest.mark.asyncio
    async def test_run_stream_handles_run_started(self, agent_runner, mock_connection, sample_context, mock_agent, mock_connection_manager, mock_send_chat_enabled):
        """Test handling of run_started event."""

        async def mock_stream(context):
            from application.agents import AgentEventType

            yield MagicMock(
                type=AgentEventType.RUN_STARTED,
                data={"run_id": "run-123"},
            )
            yield MagicMock(
                type=AgentEventType.RUN_COMPLETED,
                data={},
            )

        mock_agent.run_stream = mock_stream

        await agent_runner.run_stream(mock_connection, sample_context, "Hi")

        # Should disable chat input when run starts
        mock_send_chat_enabled.assert_called()


class TestAgentRunnerToolHandling:
    """Test tool call and result handling."""

    @pytest.mark.asyncio
    async def test_send_tool_call_sends_message(self, agent_runner, mock_connection, sample_context, mock_connection_manager):
        """Test that tool calls send protocol message."""
        tool_data = {
            "tool_name": "get_weather",
            "call_id": "call-123",
            "arguments": {"city": "Seattle"},
        }

        await agent_runner._send_tool_call(mock_connection, sample_context, tool_data)

        mock_connection_manager.send_to_connection.assert_called_once()
        call_args = mock_connection_manager.send_to_connection.call_args[0]
        message = call_args[1]

        assert message.type == "data.tool.call"
        assert message.payload["toolName"] == "get_weather"

    @pytest.mark.asyncio
    async def test_send_tool_result_sends_message(self, agent_runner, mock_connection, sample_context, mock_connection_manager):
        """Test that tool results send protocol message."""
        result_data = {
            "tool_name": "get_weather",
            "call_id": "call-123",
            "result": {"temp": 72},
            "success": True,
        }

        await agent_runner._send_tool_result(mock_connection, sample_context, result_data)

        mock_connection_manager.send_to_connection.assert_called_once()
        call_args = mock_connection_manager.send_to_connection.call_args[0]
        message = call_args[1]

        assert message.type == "data.tool.result"
        assert message.payload["success"] is True


class TestAgentRunnerStreamComplete:
    """Test stream completion handling."""

    @pytest.mark.asyncio
    async def test_send_stream_complete(self, agent_runner, mock_connection, sample_context, mock_connection_manager):
        """Test sending stream complete message."""
        await agent_runner._send_stream_complete(mock_connection, sample_context, "msg-123", "Full response content")

        call_args = mock_connection_manager.send_to_connection.call_args[0]
        message = call_args[1]

        assert message.type == "data.content.complete"
        assert message.payload["messageId"] == "msg-123"
        assert message.payload["fullContent"] == "Full response content"


class TestAgentRunnerErrorHandling:
    """Test error handling during agent run."""

    @pytest.mark.asyncio
    async def test_agent_exception_handled(self, agent_runner, mock_connection, sample_context, mock_agent, mock_send_error):
        """Test that agent exceptions are handled gracefully."""
        mock_agent.run_stream.side_effect = Exception("Agent crashed")

        result = await agent_runner.run_stream(mock_connection, sample_context, "Hi")

        # Should return None on error
        assert result is None
        # Should send error message
        mock_send_error.assert_called()

    @pytest.mark.asyncio
    async def test_run_failed_event_handled(self, agent_runner, mock_connection, sample_context, mock_agent, mock_send_error):
        """Test handling of run_failed event."""

        async def mock_stream(context):
            from application.agents import AgentEventType

            yield MagicMock(
                type=AgentEventType.RUN_FAILED,
                data={"error": "LLM rate limited"},
            )

        mock_agent.run_stream = mock_stream

        await agent_runner.run_stream(mock_connection, sample_context, "Hi")

        mock_send_error.assert_called()


class TestAgentRunnerModelOverride:
    """Test model override functionality."""

    @pytest.mark.asyncio
    async def test_model_override_uses_factory(self, agent_runner, mock_connection, mock_llm_provider_factory, mock_agent):
        """Test that model override uses LLM provider factory."""
        context = ConversationContext(
            connection_id="test-conn",
            conversation_id="conv-123",
            user_id="user-456",
            model="gpt-4o",  # Override model
        )

        async def mock_stream(ctx):
            from application.agents import AgentEventType

            yield MagicMock(
                type=AgentEventType.RUN_COMPLETED,
                data={},
            )

        mock_agent.run_stream = mock_stream

        await agent_runner.run_stream(mock_connection, context, "Hi")

        # Should call factory to get provider for the model
        mock_llm_provider_factory.get_provider_for_model.assert_called_with("gpt-4o")


class TestAgentRunnerChatInputEnabled:
    """Test chat input enabled callback."""

    @pytest.mark.asyncio
    async def test_chat_enabled_after_complete(self, agent_runner, mock_connection, sample_context, mock_agent, mock_send_chat_enabled):
        """Test that chat input is re-enabled after run completes."""

        async def mock_stream(context):
            from application.agents import AgentEventType

            yield MagicMock(
                type=AgentEventType.RUN_COMPLETED,
                data={"content": "Done"},
            )

        mock_agent.run_stream = mock_stream

        await agent_runner.run_stream(mock_connection, sample_context, "Hi")

        mock_send_chat_enabled.assert_called()
