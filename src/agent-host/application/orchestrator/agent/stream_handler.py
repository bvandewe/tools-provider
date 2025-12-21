"""Stream handling for agent responses.

This module provides the StreamHandler class which handles streaming
content to WebSocket clients in chunks.
"""

import asyncio
import logging
import uuid
from typing import TYPE_CHECKING, Any, Literal, Protocol

from application.orchestrator.context import ConversationContext
from application.protocol.core import ProtocolMessage, create_message
from application.protocol.data import ContentChunkPayload, ContentCompletePayload

if TYPE_CHECKING:
    from application.websocket.connection import Connection

log = logging.getLogger(__name__)

# Type alias for content role
ContentRole = Literal["assistant", "user", "system"]


class ConnectionManagerProtocol(Protocol):
    """Protocol for connection manager interface."""

    async def send_to_connection(self, connection_id: str, message: ProtocolMessage[Any]) -> bool:
        """Send a message to a specific connection."""
        ...


class StreamHandler:
    """Handles streaming content to WebSocket clients.

    Streams content in configurable chunks with optional delays to simulate
    real-time generation. Sends both chunk messages and completion messages.

    Example:
        >>> handler = StreamHandler(connection_manager, chunk_size=50)
        >>> await handler.stream_response(connection, context, "Hello world!")
    """

    def __init__(
        self,
        connection_manager: ConnectionManagerProtocol,
        chunk_size: int = 50,
        chunk_delay: float = 0.02,
    ) -> None:
        """Initialize the StreamHandler.

        Args:
            connection_manager: Manager for WebSocket connections
            chunk_size: Number of characters per chunk (default: 50)
            chunk_delay: Delay between chunks in seconds (default: 0.02)
        """
        self._connection_manager = connection_manager
        self._chunk_size = chunk_size
        self._chunk_delay = chunk_delay

    async def stream_response(
        self,
        connection: "Connection",
        context: ConversationContext,
        content: str,
    ) -> str:
        """Stream content to client in chunks.

        Sends content in chunks with a small delay between each to simulate
        streaming. Sends a completion message when done.

        Args:
            connection: The WebSocket connection
            context: The conversation context
            content: The content to stream

        Returns:
            The message ID used for the streamed content
        """
        # Generate a message ID for this content
        message_id = f"msg_{uuid.uuid4().hex[:12]}"

        # Stream in chunks
        for i in range(0, len(content), self._chunk_size):
            chunk = content[i : i + self._chunk_size]
            is_final = (i + self._chunk_size) >= len(content)

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
            if self._chunk_delay > 0:
                await asyncio.sleep(self._chunk_delay)

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

        return message_id

    async def send_chunk(
        self,
        connection: "Connection",
        context: ConversationContext,
        message_id: str,
        chunk: str,
        is_final: bool = False,
    ) -> None:
        """Send a single content chunk to the client.

        Args:
            connection: The WebSocket connection
            context: The conversation context
            message_id: The message ID for this stream
            chunk: The content chunk to send
            is_final: Whether this is the final chunk
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

    async def send_complete(
        self,
        connection: "Connection",
        context: ConversationContext,
        message_id: str,
        full_content: str,
        role: ContentRole = "assistant",
    ) -> None:
        """Send the completion message for a stream.

        Args:
            connection: The WebSocket connection
            context: The conversation context
            message_id: The message ID for this stream
            full_content: The complete accumulated content
            role: The message role (default: "assistant")
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
