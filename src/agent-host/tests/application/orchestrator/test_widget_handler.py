"""Unit tests for WidgetHandler.

Tests cover:
- Widget response handling and acknowledgment
- Response tracking in item state
- Confirmation button handling
- Item completion detection
- Response persistence via domain commands
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from application.orchestrator.context import ConversationContext, ItemExecutionState, OrchestratorState
from application.orchestrator.handlers.widget_handler import WidgetHandler


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
def sample_item_state():
    """Create a sample ItemExecutionState."""
    return ItemExecutionState(
        item_id="item-1",
        item_index=0,
        required_widget_ids={"widget-a", "widget-b"},
        require_user_confirmation=False,
    )


@pytest.fixture
def sample_context(sample_item_state):
    """Create a sample ConversationContext with item state."""
    context = ConversationContext(
        connection_id="test-conn-123",
        conversation_id="conv-456",
        user_id="user-789",
        state=OrchestratorState.PRESENTING,
        is_proactive=True,
        has_template=True,
    )
    context.current_item_state = sample_item_state
    return context


@pytest.fixture
def handler(mock_mediator, mock_connection_manager):
    """Create a WidgetHandler with mocked dependencies."""
    return WidgetHandler(mock_mediator, mock_connection_manager)


@pytest.fixture
def mock_advance_callback():
    """Create a mock advance callback."""
    return AsyncMock()


class TestWidgetHandlerAcknowledgment:
    """Test widget response acknowledgment."""

    @pytest.mark.asyncio
    async def test_sends_response_ack(self, handler, mock_connection, sample_context, mock_connection_manager):
        """Test that acknowledgment is sent on widget response."""
        await handler.handle_widget_response(mock_connection, sample_context, "widget-a", "item-1", "user answer")

        # Check ack was sent
        calls = mock_connection_manager.send_to_connection.call_args_list
        assert len(calls) >= 1

        ack_message = calls[0][0][1]
        assert ack_message.type == "data.response.ack"
        assert ack_message.payload["widgetId"] == "widget-a"
        assert ack_message.payload["itemId"] == "item-1"


class TestWidgetHandlerResponseTracking:
    """Test widget response tracking in item state."""

    @pytest.mark.asyncio
    async def test_tracks_widget_response(self, handler, mock_connection, sample_context):
        """Test that widget responses are stored in item state."""
        await handler.handle_widget_response(mock_connection, sample_context, "widget-a", "item-1", "user answer")

        assert sample_context.current_item_state.widget_responses["widget-a"] == "user answer"

    @pytest.mark.asyncio
    async def test_marks_required_widget_as_answered(self, handler, mock_connection, sample_context):
        """Test that required widgets are marked as answered."""
        await handler.handle_widget_response(mock_connection, sample_context, "widget-a", "item-1", "answer")

        assert "widget-a" in sample_context.current_item_state.answered_widget_ids

    @pytest.mark.asyncio
    async def test_handles_confirmation_button(self, handler, mock_connection, sample_context):
        """Test that confirmation button sets user_confirmed."""
        sample_context.current_item_state.require_user_confirmation = True

        await handler.handle_widget_response(mock_connection, sample_context, "item-1-confirm", "item-1", True)

        assert sample_context.current_item_state.user_confirmed is True


class TestWidgetHandlerItemCompletion:
    """Test item completion detection."""

    @pytest.mark.asyncio
    async def test_detects_item_completion(self, handler, mock_connection, sample_context, mock_advance_callback, mock_mediator):
        """Test that item completion is detected when all widgets answered."""
        mock_mediator.execute_async.return_value = MagicMock(is_success=True)

        # Answer first widget
        await handler.handle_widget_response(mock_connection, sample_context, "widget-a", "item-1", "answer-a", advance_callback=mock_advance_callback)

        # Not complete yet
        mock_advance_callback.assert_not_called()

        # Answer second widget
        await handler.handle_widget_response(mock_connection, sample_context, "widget-b", "item-1", "answer-b", advance_callback=mock_advance_callback)

        # Now complete - should advance
        mock_advance_callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_requires_confirmation_before_completion(self, handler, mock_connection, sample_context, mock_advance_callback, mock_mediator):
        """Test that confirmation is required before completion."""
        sample_context.current_item_state.require_user_confirmation = True
        mock_mediator.execute_async.return_value = MagicMock(is_success=True)

        # Answer all widgets
        await handler.handle_widget_response(mock_connection, sample_context, "widget-a", "item-1", "answer-a", advance_callback=mock_advance_callback)
        await handler.handle_widget_response(mock_connection, sample_context, "widget-b", "item-1", "answer-b", advance_callback=mock_advance_callback)

        # Not complete yet - needs confirmation
        assert mock_advance_callback.call_count == 0

        # Confirm
        await handler.handle_widget_response(mock_connection, sample_context, "item-1-confirm", "item-1", True, advance_callback=mock_advance_callback)

        # Now complete
        mock_advance_callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_sets_completed_at_timestamp(self, handler, mock_connection, sample_context, mock_mediator):
        """Test that completed_at is set when item completes."""
        mock_mediator.execute_async.return_value = MagicMock(is_success=True)

        # Answer all widgets to complete
        await handler.handle_widget_response(mock_connection, sample_context, "widget-a", "item-1", "a")
        await handler.handle_widget_response(mock_connection, sample_context, "widget-b", "item-1", "b")

        assert sample_context.current_item_state.completed_at is not None


class TestWidgetHandlerPersistence:
    """Test response persistence via domain commands."""

    @pytest.mark.asyncio
    async def test_persists_responses_on_completion(self, handler, mock_connection, sample_context, mock_mediator):
        """Test that responses are persisted when item completes."""
        mock_mediator.execute_async.return_value = MagicMock(is_success=True)

        # Complete the item
        await handler.handle_widget_response(mock_connection, sample_context, "widget-a", "item-1", "answer-a")
        await handler.handle_widget_response(mock_connection, sample_context, "widget-b", "item-1", "answer-b")

        # Check commands were dispatched
        calls = mock_mediator.execute_async.call_args_list
        assert len(calls) == 2

        # First: RecordItemResponseCommand
        record_command = calls[0][0][0]
        assert record_command.__class__.__name__ == "RecordItemResponseCommand"
        assert record_command.item_id == "item-1"

        # Second: AdvanceTemplateCommand
        advance_command = calls[1][0][0]
        assert advance_command.__class__.__name__ == "AdvanceTemplateCommand"

    @pytest.mark.asyncio
    async def test_calculates_response_time(self, handler, mock_connection, sample_context, mock_mediator):
        """Test that response time is calculated correctly."""
        mock_mediator.execute_async.return_value = MagicMock(is_success=True)

        # Set started_at
        sample_context.current_item_state.started_at = datetime.now(UTC)

        # Complete the item
        await handler.handle_widget_response(mock_connection, sample_context, "widget-a", "item-1", "a")
        await handler.handle_widget_response(mock_connection, sample_context, "widget-b", "item-1", "b")

        # Check response_time_ms was passed
        record_command = mock_mediator.execute_async.call_args_list[0][0][0]
        assert record_command.response_time_ms is not None
        assert record_command.response_time_ms >= 0


class TestWidgetHandlerEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_handles_unexpected_item_id(self, handler, mock_connection, sample_context):
        """Test handling response for wrong item."""
        # Response for different item
        await handler.handle_widget_response(mock_connection, sample_context, "widget-x", "item-999", "value")

        # Should not crash, response not tracked
        assert "widget-x" not in sample_context.current_item_state.widget_responses

    @pytest.mark.asyncio
    async def test_handles_no_item_state(self, handler, mock_connection):
        """Test handling response when no item state exists."""
        context = ConversationContext(
            connection_id="conn-1",
            conversation_id="conv-1",
            user_id="user-1",
        )
        context.current_item_state = None

        # Should not crash
        await handler.handle_widget_response(mock_connection, context, "widget-a", "item-1", "value")

    @pytest.mark.asyncio
    async def test_reactive_mode_returns_to_ready(self, handler, mock_connection, mock_mediator):
        """Test that reactive mode returns to READY after completion."""
        context = ConversationContext(
            connection_id="conn-1",
            conversation_id="conv-1",
            user_id="user-1",
            is_proactive=False,
            has_template=False,
        )
        context.current_item_state = ItemExecutionState(
            item_id="item-1",
            item_index=0,
            required_widget_ids={"widget-a"},
            require_user_confirmation=False,
        )
        mock_mediator.execute_async.return_value = MagicMock(is_success=True)

        await handler.handle_widget_response(mock_connection, context, "widget-a", "item-1", "answer")

        assert context.state == OrchestratorState.READY
