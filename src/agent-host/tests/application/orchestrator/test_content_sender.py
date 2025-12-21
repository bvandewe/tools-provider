"""Unit tests for ContentSender.

Tests cover:
- Content streaming with chunks
- Single chunk sending
- Content completion sending
- Tool call notifications
- Tool result sending
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from application.orchestrator.context import ConversationContext
from application.orchestrator.protocol.content_sender import ContentSender


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
    """Create a ContentSender with mocked dependencies."""
    return ContentSender(mock_connection_manager, default_chunk_size=10, default_chunk_delay=0)


def get_sent_message(mock_connection_manager, call_index=-1):
    """Extract the ProtocolMessage from the mock call."""
    return mock_connection_manager.send_to_connection.call_args_list[call_index][0][1]


class TestContentSenderStreamContent:
    """Test content streaming."""

    @pytest.mark.asyncio
    async def test_stream_content_single_chunk(self, sender, mock_connection, sample_context, mock_connection_manager):
        """Test streaming content that fits in one chunk."""
        content = "Hello!"

        message_id = await sender.stream_content(mock_connection, sample_context, content, chunk_size=100)

        assert message_id.startswith("msg_")

        # Should send 2 messages: 1 chunk (final) + 1 complete
        assert mock_connection_manager.send_to_connection.call_count == 2

        # First call: chunk
        chunk_msg = get_sent_message(mock_connection_manager, 0)
        assert chunk_msg.type == "data.content.chunk"
        assert chunk_msg.payload["content"] == "Hello!"
        assert chunk_msg.payload["final"] is True

        # Second call: complete
        complete_msg = get_sent_message(mock_connection_manager, 1)
        assert complete_msg.type == "data.content.complete"
        assert complete_msg.payload["fullContent"] == "Hello!"
        assert complete_msg.payload["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_stream_content_multiple_chunks(self, sender, mock_connection, sample_context, mock_connection_manager):
        """Test streaming content split into multiple chunks."""
        content = "Hello, World!"  # 13 chars with default chunk_size=10

        await sender.stream_content(mock_connection, sample_context, content)

        # Should send: 2 chunks + 1 complete = 3 messages
        assert mock_connection_manager.send_to_connection.call_count == 3

        # First chunk (not final)
        chunk1 = get_sent_message(mock_connection_manager, 0)
        assert chunk1.type == "data.content.chunk"
        assert chunk1.payload["content"] == "Hello, Wor"
        assert chunk1.payload["final"] is False

        # Second chunk (final)
        chunk2 = get_sent_message(mock_connection_manager, 1)
        assert chunk2.payload["content"] == "ld!"
        assert chunk2.payload["final"] is True

    @pytest.mark.asyncio
    async def test_stream_content_custom_message_id(self, sender, mock_connection, sample_context, mock_connection_manager):
        """Test streaming with custom message ID."""
        message_id = await sender.stream_content(
            mock_connection,
            sample_context,
            "Test",
            message_id="custom-msg-id",
        )

        assert message_id == "custom-msg-id"

        chunk_msg = get_sent_message(mock_connection_manager, 0)
        assert chunk_msg.payload["messageId"] == "custom-msg-id"

    @pytest.mark.asyncio
    async def test_stream_content_conversation_id(self, sender, mock_connection, sample_context, mock_connection_manager):
        """Test that conversation ID is included in messages."""
        await sender.stream_content(mock_connection, sample_context, "Hi")

        for call in mock_connection_manager.send_to_connection.call_args_list:
            message = call[0][1]
            assert message.conversation_id == "conv-456"


class TestContentSenderChunks:
    """Test individual chunk sending."""

    @pytest.mark.asyncio
    async def test_send_content_chunk(self, sender, mock_connection, sample_context, mock_connection_manager):
        """Test sending a single content chunk."""
        await sender.send_content_chunk(
            connection=mock_connection,
            context=sample_context,
            chunk="Hello",
            message_id="msg-abc",
            is_final=False,
        )

        message = get_sent_message(mock_connection_manager)
        assert message.type == "data.content.chunk"
        assert message.payload["content"] == "Hello"
        assert message.payload["messageId"] == "msg-abc"
        assert message.payload["final"] is False

    @pytest.mark.asyncio
    async def test_send_content_chunk_final(self, sender, mock_connection, sample_context, mock_connection_manager):
        """Test sending final content chunk."""
        await sender.send_content_chunk(
            connection=mock_connection,
            context=sample_context,
            chunk=" World!",
            message_id="msg-xyz",
            is_final=True,
        )

        payload = get_sent_message(mock_connection_manager).payload
        assert payload["final"] is True


class TestContentSenderComplete:
    """Test content completion sending."""

    @pytest.mark.asyncio
    async def test_send_content_complete(self, sender, mock_connection, sample_context, mock_connection_manager):
        """Test sending content completion message."""
        await sender.send_content_complete(
            connection=mock_connection,
            context=sample_context,
            message_id="msg-123",
            full_content="Complete message here",
        )

        message = get_sent_message(mock_connection_manager)
        assert message.type == "data.content.complete"
        assert message.payload["messageId"] == "msg-123"
        assert message.payload["fullContent"] == "Complete message here"
        assert message.payload["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_send_content_complete_system_role(self, sender, mock_connection, sample_context, mock_connection_manager):
        """Test sending content completion with system role."""
        await sender.send_content_complete(
            connection=mock_connection,
            context=sample_context,
            message_id="msg-456",
            full_content="System notification",
            role="system",
        )

        payload = get_sent_message(mock_connection_manager).payload
        assert payload["role"] == "system"


class TestContentSenderToolCall:
    """Test tool call notification sending."""

    @pytest.mark.asyncio
    async def test_send_tool_call(self, sender, mock_connection, sample_context, mock_connection_manager):
        """Test sending tool call notification."""
        await sender.send_tool_call(
            connection=mock_connection,
            context=sample_context,
            call_id="call-abc",
            tool_name="get_weather",
            arguments={"city": "Seattle", "units": "celsius"},
        )

        message = get_sent_message(mock_connection_manager)
        assert message.type == "data.tool.call"
        assert message.conversation_id == "conv-456"

        payload = message.payload
        assert payload["callId"] == "call-abc"
        assert payload["toolName"] == "get_weather"
        assert payload["arguments"]["city"] == "Seattle"

    @pytest.mark.asyncio
    async def test_send_tool_call_no_arguments(self, sender, mock_connection, sample_context, mock_connection_manager):
        """Test sending tool call without arguments."""
        await sender.send_tool_call(
            connection=mock_connection,
            context=sample_context,
            call_id="call-xyz",
            tool_name="get_current_time",
        )

        payload = get_sent_message(mock_connection_manager).payload
        assert payload["arguments"] == {}


class TestContentSenderToolResult:
    """Test tool result sending."""

    @pytest.mark.asyncio
    async def test_send_tool_result_success(self, sender, mock_connection, sample_context, mock_connection_manager):
        """Test sending successful tool result."""
        await sender.send_tool_result(
            connection=mock_connection,
            context=sample_context,
            call_id="call-123",
            tool_name="get_weather",
            success=True,
            result={"temperature": 72, "condition": "sunny"},
            execution_time_ms=150,  # int, not float
        )

        message = get_sent_message(mock_connection_manager)
        assert message.type == "data.tool.result"

        payload = message.payload
        assert payload["callId"] == "call-123"
        assert payload["toolName"] == "get_weather"
        assert payload["result"]["temperature"] == 72
        assert payload["executionTimeMs"] == 150
        assert payload["success"] is True

    @pytest.mark.asyncio
    async def test_send_tool_result_error(self, sender, mock_connection, sample_context, mock_connection_manager):
        """Test sending tool error result."""
        await sender.send_tool_result(
            connection=mock_connection,
            context=sample_context,
            call_id="call-456",
            tool_name="get_stock_price",
            success=False,
            error="API rate limit exceeded",
            execution_time_ms=50,  # int, not float
        )

        payload = get_sent_message(mock_connection_manager).payload
        assert payload["success"] is False
        # Error is placed in result field when success=False
        assert payload["result"] == "API rate limit exceeded"

    @pytest.mark.asyncio
    async def test_send_tool_result_string_result(self, sender, mock_connection, sample_context, mock_connection_manager):
        """Test sending tool result with string output."""
        await sender.send_tool_result(
            connection=mock_connection,
            context=sample_context,
            call_id="call-789",
            tool_name="execute_query",
            success=True,
            result="Query returned 42 rows",
        )

        payload = get_sent_message(mock_connection_manager).payload
        assert payload["result"] == "Query returned 42 rows"
        assert payload["success"] is True


class TestContentSenderMessageId:
    """Test message ID generation."""

    def test_generate_message_id(self, sender):
        """Test message ID generation format."""
        msg_id = sender.generate_message_id()

        assert msg_id.startswith("msg_")
        assert len(msg_id) == 16  # "msg_" + 12 hex chars

    def test_generate_message_id_unique(self, sender):
        """Test that message IDs are unique."""
        ids = [sender.generate_message_id() for _ in range(100)]
        assert len(set(ids)) == 100
