"""Message handler for user text messages.

This handler processes user text messages in the conversation,
coordinating with the agent to generate responses.
"""

import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from neuroglia.mediation import Mediator

from application.orchestrator.context import ConversationContext, OrchestratorState
from application.protocol.core import create_message

if TYPE_CHECKING:
    from application.websocket.connection import Connection
    from application.websocket.manager import ConnectionManager

log = logging.getLogger(__name__)


class MessageHandler:
    """Handles user text messages in the conversation.

    Responsibilities:
    - Validates conversation state for message processing
    - Sends acknowledgment to client
    - Persists user message via domain command
    - Delegates to agent runner for response generation
    - Persists assistant response

    This handler coordinates the full message processing flow while
    delegating actual agent execution to the provided callback.
    """

    def __init__(
        self,
        mediator: Mediator,
        connection_manager: "ConnectionManager",
    ):
        """Initialize the message handler.

        Args:
            mediator: Neuroglia Mediator for CQRS command/query dispatch
            connection_manager: WebSocket connection manager for sending messages
        """
        self._mediator = mediator
        self._connection_manager = connection_manager

    async def handle_user_message(
        self,
        connection: "Connection",
        context: ConversationContext,
        content: str,
        agent_runner: Callable[["Connection", ConversationContext, str], Awaitable[str | None]],
        error_sender: Callable[["Connection", str, str], Awaitable[None]],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Handle a user message from the client.

        Dispatches a domain command to process the message, then streams
        agent response back to the client.

        Args:
            connection: The WebSocket connection
            context: The conversation context
            content: The message content
            agent_runner: Callback to run agent and stream response
            error_sender: Callback to send error messages
            metadata: Optional message metadata
        """
        if context.state not in (OrchestratorState.READY, OrchestratorState.SUSPENDED):
            log.warning(f"Cannot process message in state {context.state}")
            await error_sender(connection, "INVALID_STATE", f"Cannot send message in state: {context.state}")
            return

        context.state = OrchestratorState.PROCESSING
        context.last_activity = datetime.now(UTC)

        try:
            # Send acknowledgment
            await self._send_message_ack(connection, context)

            # Persist user message via domain command
            assistant_message_id = await self._persist_user_message(context, content)

            # Run agent and stream response
            response_content = await agent_runner(connection, context, content)

            # Persist assistant message if we got a response and have message ID
            if response_content and assistant_message_id:
                await self._complete_assistant_message(context, assistant_message_id, response_content)

            context.state = OrchestratorState.READY

        except Exception as e:
            log.exception(f"Error handling user message: {e}")
            context.state = OrchestratorState.ERROR
            await error_sender(connection, "MESSAGE_ERROR", str(e))

    async def _send_message_ack(
        self,
        connection: "Connection",
        context: ConversationContext,
    ) -> None:
        """Send message acknowledgment to client."""
        ack_message = create_message(
            message_type="data.message.ack",
            payload={"status": "received"},
            conversation_id=context.conversation_id,
        )
        await self._connection_manager.send_to_connection(connection.connection_id, ack_message)

    async def _persist_user_message(
        self,
        context: ConversationContext,
        content: str,
    ) -> str | None:
        """Persist user message via domain command.

        Returns:
            The assistant message ID for later completion, or None if persistence failed
        """
        from application.commands import SendMessageCommand

        send_result = await self._mediator.execute_async(
            SendMessageCommand(
                conversation_id=context.conversation_id,
                content=content,
                user_info={"sub": context.user_id},
            )
        )

        if not send_result.is_success:
            log.warning(f"Failed to persist user message: {send_result.errors}")
            return None

        if send_result.data:
            return send_result.data.assistant_message_id

        return None

    async def _complete_assistant_message(
        self,
        context: ConversationContext,
        message_id: str,
        content: str,
    ) -> None:
        """Complete the pending assistant message with final content."""
        from application.commands.conversation.complete_message_command import CompleteMessageCommand

        complete_result = await self._mediator.execute_async(
            CompleteMessageCommand(
                conversation_id=context.conversation_id,
                message_id=message_id,
                content=content,
                user_info={"sub": context.user_id},
            )
        )

        if not complete_result.is_success:
            log.warning(f"Failed to complete assistant message: {complete_result.errors}")
