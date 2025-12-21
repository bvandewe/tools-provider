"""Unit tests for WidgetSender.

Tests cover:
- Widget render message sending
- Confirmation button widget sending
- Widget state updates
- Widget render from content DTOs
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from application.orchestrator.context import ConversationContext
from application.orchestrator.protocol.widget_sender import WidgetSender


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
    )


@pytest.fixture
def sender(mock_connection_manager):
    """Create a WidgetSender with mocked dependencies."""
    return WidgetSender(mock_connection_manager)


def get_sent_message(mock_connection_manager):
    """Extract the ProtocolMessage from the mock call."""
    return mock_connection_manager.send_to_connection.call_args[0][1]


class TestWidgetSenderRender:
    """Test widget render sending."""

    @pytest.mark.asyncio
    async def test_send_widget_render_minimal(self, sender, mock_connection, sample_context, mock_connection_manager):
        """Test sending minimal widget render."""
        await sender.send_widget_render(
            connection=mock_connection,
            context=sample_context,
            item_id="item-1",
            widget_id="widget-1",
            widget_type="free_text",  # Use valid widget type
        )

        call_args = mock_connection_manager.send_to_connection.call_args
        assert call_args[0][0] == "test-conn-123"

        message = get_sent_message(mock_connection_manager)
        assert message.type == "control.widget.render"
        assert message.conversation_id == "conv-456"

        payload = message.payload
        assert payload["itemId"] == "item-1"
        assert payload["widgetId"] == "widget-1"
        assert payload["widgetType"] == "free_text"
        assert payload["required"] is False
        assert payload["skippable"] is True

    @pytest.mark.asyncio
    async def test_send_widget_render_full(self, sender, mock_connection, sample_context, mock_connection_manager):
        """Test sending fully configured widget render."""
        await sender.send_widget_render(
            connection=mock_connection,
            context=sample_context,
            item_id="item-2",
            widget_id="widget-mc-1",
            widget_type="multiple_choice",
            stem="What is 2 + 2?",
            widget_config={"layout": "vertical"},
            options=[
                {"value": "a", "label": "3"},
                {"value": "b", "label": "4"},
                {"value": "c", "label": "5"},
            ],
            required=True,
            skippable=False,
            initial_value="b",
            show_user_response=True,
        )

        payload = get_sent_message(mock_connection_manager).payload

        assert payload["stem"] == "What is 2 + 2?"
        assert payload["required"] is True
        assert payload["skippable"] is False
        assert payload["initialValue"] == "b"
        assert payload["showUserResponse"] is True

        # Check options at top level and widgetConfig separate
        assert len(payload["options"]) == 3
        assert payload["options"][1]["label"] == "4"
        assert payload["widgetConfig"]["layout"] == "vertical"

    @pytest.mark.asyncio
    async def test_send_widget_render_layout_and_constraints(self, sender, mock_connection, sample_context, mock_connection_manager):
        """Test that layout and constraints are included."""
        await sender.send_widget_render(
            connection=mock_connection,
            context=sample_context,
            item_id="item-1",
            widget_id="widget-1",
            widget_type="slider",
            skippable=True,
        )

        payload = get_sent_message(mock_connection_manager).payload

        assert payload["layout"]["mode"] == "flow"
        assert payload["constraints"]["moveable"] is False
        assert payload["constraints"]["resizable"] is False
        assert payload["constraints"]["dismissable"] is True  # Matches skippable

    @pytest.mark.asyncio
    async def test_send_widget_render_not_skippable_constraints(self, sender, mock_connection, sample_context, mock_connection_manager):
        """Test constraints when widget is not skippable."""
        await sender.send_widget_render(
            connection=mock_connection,
            context=sample_context,
            item_id="item-1",
            widget_id="widget-1",
            widget_type="free_text",  # Use valid widget type
            skippable=False,
        )

        payload = get_sent_message(mock_connection_manager).payload
        assert payload["constraints"]["dismissable"] is False


class TestWidgetSenderRenderFromContent:
    """Test widget render from content DTO."""

    @pytest.mark.asyncio
    async def test_send_widget_render_from_content(self, sender, mock_connection, sample_context, mock_connection_manager):
        """Test sending widget render from content DTO."""
        # Create mock item and content
        mock_item = MagicMock()
        mock_item.id = "item-42"

        mock_content = MagicMock()
        mock_content.id = "content-99"
        mock_content.widget_type = "rating"
        mock_content.widget_config = {"max_stars": 5}
        mock_content.options = None
        mock_content.required = True
        mock_content.skippable = False
        mock_content.initial_value = 3
        mock_content.show_user_response = True

        await sender.send_widget_render_from_content(
            connection=mock_connection,
            context=sample_context,
            item=mock_item,
            content=mock_content,
            stem="Rate your experience",
        )

        payload = get_sent_message(mock_connection_manager).payload

        assert payload["itemId"] == "item-42"
        assert payload["widgetId"] == "content-99"
        assert payload["widgetType"] == "rating"
        assert payload["stem"] == "Rate your experience"
        assert payload["widgetConfig"]["max_stars"] == 5
        assert payload["initialValue"] == 3


class TestWidgetSenderConfirmation:
    """Test confirmation widget sending."""

    @pytest.mark.asyncio
    async def test_send_confirmation_widget(self, sender, mock_connection, sample_context, mock_connection_manager):
        """Test sending confirmation button widget."""
        await sender.send_confirmation_widget(
            connection=mock_connection,
            context=sample_context,
            item_id="item-5",
            button_text="Confirm Selection",
        )

        message = get_sent_message(mock_connection_manager)
        assert message.type == "control.widget.render"

        payload = message.payload
        assert payload["itemId"] == "item-5"
        assert payload["widgetId"] == "item-5-confirm"
        assert payload["widgetType"] == "button"
        assert payload["required"] is True
        assert payload["skippable"] is False
        assert payload["showUserResponse"] is False

        # Check button widgetConfig
        widgetConfig = payload["widgetConfig"]
        assert widgetConfig["label"] == "Confirm Selection"
        assert widgetConfig["variant"] == "primary"
        assert widgetConfig["action"] == "confirm"

    @pytest.mark.asyncio
    async def test_send_confirmation_widget_default_text(self, sender, mock_connection, sample_context, mock_connection_manager):
        """Test default button text."""
        await sender.send_confirmation_widget(
            connection=mock_connection,
            context=sample_context,
            item_id="item-1",
        )

        payload = get_sent_message(mock_connection_manager).payload
        assert payload["widgetConfig"]["label"] == "Submit"

    @pytest.mark.asyncio
    async def test_send_confirmation_widget_from_item(self, sender, mock_connection, sample_context, mock_connection_manager):
        """Test sending confirmation widget from item DTO."""
        mock_item = MagicMock()
        mock_item.id = "item-exam-q1"
        mock_item.confirmation_button_text = "Submit Answer"

        await sender.send_confirmation_widget_from_item(
            connection=mock_connection,
            context=sample_context,
            item=mock_item,
        )

        payload = get_sent_message(mock_connection_manager).payload
        assert payload["widgetId"] == "item-exam-q1-confirm"
        assert payload["widgetConfig"]["label"] == "Submit Answer"


class TestWidgetSenderUpdate:
    """Test widget state update sending."""

    @pytest.mark.asyncio
    async def test_send_widget_update_completed(self, sender, mock_connection, sample_context, mock_connection_manager):
        """Test sending widget completed state."""
        await sender.send_widget_update(
            connection=mock_connection,
            context=sample_context,
            widget_id="widget-123",
            state="completed",
            value="user answer",
        )

        message = get_sent_message(mock_connection_manager)
        assert message.type == "control.widget.update"
        assert message.conversation_id == "conv-456"

        payload = message.payload
        assert payload["widgetId"] == "widget-123"
        assert payload["state"] == "completed"
        assert payload["value"] == "user answer"

    @pytest.mark.asyncio
    async def test_send_widget_update_disabled(self, sender, mock_connection, sample_context, mock_connection_manager):
        """Test sending widget disabled state."""
        await sender.send_widget_update(
            connection=mock_connection,
            context=sample_context,
            widget_id="widget-456",
            state="disabled",
        )

        payload = get_sent_message(mock_connection_manager).payload
        assert payload["state"] == "disabled"
        assert payload["value"] is None

    @pytest.mark.asyncio
    async def test_send_widget_update_error(self, sender, mock_connection, sample_context, mock_connection_manager):
        """Test sending widget error state."""
        await sender.send_widget_update(
            connection=mock_connection,
            context=sample_context,
            widget_id="widget-789",
            state="error",
        )

        payload = get_sent_message(mock_connection_manager).payload
        assert payload["state"] == "error"
