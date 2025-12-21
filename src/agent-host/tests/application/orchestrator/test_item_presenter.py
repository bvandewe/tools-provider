"""Unit tests for ItemPresenter.

Tests cover:
- Item presentation with various content types
- Message content streaming
- Widget rendering
- Confirmation widget sending
- Content stem resolution (static vs templated)
- Item state management
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from application.orchestrator.context import ConversationContext, OrchestratorState
from application.orchestrator.template.content_generator import ContentGenerator
from application.orchestrator.template.item_presenter import ItemPresenter
from application.orchestrator.template.jinja_renderer import JinjaRenderer


@pytest.fixture
def mock_connection_manager():
    """Create a mock ConnectionManager."""
    manager = MagicMock()
    manager.send_to_connection = AsyncMock(return_value=True)
    return manager


@pytest.fixture
def mock_content_generator():
    """Create a mock ContentGenerator."""
    generator = MagicMock(spec=ContentGenerator)
    generator.generate = AsyncMock(return_value="Generated content")
    return generator


@pytest.fixture
def mock_jinja_renderer():
    """Create a mock JinjaRenderer."""
    renderer = MagicMock(spec=JinjaRenderer)
    renderer.render = MagicMock(side_effect=lambda template, ctx: template)
    return renderer


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
def mock_send_chat_input_enabled():
    """Create a mock chat input enabled callback."""
    return AsyncMock()


@pytest.fixture
def mock_send_item_context():
    """Create a mock send item context callback."""
    return AsyncMock()


@pytest.fixture
def presenter(
    mock_connection_manager,
    mock_content_generator,
    mock_jinja_renderer,
    mock_stream_response,
    mock_send_chat_input_enabled,
    mock_send_item_context,
):
    """Create an ItemPresenter with mocked dependencies."""
    return ItemPresenter(
        connection_manager=mock_connection_manager,
        content_generator=mock_content_generator,
        jinja_renderer=mock_jinja_renderer,
        stream_response=mock_stream_response,
        send_chat_input_enabled=mock_send_chat_input_enabled,
        send_item_context=mock_send_item_context,
    )


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
def sample_message_content():
    """Create a sample message content."""
    content = MagicMock()
    content.id = "content-1"
    content.widget_type = "message"
    content.is_templated = False
    content.stem = "Hello, welcome to the quiz!"
    content.required = False
    content.order = 0
    return content


@pytest.fixture
def sample_widget_content():
    """Create a sample widget content."""
    content = MagicMock()
    content.id = "widget-1"
    content.widget_type = "multiple_choice"
    content.is_templated = False
    content.stem = "What is 2+2?"
    content.required = True
    content.skippable = False
    content.order = 1
    content.options = ["3", "4", "5"]
    content.widget_config = {"layout": "vertical"}
    content.initial_value = None
    content.show_user_response = True
    return content


@pytest.fixture
def sample_item(sample_message_content, sample_widget_content):
    """Create a sample ConversationItemDto-like object."""
    item = MagicMock()
    item.id = "item-1"
    item.title = "Question 1"
    item.contents = [sample_message_content, sample_widget_content]
    item.require_user_confirmation = False
    item.confirmation_button_text = "Continue"
    item.enable_chat_input = False
    return item


class TestItemPresenterPresentation:
    """Test item presentation logic."""

    @pytest.mark.asyncio
    async def test_present_item_updates_context_state(self, presenter, mock_connection, sample_context, sample_item):
        """Test that presenting item updates context with item state."""
        await presenter.present_item(mock_connection, sample_context, sample_item, 0)

        assert sample_context.current_item_index == 0
        assert sample_context.current_item_state is not None
        assert sample_context.current_item_state.item_id == "item-1"

    @pytest.mark.asyncio
    async def test_present_item_sends_item_context(self, presenter, mock_connection, sample_context, sample_item, mock_send_item_context):
        """Test that presenting item sends item context to client."""
        await presenter.present_item(mock_connection, sample_context, sample_item, 0)

        mock_send_item_context.assert_called_once_with(mock_connection, sample_context, 0, sample_item)

    @pytest.mark.asyncio
    async def test_present_item_with_required_widgets_suspends(self, presenter, mock_connection, sample_context, sample_item):
        """Test that items with required widgets set state to SUSPENDED."""
        await presenter.present_item(mock_connection, sample_context, sample_item, 0)

        assert sample_context.state == OrchestratorState.SUSPENDED

    @pytest.mark.asyncio
    async def test_present_informational_item_stays_ready(self, presenter, mock_connection, sample_context, mock_send_chat_input_enabled):
        """Test that informational items (no required widgets) stay READY."""
        item = MagicMock()
        item.id = "info-item"
        item.title = "Information"
        item.contents = []
        item.require_user_confirmation = False
        item.enable_chat_input = True

        await presenter.present_item(mock_connection, sample_context, item, 0)

        assert sample_context.state == OrchestratorState.READY
        mock_send_chat_input_enabled.assert_called_with(mock_connection, True)


class TestItemPresenterContentRendering:
    """Test content rendering logic."""

    @pytest.mark.asyncio
    async def test_render_message_content_streams_response(self, presenter, mock_connection, sample_context, sample_item, sample_message_content, mock_stream_response):
        """Test that message content is streamed as agent response."""
        await presenter.render_content(mock_connection, sample_context, sample_item, sample_message_content)

        mock_stream_response.assert_called_once()
        call_args = mock_stream_response.call_args[0]
        assert call_args[2] == "Hello, welcome to the quiz!"

    @pytest.mark.asyncio
    async def test_render_widget_content_sends_widget_render(self, presenter, mock_connection, sample_context, sample_item, sample_widget_content, mock_connection_manager):
        """Test that widget content sends widget.render message."""
        await presenter.render_content(mock_connection, sample_context, sample_item, sample_widget_content)

        mock_connection_manager.send_to_connection.assert_called_once()
        call_args = mock_connection_manager.send_to_connection.call_args[0]
        message = call_args[1]
        assert message.type == "control.widget.render"


class TestItemPresenterContentStem:
    """Test content stem resolution."""

    @pytest.mark.asyncio
    async def test_static_content_returns_stem(self, presenter, sample_context):
        """Test that static content returns its stem directly."""
        content = MagicMock()
        content.is_templated = False
        content.stem = "Static content"

        result = await presenter._get_content_stem(sample_context, content)

        assert result == "Static content"

    @pytest.mark.asyncio
    async def test_templated_content_uses_generator(self, presenter, sample_context, mock_content_generator):
        """Test that templated content uses ContentGenerator."""
        content = MagicMock()
        content.id = "templated-1"
        content.is_templated = True
        content.stem = None

        item = MagicMock()
        item.instructions = "Generate greeting"

        result = await presenter._get_content_stem(sample_context, content, item)

        assert result == "Generated content"
        mock_content_generator.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_templated_content_fallback_to_static(self, presenter, sample_context, mock_content_generator):
        """Test fallback to static stem when generation fails."""
        mock_content_generator.generate.return_value = None

        content = MagicMock()
        content.id = "templated-1"
        content.is_templated = True
        content.stem = "Fallback content"

        result = await presenter._get_content_stem(sample_context, content)

        assert result == "Fallback content"


class TestItemPresenterConfirmationWidget:
    """Test confirmation widget sending."""

    @pytest.mark.asyncio
    async def test_send_confirmation_widget(self, presenter, mock_connection, sample_context, mock_connection_manager):
        """Test sending a confirmation button widget."""
        item = MagicMock()
        item.id = "item-1"
        item.confirmation_button_text = "Next Question"

        await presenter.send_confirmation_widget(mock_connection, sample_context, item)

        mock_connection_manager.send_to_connection.assert_called_once()
        call_args = mock_connection_manager.send_to_connection.call_args[0]
        message = call_args[1]
        assert message.type == "control.widget.render"
        assert message.payload["widgetType"] == "button"
        assert message.payload["widgetId"] == "item-1-confirm"

    @pytest.mark.asyncio
    async def test_confirmation_widget_config(self, presenter, mock_connection, sample_context, mock_connection_manager):
        """Test confirmation widget has correct config."""
        item = MagicMock()
        item.id = "item-2"
        item.confirmation_button_text = "Submit Answer"

        await presenter.send_confirmation_widget(mock_connection, sample_context, item)

        call_args = mock_connection_manager.send_to_connection.call_args[0]
        message = call_args[1]
        config = message.payload["config"]
        assert config["label"] == "Submit Answer"
        assert config["variant"] == "primary"
        assert config["action"] == "confirm"


class TestItemPresenterWidgetRender:
    """Test widget rendering."""

    @pytest.mark.asyncio
    async def test_widget_render_includes_options(self, presenter, mock_connection, sample_context, mock_connection_manager):
        """Test that multiple_choice widgets include options."""
        item = MagicMock()
        item.id = "item-1"

        content = MagicMock()
        content.id = "mc-widget"
        content.widget_type = "multiple_choice"
        content.options = ["A", "B", "C"]
        content.widget_config = {}
        content.required = True
        content.skippable = False
        content.initial_value = None
        content.show_user_response = True

        await presenter.send_widget_render(mock_connection, sample_context, item, content, "Choose one:")

        call_args = mock_connection_manager.send_to_connection.call_args[0]
        message = call_args[1]
        assert message.payload["config"]["options"] == ["A", "B", "C"]

    @pytest.mark.asyncio
    async def test_widget_render_preserves_widget_config(self, presenter, mock_connection, sample_context, mock_connection_manager):
        """Test that existing widget_config is preserved."""
        item = MagicMock()
        item.id = "item-1"

        content = MagicMock()
        content.id = "text-widget"
        content.widget_type = "free_text"  # Valid widget type
        content.options = None
        content.widget_config = {"placeholder": "Enter text...", "maxLength": 100}
        content.required = True
        content.skippable = True
        content.initial_value = None
        content.show_user_response = True

        await presenter.send_widget_render(mock_connection, sample_context, item, content, "Type here:")

        call_args = mock_connection_manager.send_to_connection.call_args[0]
        message = call_args[1]
        assert message.payload["config"]["placeholder"] == "Enter text..."
        assert message.payload["config"]["maxLength"] == 100


class TestItemPresenterExecutionState:
    """Test item execution state tracking."""

    @pytest.mark.asyncio
    async def test_tracks_required_widget_ids(self, presenter, mock_connection, sample_context, sample_item):
        """Test that required widget IDs are tracked in state."""
        await presenter.present_item(mock_connection, sample_context, sample_item, 0)

        state = sample_context.current_item_state
        assert "widget-1" in state.required_widget_ids
        # Message content is not required (widget_type=message)
        assert "content-1" not in state.required_widget_ids

    @pytest.mark.asyncio
    async def test_tracks_confirmation_requirement(self, presenter, mock_connection, sample_context):
        """Test that confirmation requirement is tracked."""
        item = MagicMock()
        item.id = "confirm-item"
        item.title = "Confirm"
        item.contents = []
        item.require_user_confirmation = True
        item.confirmation_button_text = "I confirm"
        item.enable_chat_input = False

        await presenter.present_item(mock_connection, sample_context, item, 0)

        state = sample_context.current_item_state
        assert state.require_user_confirmation is True
        assert state.confirmation_button_text == "I confirm"
