"""Unit tests for MessageHandler.

Tests cover:
- User message handling with valid state
- Message rejection in invalid states
- Message acknowledgment sending
- User message persistence
- Assistant message completion
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from application.orchestrator.context import ConversationContext, OrchestratorState
from application.orchestrator.handlers.message_handler import MessageHandler


@pytest.fixture
def mock_mediator():
    """Create a mock Mediator."""
    mediator = MagicMock()
    mediator.execute_async = AsyncMock()
    return mediator


@pytest.fixture
def mock_connection_manager():
    """Create a mock ConnectionManager."""
    manager = MagicMock()
    manager.send_to_connection = AsyncMock()
    return manager


@pytest.fixture
def mock_connection():
    """Create a mock Connection."""
    conn = MagicMock()
    conn.connection_id = "test-conn-123"
    return conn


@pytest.fixture
def sample_context():
    """Create a sample ConversationContext in READY state."""
    return ConversationContext(
        connection_id="test-conn-123",
        conversation_id="conv-456",
        user_id="user-789",
        state=OrchestratorState.READY,
    )


@pytest.fixture
def handler(mock_mediator, mock_connection_manager):
    """Create a MessageHandler with mocked dependencies."""
    return MessageHandler(mock_mediator, mock_connection_manager)


@pytest.fixture
def mock_agent_runner():
    """Create a mock agent runner callback."""
    return AsyncMock(return_value="Agent response content")


@pytest.fixture
def mock_error_sender():
    """Create a mock error sender callback."""
    return AsyncMock()


class TestMessageHandlerValidation:
    """Test message handling state validation."""

    @pytest.mark.asyncio
    async def test_reject_message_in_processing_state(self, handler, mock_connection, mock_agent_runner, mock_error_sender):
        """Test that messages are rejected when in PROCESSING state."""
        context = ConversationContext(
            connection_id="conn-1",
            conversation_id="conv-1",
            user_id="user-1",
            state=OrchestratorState.PROCESSING,
        )

        await handler.handle_user_message(mock_connection, context, "Hello", mock_agent_runner, mock_error_sender)

        # Should call error sender with INVALID_STATE
        mock_error_sender.assert_called_once()
        call_args = mock_error_sender.call_args[0]
        assert call_args[1] == "INVALID_STATE"

        # Should NOT run agent
        mock_agent_runner.assert_not_called()

    @pytest.mark.asyncio
    async def test_accept_message_in_ready_state(self, handler, mock_connection, sample_context, mock_agent_runner, mock_error_sender, mock_mediator):
        """Test that messages are accepted in READY state."""
        # Configure mediator to return success
        mock_mediator.execute_async.return_value = MagicMock(is_success=True, data=MagicMock(assistant_message_id="msg-123"))

        await handler.handle_user_message(mock_connection, sample_context, "Hello", mock_agent_runner, mock_error_sender)

        # Should run agent
        mock_agent_runner.assert_called_once()

        # Should NOT call error sender
        mock_error_sender.assert_not_called()

    @pytest.mark.asyncio
    async def test_accept_message_in_suspended_state(self, handler, mock_connection, mock_agent_runner, mock_error_sender, mock_mediator):
        """Test that messages are accepted in SUSPENDED state."""
        context = ConversationContext(
            connection_id="conn-1",
            conversation_id="conv-1",
            user_id="user-1",
            state=OrchestratorState.SUSPENDED,
        )

        mock_mediator.execute_async.return_value = MagicMock(is_success=True, data=MagicMock(assistant_message_id="msg-123"))

        await handler.handle_user_message(mock_connection, context, "Hello", mock_agent_runner, mock_error_sender)

        # Should run agent
        mock_agent_runner.assert_called_once()


class TestMessageHandlerAcknowledgment:
    """Test message acknowledgment sending."""

    @pytest.mark.asyncio
    async def test_sends_message_ack(self, handler, mock_connection, sample_context, mock_agent_runner, mock_error_sender, mock_mediator, mock_connection_manager):
        """Test that acknowledgment is sent before processing."""
        mock_mediator.execute_async.return_value = MagicMock(is_success=True, data=MagicMock(assistant_message_id="msg-123"))

        await handler.handle_user_message(mock_connection, sample_context, "Hello", mock_agent_runner, mock_error_sender)

        # Check that ack was sent
        calls = mock_connection_manager.send_to_connection.call_args_list
        assert len(calls) >= 1

        # First call should be the ack
        ack_message = calls[0][0][1]
        assert ack_message.type == "data.message.ack"
        assert ack_message.payload["status"] == "received"


class TestMessageHandlerPersistence:
    """Test message persistence via domain commands."""

    @pytest.mark.asyncio
    async def test_persists_user_message(self, handler, mock_connection, sample_context, mock_agent_runner, mock_error_sender, mock_mediator):
        """Test that user message is persisted via SendMessageCommand."""
        mock_mediator.execute_async.return_value = MagicMock(is_success=True, data=MagicMock(assistant_message_id="msg-123"))

        await handler.handle_user_message(mock_connection, sample_context, "Hello world", mock_agent_runner, mock_error_sender)

        # Check SendMessageCommand was dispatched
        send_call = mock_mediator.execute_async.call_args_list[0]
        command = send_call[0][0]
        assert command.__class__.__name__ == "SendMessageCommand"
        assert command.content == "Hello world"
        assert command.conversation_id == "conv-456"

    @pytest.mark.asyncio
    async def test_completes_assistant_message(self, handler, mock_connection, sample_context, mock_agent_runner, mock_error_sender, mock_mediator):
        """Test that assistant message is completed after agent response."""
        mock_mediator.execute_async.side_effect = [
            # First call: SendMessageCommand
            MagicMock(is_success=True, data=MagicMock(assistant_message_id="msg-123")),
            # Second call: CompleteMessageCommand
            MagicMock(is_success=True),
        ]

        await handler.handle_user_message(mock_connection, sample_context, "Hello", mock_agent_runner, mock_error_sender)

        # Check CompleteMessageCommand was dispatched
        complete_call = mock_mediator.execute_async.call_args_list[1]
        command = complete_call[0][0]
        assert command.__class__.__name__ == "CompleteMessageCommand"
        assert command.message_id == "msg-123"
        assert command.content == "Agent response content"

    @pytest.mark.asyncio
    async def test_handles_persistence_failure_gracefully(self, handler, mock_connection, sample_context, mock_agent_runner, mock_error_sender, mock_mediator):
        """Test that agent still runs even if persistence fails."""
        mock_mediator.execute_async.return_value = MagicMock(
            is_success=False,
            errors=["Database error"],
            data=None,
        )

        await handler.handle_user_message(mock_connection, sample_context, "Hello", mock_agent_runner, mock_error_sender)

        # Should still run agent
        mock_agent_runner.assert_called_once()


class TestMessageHandlerStateTransitions:
    """Test state machine transitions during message handling."""

    @pytest.mark.asyncio
    async def test_transitions_to_processing(self, handler, mock_connection, sample_context, mock_agent_runner, mock_error_sender, mock_mediator):
        """Test that state transitions to PROCESSING during message handling."""
        mock_mediator.execute_async.return_value = MagicMock(is_success=True, data=MagicMock(assistant_message_id="msg-123"))

        original_state = sample_context.state

        # Capture state during agent run
        async def capture_state(conn, ctx, msg):
            assert ctx.state == OrchestratorState.PROCESSING
            return "Response"

        mock_agent_runner.side_effect = capture_state

        await handler.handle_user_message(mock_connection, sample_context, "Hello", mock_agent_runner, mock_error_sender)

        # Should return to READY after processing
        assert sample_context.state == OrchestratorState.READY

    @pytest.mark.asyncio
    async def test_transitions_to_error_on_exception(self, handler, mock_connection, sample_context, mock_agent_runner, mock_error_sender, mock_mediator):
        """Test that state transitions to ERROR on exception."""
        mock_mediator.execute_async.return_value = MagicMock(is_success=True, data=MagicMock(assistant_message_id="msg-123"))

        mock_agent_runner.side_effect = Exception("Agent crashed")

        await handler.handle_user_message(mock_connection, sample_context, "Hello", mock_agent_runner, mock_error_sender)

        # Should transition to ERROR
        assert sample_context.state == OrchestratorState.ERROR

        # Should send error
        mock_error_sender.assert_called_once()

    @pytest.mark.asyncio
    async def test_updates_last_activity(self, handler, mock_connection, sample_context, mock_agent_runner, mock_error_sender, mock_mediator):
        """Test that last_activity timestamp is updated."""
        mock_mediator.execute_async.return_value = MagicMock(is_success=True, data=MagicMock(assistant_message_id="msg-123"))

        old_activity = sample_context.last_activity

        await handler.handle_user_message(mock_connection, sample_context, "Hello", mock_agent_runner, mock_error_sender)

        assert sample_context.last_activity > old_activity
