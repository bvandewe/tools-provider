"""Unit tests for ConfigSender.

Tests cover:
- Conversation configuration sending
- Chat input state toggling
- Item context sending
- Error message sending
- Flow control (pause/resume)
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from application.orchestrator.context import ConversationContext
from application.orchestrator.protocol.config_sender import ConfigSender


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
        definition_id="def-abc",
        definition_name="Test Conversation",
        template_id="tpl-xyz",
        is_proactive=True,
        total_items=5,
        template_config={
            "allow_backward_navigation": False,
            "allow_navigation": False,
            "enable_chat_input_initially": False,
            "display_progress_indicator": True,
            "display_final_score_report": True,
            "continue_after_completion": False,
        },
    )


@pytest.fixture
def sender(mock_connection_manager):
    """Create a ConfigSender with mocked dependencies."""
    return ConfigSender(mock_connection_manager)


def get_sent_message(mock_connection_manager):
    """Extract the ProtocolMessage from the mock call."""
    return mock_connection_manager.send_to_connection.call_args[0][1]


class TestConfigSenderConversationConfig:
    """Test conversation configuration sending."""

    @pytest.mark.asyncio
    async def test_send_conversation_config_proactive(self, sender, mock_connection, sample_context, mock_connection_manager):
        """Test sending config for proactive conversation."""
        await sender.send_conversation_config(mock_connection, sample_context)

        # Verify message was sent
        mock_connection_manager.send_to_connection.assert_called_once()
        call_args = mock_connection_manager.send_to_connection.call_args

        # Check connection ID
        assert call_args[0][0] == "test-conn-123"

        # Check message structure (ProtocolMessage)
        message = get_sent_message(mock_connection_manager)
        assert message.type == "control.conversation.config"
        assert message.conversation_id == "conv-456"

        # Check payload
        payload = message.payload
        assert payload["templateId"] == "tpl-xyz"
        assert payload["templateName"] == "Test Conversation"
        assert payload["totalItems"] == 5
        assert payload["allowBackwardNavigation"] is False
        assert payload["enableChatInputInitially"] is False
        assert payload["displayProgressIndicator"] is True

    @pytest.mark.asyncio
    async def test_send_conversation_config_reactive(self, sender, mock_connection, mock_connection_manager):
        """Test sending config for reactive conversation."""
        context = ConversationContext(
            connection_id="conn-1",
            conversation_id="conv-1",
            user_id="user-1",
            is_proactive=False,
            template_config={},  # Empty template config
        )

        await sender.send_conversation_config(mock_connection, context)

        message = get_sent_message(mock_connection_manager)
        payload = message.payload

        # Reactive conversations have different defaults
        assert payload["allowBackwardNavigation"] is True  # not context.is_proactive
        assert payload["enableChatInputInitially"] is True
        assert payload["displayProgressIndicator"] is False

    @pytest.mark.asyncio
    async def test_send_conversation_config_default_template_id(self, sender, mock_connection, mock_connection_manager):
        """Test default template ID when none provided."""
        context = ConversationContext(
            connection_id="conn-1",
            conversation_id="conv-1",
            user_id="user-1",
            template_id=None,
        )

        await sender.send_conversation_config(mock_connection, context)

        payload = get_sent_message(mock_connection_manager).payload
        assert payload["templateId"] == "default"


class TestConfigSenderChatInput:
    """Test chat input state sending."""

    @pytest.mark.asyncio
    async def test_send_chat_input_enabled(self, sender, mock_connection, sample_context, mock_connection_manager):
        """Test enabling chat input."""
        await sender.send_chat_input_enabled(mock_connection, sample_context, enabled=True)

        message = get_sent_message(mock_connection_manager)
        assert message.type == "control.flow.chatInput"
        assert message.payload["enabled"] is True

    @pytest.mark.asyncio
    async def test_send_chat_input_disabled(self, sender, mock_connection, sample_context, mock_connection_manager):
        """Test disabling chat input."""
        await sender.send_chat_input_enabled(mock_connection, sample_context, enabled=False)

        payload = get_sent_message(mock_connection_manager).payload
        assert payload["enabled"] is False


class TestConfigSenderItemContext:
    """Test item context sending."""

    @pytest.mark.asyncio
    async def test_send_item_context_with_item(self, sender, mock_connection, sample_context, mock_connection_manager):
        """Test sending item context with item DTO."""
        # Create a mock item DTO
        mock_item = MagicMock()
        mock_item.id = "item-123"
        mock_item.title = "Question 1"
        mock_item.enable_chat_input = False
        mock_item.time_limit_seconds = 60

        await sender.send_item_context(mock_connection, sample_context, item_index=0, item=mock_item)

        message = get_sent_message(mock_connection_manager)
        assert message.type == "control.item.context"

        payload = message.payload
        assert payload["itemId"] == "item-123"
        assert payload["itemIndex"] == 0
        assert payload["totalItems"] == 5
        assert payload["itemTitle"] == "Question 1"
        assert payload["enableChatInput"] is False
        assert payload["timeLimitSeconds"] == 60
        assert payload["showRemainingTime"] is True

    @pytest.mark.asyncio
    async def test_send_item_context_without_item(self, sender, mock_connection, sample_context, mock_connection_manager):
        """Test sending item context with defaults."""
        await sender.send_item_context(mock_connection, sample_context, item_index=2)

        payload = get_sent_message(mock_connection_manager).payload
        assert payload["itemId"] == "item-2"
        assert payload["itemIndex"] == 2
        assert payload["itemTitle"] == "Item 3"
        assert payload["enableChatInput"] is True
        assert "timeLimitSeconds" not in payload  # Should be excluded when None

    @pytest.mark.asyncio
    async def test_send_item_context_min_total_items(self, sender, mock_connection, mock_connection_manager):
        """Test minimum total items is 1."""
        context = ConversationContext(
            connection_id="conn-1",
            conversation_id="conv-1",
            user_id="user-1",
            total_items=0,
        )

        await sender.send_item_context(mock_connection, context, item_index=0)

        payload = get_sent_message(mock_connection_manager).payload
        assert payload["totalItems"] == 1


class TestConfigSenderError:
    """Test error message sending."""

    @pytest.mark.asyncio
    async def test_send_error_with_defaults(self, sender, mock_connection, mock_connection_manager):
        """Test sending error with default options."""
        await sender.send_error(
            mock_connection,
            conversation_id="conv-123",
            code="TEST_ERROR",
            message="Something went wrong",
        )

        message = get_sent_message(mock_connection_manager)
        assert message.type == "system.error"
        assert message.conversation_id == "conv-123"

        payload = message.payload
        assert payload["code"] == "TEST_ERROR"
        assert payload["message"] == "Something went wrong"
        assert payload["isRetryable"] is True
        assert payload["category"] == "business"

    @pytest.mark.asyncio
    async def test_send_error_custom_options(self, sender, mock_connection, mock_connection_manager):
        """Test sending error with custom options."""
        await sender.send_error(
            mock_connection,
            conversation_id="conv-123",
            code="VALIDATION_ERROR",
            message="Invalid input",
            is_retryable=False,
            category="validation",
        )

        payload = get_sent_message(mock_connection_manager).payload
        assert payload["isRetryable"] is False
        assert payload["category"] == "validation"

    @pytest.mark.asyncio
    async def test_send_error_no_conversation_id(self, sender, mock_connection, mock_connection_manager):
        """Test sending error without conversation ID."""
        await sender.send_error(
            mock_connection,
            conversation_id=None,
            code="CONNECTION_ERROR",
            message="Connection failed",
        )

        message = get_sent_message(mock_connection_manager)
        assert message.conversation_id is None


class TestConfigSenderFlowControl:
    """Test flow control sending."""

    @pytest.mark.asyncio
    async def test_send_flow_paused(self, sender, mock_connection, sample_context, mock_connection_manager):
        """Test sending flow paused notification."""
        await sender.send_flow_paused(mock_connection, sample_context, reason="User clicked pause")

        message = get_sent_message(mock_connection_manager)
        assert message.type == "control.flow.pause"

        payload = message.payload
        assert payload["paused"] is True
        assert payload["reason"] == "User clicked pause"
        assert payload["canResume"] is True

    @pytest.mark.asyncio
    async def test_send_flow_paused_default_reason(self, sender, mock_connection, sample_context, mock_connection_manager):
        """Test sending flow paused with default reason."""
        await sender.send_flow_paused(mock_connection, sample_context)

        payload = get_sent_message(mock_connection_manager).payload
        assert payload["reason"] == "User requested pause"

    @pytest.mark.asyncio
    async def test_send_flow_resumed(self, sender, mock_connection, sample_context, mock_connection_manager):
        """Test sending flow resumed notification."""
        await sender.send_flow_resumed(mock_connection, sample_context)

        message = get_sent_message(mock_connection_manager)
        assert message.type == "control.flow.resume"
        assert message.payload["resumed"] is True
