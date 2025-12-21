"""Test for MessageContentUpdatedDomainEvent and update_message_content method."""

from datetime import UTC, datetime

import pytest

from domain.entities.conversation import Conversation
from domain.events.conversation import MessageContentUpdatedDomainEvent
from domain.models.message import MessageRole, MessageStatus


class TestMessageContentUpdatedDomainEvent:
    """Tests for the MessageContentUpdatedDomainEvent."""

    def test_event_creation(self):
        """Test that the event can be created with all required fields."""
        event = MessageContentUpdatedDomainEvent(
            aggregate_id="conv-123",
            message_id="msg-456",
            content="Hello world",
        )

        assert event.aggregate_id == "conv-123"
        assert event.message_id == "msg-456"
        assert event.content == "Hello world"
        assert event.updated_at is not None

    def test_event_with_custom_timestamp(self):
        """Test that the event can be created with a custom timestamp."""
        custom_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        event = MessageContentUpdatedDomainEvent(
            aggregate_id="conv-123",
            message_id="msg-456",
            content="Test content",
            updated_at=custom_time,
        )

        assert event.updated_at == custom_time


class TestConversationUpdateMessageContent:
    """Tests for the Conversation.update_message_content method."""

    def test_update_message_content_success(self):
        """Test that update_message_content updates the message content."""
        # Create a conversation with a message
        conv = Conversation(
            user_id="user-123",
            definition_id="def-456",
            system_prompt="You are a helpful assistant.",
        )

        # Add an assistant message with empty content (like streaming start)
        message_id = conv.add_message(
            role=MessageRole.ASSISTANT,
            content="",
            status=MessageStatus.PENDING,
        )

        # Update the message content
        result = conv.update_message_content(message_id, "Updated content after streaming")

        assert result is True

        # Verify the content was updated in state
        messages = conv.state.messages
        assistant_msg = next(m for m in messages if m["id"] == message_id)
        assert assistant_msg["content"] == "Updated content after streaming"

    def test_update_message_content_no_change(self):
        """Test that update_message_content returns False when content unchanged."""
        conv = Conversation(
            user_id="user-123",
            definition_id="def-456",
        )

        message_id = conv.add_message(
            role=MessageRole.ASSISTANT,
            content="Same content",
            status=MessageStatus.COMPLETED,
        )

        # Try to update with same content
        result = conv.update_message_content(message_id, "Same content")

        assert result is False

    def test_update_message_content_not_found(self):
        """Test that update_message_content returns False for non-existent message."""
        conv = Conversation(
            user_id="user-123",
            definition_id="def-456",
        )

        result = conv.update_message_content("non-existent-id", "Some content")

        assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
