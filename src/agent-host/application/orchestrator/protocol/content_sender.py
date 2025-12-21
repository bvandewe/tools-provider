"""Content streaming protocol sender.

Handles sending:
- Content chunks (data.content.chunk)
- Content completion (data.content.complete)
- Tool call notifications (data.tool.call)
- Tool results (data.tool.result)
"""

import asyncio
import logging
import uuid
from typing import TYPE_CHECKING

from application.protocol.core import create_message
from application.protocol.data import ContentChunkPayload, ContentCompletePayload, ToolCallPayload, ToolResultPayload

if TYPE_CHECKING:
    from application.orchestrator.context import ConversationContext
    from application.websocket.connection import Connection
    from application.websocket.manager import ConnectionManager

log = logging.getLogger(__name__)


class ContentSender:
    """Sends content streaming protocol messages to clients.

    This class encapsulates the logic for streaming content to clients,
    including agent responses, tool calls, and tool results.

    Attributes:
        _connection_manager: The WebSocket connection manager
        _default_chunk_size: Default size for content chunks
        _default_chunk_delay: Default delay between chunks (simulated streaming)

    Usage:
        sender = ContentSender(connection_manager)
        await sender.stream_content(connection, context, "Hello, world!")
        await sender.send_tool_call(connection, context, tool_id, tool_name, args)
    """

    def __init__(
        self,
        connection_manager: "ConnectionManager",
        default_chunk_size: int = 50,
        default_chunk_delay: float = 0.02,
    ):
        """Initialize the content sender.

        Args:
            connection_manager: The WebSocket connection manager for message delivery
            default_chunk_size: Default characters per chunk for streaming
            default_chunk_delay: Default delay between chunks in seconds
        """
        self._connection_manager = connection_manager
        self._default_chunk_size = default_chunk_size
        self._default_chunk_delay = default_chunk_delay

    async def stream_content(
        self,
        connection: "Connection",
        context: "ConversationContext",
        content: str,
        chunk_size: int | None = None,
        chunk_delay: float | None = None,
        message_id: str | None = None,
    ) -> str:
        """Stream content to client in chunks.

        Simulates streaming by sending content in chunks with small delays.
        Useful for displaying agent responses progressively.

        Args:
            connection: The WebSocket connection
            context: The conversation context
            content: The full content to stream
            chunk_size: Characters per chunk (uses default if None)
            chunk_delay: Delay between chunks in seconds (uses default if None)
            message_id: Optional message ID (generated if None)

        Returns:
            The message ID used for this stream
        """
        # Use defaults if not specified
        chunk_size = chunk_size or self._default_chunk_size
        chunk_delay = chunk_delay or self._default_chunk_delay

        # Generate a message ID if not provided
        if message_id is None:
            message_id = f"msg_{uuid.uuid4().hex[:12]}"

        # Stream in chunks
        for i in range(0, len(content), chunk_size):
            chunk = content[i : i + chunk_size]
            is_final = (i + chunk_size) >= len(content)

            chunk_message = create_message(
                message_type="data.content.chunk",
                payload=ContentChunkPayload(
                    content=chunk,
                    messageId=message_id,
                    final=is_final,
                ).model_dump(by_alias=True, exclude_none=True),
                conversation_id=context.conversation_id,
            )
            await self._connection_manager.send_to_connection(connection.connection_id, chunk_message)

            # Small delay to simulate streaming
            if not is_final:
                await asyncio.sleep(chunk_delay)

        # Send completion message
        complete_message = create_message(
            message_type="data.content.complete",
            payload=ContentCompletePayload(
                messageId=message_id,
                role="assistant",
                fullContent=content,
            ).model_dump(by_alias=True, exclude_none=True),
            conversation_id=context.conversation_id,
        )
        await self._connection_manager.send_to_connection(connection.connection_id, complete_message)

        log.debug(f"📤 Streamed content ({len(content)} chars) as message {message_id}")
        return message_id

    async def send_content_chunk(
        self,
        connection: "Connection",
        context: "ConversationContext",
        chunk: str,
        message_id: str,
        is_final: bool = False,
    ) -> None:
        """Send a single content chunk.

        For real-time streaming from LLM providers. Use this when
        you're receiving chunks from an external source.

        Args:
            connection: The WebSocket connection
            context: The conversation context
            chunk: The content chunk
            message_id: The message ID for this stream
            is_final: Whether this is the last chunk
        """
        chunk_message = create_message(
            message_type="data.content.chunk",
            payload=ContentChunkPayload(
                content=chunk,
                messageId=message_id,
                final=is_final,
            ).model_dump(by_alias=True, exclude_none=True),
            conversation_id=context.conversation_id,
        )
        await self._connection_manager.send_to_connection(connection.connection_id, chunk_message)

    async def send_content_complete(
        self,
        connection: "Connection",
        context: "ConversationContext",
        message_id: str,
        full_content: str,
        role: str = "assistant",
    ) -> None:
        """Send content completion message.

        Call this after streaming all chunks to finalize the message.

        Args:
            connection: The WebSocket connection
            context: The conversation context
            message_id: The message ID for this stream
            full_content: The complete content (for client reference)
            role: The message role ("assistant", "system")
        """
        complete_message = create_message(
            message_type="data.content.complete",
            payload=ContentCompletePayload(
                messageId=message_id,
                role=role,
                fullContent=full_content,
            ).model_dump(by_alias=True, exclude_none=True),
            conversation_id=context.conversation_id,
        )
        await self._connection_manager.send_to_connection(connection.connection_id, complete_message)
        log.debug(f"📤 Sent content complete for message {message_id}")

    async def send_tool_call(
        self,
        connection: "Connection",
        context: "ConversationContext",
        call_id: str,
        tool_name: str,
        arguments: dict | None = None,
    ) -> None:
        """Send tool call notification to client.

        Informs the client that a tool is being called, allowing
        the UI to display tool execution status.

        Args:
            connection: The WebSocket connection
            context: The conversation context
            call_id: Unique identifier for this tool call
            tool_name: Name of the tool being called
            arguments: Arguments passed to the tool
        """
        tool_message = create_message(
            message_type="data.tool.call",
            payload=ToolCallPayload(
                callId=call_id,
                toolName=tool_name,
                arguments=arguments or {},
            ).model_dump(by_alias=True, exclude_none=True),
            conversation_id=context.conversation_id,
        )
        await self._connection_manager.send_to_connection(connection.connection_id, tool_message)
        log.debug(f"📤 Sent tool call: {tool_name} ({call_id})")

    async def send_tool_result(
        self,
        connection: "Connection",
        context: "ConversationContext",
        call_id: str,
        tool_name: str,
        success: bool = True,
        result: str | dict | None = None,
        error: str | None = None,
        execution_time_ms: int | None = None,
    ) -> None:
        """Send tool result to client.

        Reports the outcome of a tool execution.

        Args:
            connection: The WebSocket connection
            context: The conversation context
            call_id: The tool call ID this result is for
            tool_name: Name of the tool that was called
            success: Whether the tool execution was successful
            result: The tool's result (if successful)
            error: Error message (if failed)
            execution_time_ms: How long the tool took to execute (integer ms)
        """
        result_message = create_message(
            message_type="data.tool.result",
            payload=ToolResultPayload(
                callId=call_id,
                toolName=tool_name,
                success=success,
                result=result if success else error,
                executionTimeMs=execution_time_ms,
            ).model_dump(by_alias=True, exclude_none=True),
            conversation_id=context.conversation_id,
        )
        await self._connection_manager.send_to_connection(connection.connection_id, result_message)

        if error:
            log.debug(f"📤 Sent tool error: {tool_name} ({call_id}): {error}")
        else:
            log.debug(f"📤 Sent tool result: {tool_name} ({call_id})")

    def generate_message_id(self) -> str:
        """Generate a unique message ID for content streaming.

        Returns:
            A unique message ID string
        """
        return f"msg_{uuid.uuid4().hex[:12]}"
