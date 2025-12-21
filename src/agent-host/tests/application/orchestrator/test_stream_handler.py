"""Unit tests for StreamHandler.

Tests cover:
- Streaming content in chunks
- Sending completion messages
- Configurable chunk size and delay
- Single chunk and complete methods
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from application.orchestrator.agent.stream_handler import StreamHandler
from application.orchestrator.context import ConversationContext


@pytest.fixture
def mock_connection_manager():
    """Create a mock ConnectionManager."""
    manager = MagicMock()
    manager.send_to_connection = AsyncMock(return_value=True)
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
def handler(mock_connection_manager):
    """Create a StreamHandler with mocked dependencies."""
    return StreamHandler(
        connection_manager=mock_connection_manager,
        chunk_size=10,  # Small for testing
        chunk_delay=0,  # No delay for tests
    )


class TestStreamHandlerBasicStreaming:
    """Test basic streaming functionality."""

    @pytest.mark.asyncio
    async def test_stream_response_returns_message_id(self, handler, mock_connection, sample_context):
        """Test that streaming returns a message ID."""
        message_id = await handler.stream_response(mock_connection, sample_context, "Hello")

        assert message_id is not None
        assert message_id.startswith("msg_")

    @pytest.mark.asyncio
    async def test_stream_response_sends_chunks(self, handler, mock_connection, sample_context, mock_connection_manager):
        """Test that content is sent in chunks."""
        await handler.stream_response(mock_connection, sample_context, "Hello World!")

        # Should send chunks + completion message
        assert mock_connection_manager.send_to_connection.call_count >= 2

    @pytest.mark.asyncio
    async def test_stream_response_sends_complete(self, handler, mock_connection, sample_context, mock_connection_manager):
        """Test that completion message is sent."""
        await handler.stream_response(mock_connection, sample_context, "Hi")

        # Find the completion message
        calls = mock_connection_manager.send_to_connection.call_args_list
        last_call = calls[-1]
        message = last_call[0][1]

        assert message.type == "data.content.complete"
        assert message.payload["fullContent"] == "Hi"


class TestStreamHandlerChunking:
    """Test chunking behavior."""

    @pytest.mark.asyncio
    async def test_short_content_single_chunk(self, mock_connection_manager, mock_connection, sample_context):
        """Test that short content sends as single chunk."""
        handler = StreamHandler(mock_connection_manager, chunk_size=100, chunk_delay=0)

        await handler.stream_response(mock_connection, sample_context, "Short")

        # Should send 1 chunk (final=True) + 1 completion = 2 messages
        assert mock_connection_manager.send_to_connection.call_count == 2

    @pytest.mark.asyncio
    async def test_long_content_multiple_chunks(self, mock_connection_manager, mock_connection, sample_context):
        """Test that long content is split into multiple chunks."""
        handler = StreamHandler(mock_connection_manager, chunk_size=5, chunk_delay=0)
        content = "Hello World!"  # 12 chars = 3 chunks

        await handler.stream_response(mock_connection, sample_context, content)

        # Should send 3 chunks + 1 completion = 4 messages
        assert mock_connection_manager.send_to_connection.call_count == 4

    @pytest.mark.asyncio
    async def test_final_flag_only_on_last_chunk(self, mock_connection_manager, mock_connection, sample_context):
        """Test that only the last chunk has final=True."""
        handler = StreamHandler(mock_connection_manager, chunk_size=5, chunk_delay=0)

        await handler.stream_response(mock_connection, sample_context, "Hello World")

        calls = mock_connection_manager.send_to_connection.call_args_list
        chunk_calls = [c for c in calls if c[0][1].type == "data.content.chunk"]

        # All but last chunk should have final=False
        for chunk_call in chunk_calls[:-1]:
            message = chunk_call[0][1]
            assert message.payload.get("final") is False

        # Last chunk should have final=True
        last_chunk = chunk_calls[-1][0][1]
        assert last_chunk.payload.get("final") is True


class TestStreamHandlerSendChunk:
    """Test individual chunk sending."""

    @pytest.mark.asyncio
    async def test_send_chunk_creates_message(self, handler, mock_connection, sample_context, mock_connection_manager):
        """Test sending individual chunk."""
        await handler.send_chunk(mock_connection, sample_context, "msg-1", "Hello", is_final=False)

        mock_connection_manager.send_to_connection.assert_called_once()
        call_args = mock_connection_manager.send_to_connection.call_args[0]
        message = call_args[1]

        assert message.type == "data.content.chunk"
        assert message.payload["content"] == "Hello"
        assert message.payload["messageId"] == "msg-1"
        assert message.payload["final"] is False

    @pytest.mark.asyncio
    async def test_send_chunk_final(self, handler, mock_connection, sample_context, mock_connection_manager):
        """Test sending final chunk."""
        await handler.send_chunk(mock_connection, sample_context, "msg-2", "!", is_final=True)

        call_args = mock_connection_manager.send_to_connection.call_args[0]
        message = call_args[1]

        assert message.payload["final"] is True


class TestStreamHandlerSendComplete:
    """Test completion message sending."""

    @pytest.mark.asyncio
    async def test_send_complete_creates_message(self, handler, mock_connection, sample_context, mock_connection_manager):
        """Test sending completion message."""
        await handler.send_complete(mock_connection, sample_context, "msg-1", "Full content here")

        mock_connection_manager.send_to_connection.assert_called_once()
        call_args = mock_connection_manager.send_to_connection.call_args[0]
        message = call_args[1]

        assert message.type == "data.content.complete"
        assert message.payload["messageId"] == "msg-1"
        assert message.payload["fullContent"] == "Full content here"
        assert message.payload["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_send_complete_custom_role(self, handler, mock_connection, sample_context, mock_connection_manager):
        """Test sending completion with custom role."""
        await handler.send_complete(mock_connection, sample_context, "msg-1", "Content", role="system")

        call_args = mock_connection_manager.send_to_connection.call_args[0]
        message = call_args[1]

        assert message.payload["role"] == "system"


class TestStreamHandlerConfiguration:
    """Test handler configuration options."""

    @pytest.mark.asyncio
    async def test_custom_chunk_size(self, mock_connection_manager, mock_connection, sample_context):
        """Test custom chunk size configuration."""
        handler = StreamHandler(mock_connection_manager, chunk_size=3, chunk_delay=0)
        content = "123456789"  # 9 chars = 3 chunks

        await handler.stream_response(mock_connection, sample_context, content)

        # Should send 3 chunks + 1 completion = 4 messages
        assert mock_connection_manager.send_to_connection.call_count == 4

    @pytest.mark.asyncio
    async def test_empty_content(self, handler, mock_connection, sample_context, mock_connection_manager):
        """Test streaming empty content."""
        await handler.stream_response(mock_connection, sample_context, "")

        # Should still send completion message
        calls = mock_connection_manager.send_to_connection.call_args_list
        assert any(c[0][1].type == "data.content.complete" for c in calls)
