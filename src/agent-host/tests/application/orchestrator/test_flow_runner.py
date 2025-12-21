"""Unit tests for FlowRunner.

Tests cover:
- Proactive flow startup
- Item advancement
- Flow completion
- Error handling
- Template configuration handling
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from application.orchestrator.context import ConversationContext, OrchestratorState
from application.orchestrator.template.flow_runner import FlowRunner


@pytest.fixture
def mock_mediator():
    """Create a mock Mediator."""
    mediator = MagicMock()
    mediator.execute_async = AsyncMock()
    return mediator


@pytest.fixture
def mock_item_presenter():
    """Create a mock ItemPresenter."""
    presenter = MagicMock()
    presenter.present_item = AsyncMock()
    return presenter


@pytest.fixture
def mock_connection():
    """Create a mock Connection."""
    conn = MagicMock()
    conn.connection_id = "test-conn-123"
    return conn


@pytest.fixture
def mock_stream_response():
    """Create a mock stream response callback."""
    return AsyncMock()


@pytest.fixture
def mock_send_error():
    """Create a mock error sender callback."""
    return AsyncMock()


@pytest.fixture
def mock_send_chat_input_enabled():
    """Create a mock chat input enabled callback."""
    return AsyncMock()


@pytest.fixture
def runner(
    mock_mediator,
    mock_item_presenter,
    mock_stream_response,
    mock_send_error,
    mock_send_chat_input_enabled,
):
    """Create a FlowRunner with mocked dependencies."""
    return FlowRunner(
        mediator=mock_mediator,
        item_presenter=mock_item_presenter,
        stream_response=mock_stream_response,
        send_error=mock_send_error,
        send_chat_input_enabled=mock_send_chat_input_enabled,
    )


@pytest.fixture
def sample_context():
    """Create a sample ConversationContext for proactive flow."""
    return ConversationContext(
        connection_id="test-conn-123",
        conversation_id="conv-456",
        user_id="user-789",
        template_id="template-1",
        template_config={
            "enable_chat_input_initially": False,
            "introduction_message": "Welcome to the quiz!",
            "completion_message": "You completed the quiz!",
            "continue_after_completion": False,
        },
        total_items=3,
        state=OrchestratorState.READY,
    )


@pytest.fixture
def sample_item_result():
    """Create a sample successful item query result."""
    result = MagicMock()
    result.is_success = True
    result.data = MagicMock()
    result.data.id = "item-1"
    result.data.title = "Question 1"
    return result


class TestFlowRunnerProactiveFlow:
    """Test proactive flow startup."""

    @pytest.mark.asyncio
    async def test_run_proactive_flow_disables_chat(self, runner, mock_connection, sample_context, mock_send_chat_input_enabled, mock_mediator, sample_item_result):
        """Test that proactive flow disables chat input initially."""
        mock_mediator.execute_async.return_value = sample_item_result

        await runner.run_proactive_flow(mock_connection, sample_context)

        # First call should disable chat input
        first_call = mock_send_chat_input_enabled.call_args_list[0]
        assert first_call[0][1] is False

    @pytest.mark.asyncio
    async def test_run_proactive_flow_sends_introduction(self, runner, mock_connection, sample_context, mock_stream_response, mock_mediator, sample_item_result):
        """Test that proactive flow sends introduction message."""
        mock_mediator.execute_async.return_value = sample_item_result

        await runner.run_proactive_flow(mock_connection, sample_context)

        mock_stream_response.assert_called_once()
        call_args = mock_stream_response.call_args[0]
        assert call_args[2] == "Welcome to the quiz!"

    @pytest.mark.asyncio
    async def test_run_proactive_flow_presents_first_item(self, runner, mock_connection, sample_context, mock_item_presenter, mock_mediator, sample_item_result):
        """Test that proactive flow presents the first item."""
        mock_mediator.execute_async.return_value = sample_item_result

        await runner.run_proactive_flow(mock_connection, sample_context)

        mock_item_presenter.present_item.assert_called_once()
        call_args = mock_item_presenter.present_item.call_args[0]
        assert call_args[3] == 0  # item_index

    @pytest.mark.asyncio
    async def test_run_proactive_flow_enables_chat_if_configured(self, runner, mock_connection, mock_send_chat_input_enabled, mock_mediator, sample_item_result):
        """Test that chat input is enabled if configured."""
        context = ConversationContext(
            connection_id="conn-1",
            conversation_id="conv-1",
            user_id="user-1",
            template_id="template-1",
            template_config={"enable_chat_input_initially": True},
            total_items=1,
        )
        mock_mediator.execute_async.return_value = sample_item_result

        await runner.run_proactive_flow(mock_connection, context)

        first_call = mock_send_chat_input_enabled.call_args_list[0]
        assert first_call[0][1] is True


class TestFlowRunnerErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    async def test_run_proactive_flow_handles_exception(self, runner, mock_connection, sample_context, mock_send_error, mock_mediator):
        """Test that exceptions are caught and error is sent."""
        mock_mediator.execute_async.side_effect = Exception("Database error")

        await runner.run_proactive_flow(mock_connection, sample_context)

        assert sample_context.state == OrchestratorState.ERROR
        mock_send_error.assert_called_once()
        error_args = mock_send_error.call_args[0]
        assert error_args[1] == "FLOW_ERROR"

    @pytest.mark.asyncio
    async def test_present_item_error_sends_error(self, runner, mock_connection, sample_context, mock_send_error, mock_mediator):
        """Test that item load failure sends error."""
        result = MagicMock()
        result.is_success = False
        result.data = None
        result.errors = ["Item not found"]
        mock_mediator.execute_async.return_value = result

        await runner._present_item_at_index(mock_connection, sample_context, 0)

        mock_send_error.assert_called_once()
        error_args = mock_send_error.call_args[0]
        assert error_args[1] == "ITEM_LOAD_FAILED"

    @pytest.mark.asyncio
    async def test_no_template_id_sends_error(self, runner, mock_connection, mock_send_error):
        """Test that missing template_id sends error."""
        context = ConversationContext(
            connection_id="conn-1",
            conversation_id="conv-1",
            user_id="user-1",
            template_id=None,  # No template
        )

        await runner._present_item_at_index(mock_connection, context, 0)

        mock_send_error.assert_called_once()
        error_args = mock_send_error.call_args[0]
        assert error_args[1] == "NO_TEMPLATE"


class TestFlowRunnerAdvancement:
    """Test item advancement logic."""

    @pytest.mark.asyncio
    async def test_advance_to_next_item(self, runner, mock_connection, sample_context, mock_item_presenter, mock_mediator, sample_item_result):
        """Test advancing to the next item."""
        sample_context.current_item_index = 0
        mock_mediator.execute_async.return_value = sample_item_result

        await runner.advance_to_next_item(mock_connection, sample_context)

        mock_item_presenter.present_item.assert_called_once()
        call_args = mock_item_presenter.present_item.call_args[0]
        assert call_args[3] == 1  # next item index

    @pytest.mark.asyncio
    async def test_advance_past_last_item_completes_flow(self, runner, mock_connection, sample_context, mock_item_presenter, mock_stream_response):
        """Test that advancing past last item completes the flow."""
        sample_context.current_item_index = 2  # At last item (0-indexed)
        sample_context.total_items = 3

        await runner.advance_to_next_item(mock_connection, sample_context)

        # Should not present another item
        mock_item_presenter.present_item.assert_not_called()
        # Should send completion message
        mock_stream_response.assert_called_once()
        assert sample_context.state == OrchestratorState.COMPLETED


class TestFlowRunnerCompletion:
    """Test flow completion logic."""

    @pytest.mark.asyncio
    async def test_complete_flow_sends_completion_message(self, runner, mock_connection, sample_context, mock_stream_response):
        """Test that completion message is sent."""
        await runner.complete_flow(mock_connection, sample_context)

        mock_stream_response.assert_called_once()
        call_args = mock_stream_response.call_args[0]
        assert call_args[2] == "You completed the quiz!"

    @pytest.mark.asyncio
    async def test_complete_flow_sets_completed_state(self, runner, mock_connection, sample_context, mock_send_chat_input_enabled):
        """Test that flow completion sets COMPLETED state."""
        await runner.complete_flow(mock_connection, sample_context)

        assert sample_context.state == OrchestratorState.COMPLETED
        mock_send_chat_input_enabled.assert_called_with(mock_connection, False)

    @pytest.mark.asyncio
    async def test_complete_flow_continues_if_configured(self, runner, mock_connection, mock_send_chat_input_enabled):
        """Test that flow continues with free chat if configured."""
        context = ConversationContext(
            connection_id="conn-1",
            conversation_id="conv-1",
            user_id="user-1",
            template_config={
                "continue_after_completion": True,
            },
        )

        await runner.complete_flow(mock_connection, context)

        assert context.state == OrchestratorState.READY
        mock_send_chat_input_enabled.assert_called_with(mock_connection, True)

    @pytest.mark.asyncio
    async def test_complete_flow_without_completion_message(self, runner, mock_connection, mock_stream_response):
        """Test completion without configured message."""
        context = ConversationContext(
            connection_id="conn-1",
            conversation_id="conv-1",
            user_id="user-1",
            template_config={},  # No completion_message
        )

        await runner.complete_flow(mock_connection, context)

        mock_stream_response.assert_not_called()


class TestFlowRunnerItemLoading:
    """Test item loading via mediator."""

    @pytest.mark.asyncio
    async def test_loads_item_with_correct_query(self, runner, mock_connection, sample_context, mock_mediator, sample_item_result):
        """Test that items are loaded with correct query parameters."""
        mock_mediator.execute_async.return_value = sample_item_result

        await runner._present_item_at_index(mock_connection, sample_context, 2)

        mock_mediator.execute_async.assert_called_once()
        query = mock_mediator.execute_async.call_args[0][0]
        assert query.template_id == "template-1"
        assert query.item_index == 2
        assert query.for_client is False

    @pytest.mark.asyncio
    async def test_item_load_failure_at_end_completes_flow(self, runner, mock_connection, sample_context, mock_mediator, mock_stream_response):
        """Test that item load failure at end of items completes flow."""
        result = MagicMock()
        result.is_success = False
        result.data = None
        mock_mediator.execute_async.return_value = result

        # Set item_index to be at or past total_items
        await runner._present_item_at_index(mock_connection, sample_context, 3)

        # Should complete the flow instead of sending error
        mock_stream_response.assert_called_once()
        assert sample_context.state == OrchestratorState.COMPLETED
