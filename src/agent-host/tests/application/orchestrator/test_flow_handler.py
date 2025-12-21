"""Unit tests for FlowHandler.

Tests cover:
- Flow start for proactive/reactive conversations
- Flow pause with acknowledgment
- Flow cancel and state reset
- Flow resume from paused state
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from application.orchestrator.context import ConversationContext, OrchestratorState
from application.orchestrator.handlers.flow_handler import FlowHandler


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
    """Create a sample ConversationContext."""
    return ConversationContext(
        connection_id="test-conn-123",
        conversation_id="conv-456",
        user_id="user-789",
        state=OrchestratorState.READY,
    )


@pytest.fixture
def handler(mock_connection_manager):
    """Create a FlowHandler with mocked dependencies."""
    return FlowHandler(mock_connection_manager)


@pytest.fixture
def mock_proactive_runner():
    """Create a mock proactive flow runner callback."""
    return AsyncMock()


@pytest.fixture
def mock_chat_input_sender():
    """Create a mock chat input sender callback."""
    return AsyncMock()


class TestFlowHandlerStart:
    """Test flow start handling."""

    @pytest.mark.asyncio
    async def test_start_proactive_flow(self, handler, mock_connection, mock_proactive_runner):
        """Test starting proactive flow triggers runner."""
        context = ConversationContext(
            connection_id="conn-1",
            conversation_id="conv-1",
            user_id="user-1",
            state=OrchestratorState.READY,
            is_proactive=True,
            has_template=True,
        )

        await handler.handle_flow_start(mock_connection, context, proactive_runner=mock_proactive_runner)

        # State should transition to PRESENTING
        assert context.state == OrchestratorState.PRESENTING

    @pytest.mark.asyncio
    async def test_start_reactive_enables_chat(self, handler, mock_connection, sample_context, mock_chat_input_sender):
        """Test starting reactive flow enables chat input."""
        sample_context.is_proactive = False
        sample_context.has_template = False

        await handler.handle_flow_start(mock_connection, sample_context, chat_input_sender=mock_chat_input_sender)

        mock_chat_input_sender.assert_called_once_with(mock_connection, True)

    @pytest.mark.asyncio
    async def test_start_ignores_non_ready_state(self, handler, mock_connection, mock_proactive_runner):
        """Test that start is ignored when not in READY state."""
        context = ConversationContext(
            connection_id="conn-1",
            conversation_id="conv-1",
            user_id="user-1",
            state=OrchestratorState.PROCESSING,
            is_proactive=True,
            has_template=True,
        )

        await handler.handle_flow_start(mock_connection, context, proactive_runner=mock_proactive_runner)

        # State should not change
        assert context.state == OrchestratorState.PROCESSING


class TestFlowHandlerPause:
    """Test flow pause handling."""

    @pytest.mark.asyncio
    async def test_pause_transitions_state(self, handler, mock_connection, sample_context):
        """Test that pause transitions to PAUSED state."""
        await handler.handle_flow_pause(mock_connection, sample_context, reason="user break")

        assert sample_context.state == OrchestratorState.PAUSED

    @pytest.mark.asyncio
    async def test_pause_sends_acknowledgment(self, handler, mock_connection, sample_context, mock_connection_manager):
        """Test that pause sends acknowledgment message."""
        await handler.handle_flow_pause(mock_connection, sample_context, reason="break time")

        mock_connection_manager.send_to_connection.assert_called_once()

        message = mock_connection_manager.send_to_connection.call_args[0][1]
        assert message.type == "control.conversation.pause"
        assert message.payload["reason"] == "break time"
        assert "pausedAt" in message.payload

    @pytest.mark.asyncio
    async def test_pause_default_reason(self, handler, mock_connection, sample_context, mock_connection_manager):
        """Test default pause reason."""
        await handler.handle_flow_pause(mock_connection, sample_context)

        message = mock_connection_manager.send_to_connection.call_args[0][1]
        assert message.payload["reason"] == "user_requested"


class TestFlowHandlerCancel:
    """Test flow cancel handling."""

    @pytest.mark.asyncio
    async def test_cancel_resets_state(self, handler, mock_connection, sample_context):
        """Test that cancel resets to READY state."""
        sample_context.state = OrchestratorState.PROCESSING
        sample_context.pending_widget_id = "widget-123"
        sample_context.pending_tool_call_id = "call-456"

        await handler.handle_flow_cancel(mock_connection, sample_context)

        assert sample_context.state == OrchestratorState.READY
        assert sample_context.pending_widget_id is None
        assert sample_context.pending_tool_call_id is None

    @pytest.mark.asyncio
    async def test_cancel_sends_acknowledgment(self, handler, mock_connection, sample_context, mock_connection_manager):
        """Test that cancel sends acknowledgment message."""
        await handler.handle_flow_cancel(mock_connection, sample_context, request_id="req-123")

        mock_connection_manager.send_to_connection.assert_called_once()

        message = mock_connection_manager.send_to_connection.call_args[0][1]
        assert message.type == "control.conversation.cancel"
        assert message.payload["requestId"] == "req-123"
        assert "cancelledAt" in message.payload


class TestFlowHandlerResume:
    """Test flow resume handling."""

    @pytest.mark.asyncio
    async def test_resume_from_paused(self, handler, mock_connection, mock_connection_manager):
        """Test resuming from PAUSED state."""
        context = ConversationContext(
            connection_id="conn-1",
            conversation_id="conv-1",
            user_id="user-1",
            state=OrchestratorState.PAUSED,
            is_proactive=False,
        )

        await handler.handle_flow_resume(mock_connection, context)

        assert context.state == OrchestratorState.READY

        # Check acknowledgment
        message = mock_connection_manager.send_to_connection.call_args[0][1]
        assert message.type == "control.conversation.resume"
        assert "resumedAt" in message.payload

    @pytest.mark.asyncio
    async def test_resume_proactive_triggers_runner(self, handler, mock_connection, mock_proactive_runner):
        """Test resuming proactive flow triggers runner."""
        context = ConversationContext(
            connection_id="conn-1",
            conversation_id="conv-1",
            user_id="user-1",
            state=OrchestratorState.PAUSED,
            is_proactive=True,
            has_template=True,
        )

        await handler.handle_flow_resume(mock_connection, context, proactive_runner=mock_proactive_runner)

        assert context.state == OrchestratorState.PRESENTING

    @pytest.mark.asyncio
    async def test_resume_reactive_enables_chat(self, handler, mock_connection, mock_chat_input_sender):
        """Test resuming reactive flow enables chat input."""
        context = ConversationContext(
            connection_id="conn-1",
            conversation_id="conv-1",
            user_id="user-1",
            state=OrchestratorState.PAUSED,
            is_proactive=False,
        )

        await handler.handle_flow_resume(mock_connection, context, chat_input_sender=mock_chat_input_sender)

        mock_chat_input_sender.assert_called_once_with(mock_connection, True)

    @pytest.mark.asyncio
    async def test_resume_ignores_non_paused_state(self, handler, mock_connection, mock_connection_manager):
        """Test that resume is ignored when not in PAUSED state."""
        context = ConversationContext(
            connection_id="conn-1",
            conversation_id="conv-1",
            user_id="user-1",
            state=OrchestratorState.READY,
        )

        await handler.handle_flow_resume(mock_connection, context)

        # Should not send anything
        mock_connection_manager.send_to_connection.assert_not_called()

        # State unchanged
        assert context.state == OrchestratorState.READY
