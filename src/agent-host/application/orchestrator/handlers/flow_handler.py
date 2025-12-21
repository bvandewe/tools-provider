"""Flow handler for conversation flow control.

This handler manages the conversation flow state machine,
handling start, pause, and cancel operations.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from application.orchestrator.context import ConversationContext, OrchestratorState
from application.protocol.core import create_message

if TYPE_CHECKING:
    from application.websocket.connection import Connection
    from application.websocket.manager import ConnectionManager

log = logging.getLogger(__name__)


class FlowHandler:
    """Handles conversation flow control operations.

    Responsibilities:
    - Starting proactive/reactive conversation flows
    - Pausing active conversations
    - Cancelling ongoing operations

    This handler manages the conversation state machine transitions
    for flow control operations.
    """

    def __init__(
        self,
        connection_manager: "ConnectionManager",
    ):
        """Initialize the flow handler.

        Args:
            connection_manager: WebSocket connection manager for sending messages
        """
        self._connection_manager = connection_manager

    async def handle_flow_start(
        self,
        connection: "Connection",
        context: ConversationContext,
        proactive_runner: Callable[["Connection", ConversationContext], Awaitable[None]] | None = None,
        chat_input_sender: Callable[["Connection", bool], Awaitable[None]] | None = None,
    ) -> None:
        """Handle explicit flow start request from client.

        For proactive conversations, this triggers the template flow.
        For reactive, this is a no-op (flow starts with first message).

        Args:
            connection: The WebSocket connection
            context: The conversation context
            proactive_runner: Callback to run proactive flow (for template-based conversations)
            chat_input_sender: Callback to enable/disable chat input
        """
        log.info(f"▶️ Flow start requested: conversation={context.conversation_id}")

        if context.is_proactive and context.has_template:
            if context.state == OrchestratorState.READY:
                context.state = OrchestratorState.PRESENTING
                if proactive_runner:
                    # Run proactive flow in background task
                    asyncio.create_task(proactive_runner(connection, context))
        else:
            # Reactive mode - just ensure chat input is enabled
            if chat_input_sender:
                await chat_input_sender(connection, True)

    async def handle_flow_pause(
        self,
        connection: "Connection",
        context: ConversationContext,
        reason: str | None = None,
    ) -> None:
        """Handle flow pause request from client.

        Pauses the current conversation flow. The conversation can be
        resumed later with a flow start request.

        Args:
            connection: The WebSocket connection
            context: The conversation context
            reason: Optional pause reason
        """
        log.info(f"⏸️ Flow paused: conversation={context.conversation_id}, reason={reason}")
        context.state = OrchestratorState.PAUSED

        # Send pause acknowledgment
        pause_ack = create_message(
            message_type="control.conversation.pause",
            payload={
                "reason": reason or "user_requested",
                "pausedAt": datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            },
            conversation_id=context.conversation_id,
        )
        await self._connection_manager.send_to_connection(connection.connection_id, pause_ack)

        # TODO: Dispatch PauseConversationCommand to persist state

    async def handle_flow_cancel(
        self,
        connection: "Connection",
        context: ConversationContext,
        request_id: str | None = None,
    ) -> None:
        """Handle flow/request cancellation from client.

        Cancels the current operation and resets to ready state.
        If a specific request_id is provided, only that request is cancelled.

        Args:
            connection: The WebSocket connection
            context: The conversation context
            request_id: Optional specific request to cancel
        """
        log.info(f"🚫 Flow cancelled: conversation={context.conversation_id}")

        # Reset to ready state
        context.state = OrchestratorState.READY
        context.pending_widget_id = None
        context.pending_tool_call_id = None

        # Send cancellation acknowledgment
        cancel_ack = create_message(
            message_type="control.conversation.cancel",
            payload={
                "requestId": request_id,
                "cancelledAt": datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            },
            conversation_id=context.conversation_id,
        )
        await self._connection_manager.send_to_connection(connection.connection_id, cancel_ack)

        # TODO: Dispatch CancelOperationCommand if request_id provided

    async def handle_flow_resume(
        self,
        connection: "Connection",
        context: ConversationContext,
        proactive_runner: Callable[["Connection", ConversationContext], Awaitable[None]] | None = None,
        chat_input_sender: Callable[["Connection", bool], Awaitable[None]] | None = None,
    ) -> None:
        """Handle flow resume request after pause.

        Resumes a paused conversation from where it left off.

        Args:
            connection: The WebSocket connection
            context: The conversation context
            proactive_runner: Callback to run proactive flow (for template-based conversations)
            chat_input_sender: Callback to enable/disable chat input
        """
        if context.state != OrchestratorState.PAUSED:
            log.warning(f"Cannot resume from state {context.state}")
            return

        log.info(f"▶️ Flow resumed: conversation={context.conversation_id}")

        # Send resume acknowledgment
        resume_ack = create_message(
            message_type="control.conversation.resume",
            payload={
                "resumedAt": datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            },
            conversation_id=context.conversation_id,
        )
        await self._connection_manager.send_to_connection(connection.connection_id, resume_ack)

        # Resume the appropriate flow
        if context.is_proactive and context.has_template:
            context.state = OrchestratorState.PRESENTING
            if proactive_runner:
                asyncio.create_task(proactive_runner(connection, context))
        else:
            context.state = OrchestratorState.READY
            if chat_input_sender:
                await chat_input_sender(connection, True)

        # TODO: Dispatch ResumeConversationCommand to persist state
