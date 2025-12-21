"""WebSocket Broadcast Handlers for Domain Events.

These handlers listen to domain events and broadcast corresponding
protocol messages to connected WebSocket clients.

The Repository automatically publishes domain events to the Mediator after
persistence, and the Mediator auto-discovers these handlers because
'application.events.websocket' is registered in main.py.

Pattern:
1. Domain emits event (e.g., MessageAddedDomainEvent)
2. This handler receives the event
3. Handler maps domain event to protocol message
4. Handler calls connection_manager.broadcast_to_conversation()
"""

import logging

from neuroglia.mediation import DomainEventHandler

from application.protocol.control import ConversationPausePayload
from application.protocol.core import create_message
from application.protocol.data import ContentCompletePayload, MessageAckPayload, ToolCallPayload, ToolResultPayload
from application.websocket.manager import ConnectionManager
from domain.events.conversation import (
    ConversationClearedDomainEvent,
    ConversationCompletedDomainEvent,
    ConversationPausedDomainEvent,
    ConversationResumedDomainEvent,
    ConversationStartedDomainEvent,
    ConversationTerminatedDomainEvent,
    ConversationTitleUpdatedDomainEvent,
    MessageAddedDomainEvent,
    MessageStatusUpdatedDomainEvent,
    ToolCallAddedDomainEvent,
    ToolResultAddedDomainEvent,
)

log = logging.getLogger(__name__)


# =============================================================================
# CONVERSATION LIFECYCLE HANDLERS
# =============================================================================


class ConversationStartedWebSocketHandler(DomainEventHandler[ConversationStartedDomainEvent]):
    """Broadcasts conversation started event to WebSocket clients.

    When a conversation is started, notify connected clients that the flow is beginning.
    """

    def __init__(self, connection_manager: ConnectionManager):
        super().__init__()
        self._manager = connection_manager

    async def handle_async(self, event: ConversationStartedDomainEvent) -> None:
        """Broadcast conversation started to all participants.

        Args:
            event: The domain event
        """
        log.info(f"📡 Broadcasting conversation.started for {event.aggregate_id}")

        message = create_message(
            message_type="control.conversation.started",
            payload={"startedAt": event.started_at.isoformat()},
            conversation_id=event.aggregate_id,
        )
        await self._manager.broadcast_to_conversation(event.aggregate_id, message)


class ConversationPausedWebSocketHandler(DomainEventHandler[ConversationPausedDomainEvent]):
    """Broadcasts conversation paused event to WebSocket clients."""

    def __init__(self, connection_manager: ConnectionManager):
        super().__init__()
        self._manager = connection_manager

    async def handle_async(self, event: ConversationPausedDomainEvent) -> None:
        """Broadcast conversation paused to all participants.

        Args:
            event: The domain event
        """
        log.info(f"📡 Broadcasting conversation.paused for {event.aggregate_id}")

        payload = ConversationPausePayload(
            reason="user_initiated",
            pausedAt=event.paused_at.isoformat(),
        )
        message = create_message(
            message_type="control.conversation.paused",
            payload=payload.model_dump(by_alias=True),
            conversation_id=event.aggregate_id,
        )
        await self._manager.broadcast_to_conversation(event.aggregate_id, message)


class ConversationResumedWebSocketHandler(DomainEventHandler[ConversationResumedDomainEvent]):
    """Broadcasts conversation resumed event to WebSocket clients."""

    def __init__(self, connection_manager: ConnectionManager):
        super().__init__()
        self._manager = connection_manager

    async def handle_async(self, event: ConversationResumedDomainEvent) -> None:
        """Broadcast conversation resumed to all participants.

        Args:
            event: The domain event
        """
        log.info(f"📡 Broadcasting conversation.resumed for {event.aggregate_id}")

        message = create_message(
            message_type="control.conversation.resumed",
            payload={"resumedAt": event.resumed_at.isoformat()},
            conversation_id=event.aggregate_id,
        )
        await self._manager.broadcast_to_conversation(event.aggregate_id, message)


class ConversationCompletedWebSocketHandler(DomainEventHandler[ConversationCompletedDomainEvent]):
    """Broadcasts conversation completed event to WebSocket clients."""

    def __init__(self, connection_manager: ConnectionManager):
        super().__init__()
        self._manager = connection_manager

    async def handle_async(self, event: ConversationCompletedDomainEvent) -> None:
        """Broadcast conversation completed to all participants.

        Args:
            event: The domain event
        """
        log.info(f"📡 Broadcasting conversation.completed for {event.aggregate_id}")

        message = create_message(
            message_type="control.conversation.completed",
            payload={
                "completedAt": event.completed_at.isoformat(),
                "summary": event.summary,
            },
            conversation_id=event.aggregate_id,
        )
        await self._manager.broadcast_to_conversation(event.aggregate_id, message)


class ConversationTerminatedWebSocketHandler(DomainEventHandler[ConversationTerminatedDomainEvent]):
    """Broadcasts conversation terminated event to WebSocket clients."""

    def __init__(self, connection_manager: ConnectionManager):
        super().__init__()
        self._manager = connection_manager

    async def handle_async(self, event: ConversationTerminatedDomainEvent) -> None:
        """Broadcast conversation terminated to all participants.

        Args:
            event: The domain event
        """
        log.info(f"📡 Broadcasting conversation.terminated for {event.aggregate_id}")

        message = create_message(
            message_type="control.conversation.terminated",
            payload={
                "reason": event.reason,
                "terminatedAt": event.terminated_at.isoformat(),
            },
            conversation_id=event.aggregate_id,
        )
        await self._manager.broadcast_to_conversation(event.aggregate_id, message)


class ConversationClearedWebSocketHandler(DomainEventHandler[ConversationClearedDomainEvent]):
    """Broadcasts conversation cleared event to WebSocket clients."""

    def __init__(self, connection_manager: ConnectionManager):
        super().__init__()
        self._manager = connection_manager

    async def handle_async(self, event: ConversationClearedDomainEvent) -> None:
        """Broadcast conversation cleared to all participants.

        Args:
            event: The domain event
        """
        log.info(f"📡 Broadcasting conversation.cleared for {event.aggregate_id}")

        message = create_message(
            message_type="control.conversation.cleared",
            payload={
                "keepSystem": event.keep_system,
                "clearedAt": event.cleared_at.isoformat(),
            },
            conversation_id=event.aggregate_id,
        )
        await self._manager.broadcast_to_conversation(event.aggregate_id, message)


class ConversationTitleUpdatedWebSocketHandler(DomainEventHandler[ConversationTitleUpdatedDomainEvent]):
    """Broadcasts conversation title updated event to WebSocket clients."""

    def __init__(self, connection_manager: ConnectionManager):
        super().__init__()
        self._manager = connection_manager

    async def handle_async(self, event: ConversationTitleUpdatedDomainEvent) -> None:
        """Broadcast title update to all participants.

        Args:
            event: The domain event
        """
        log.info(f"📡 Broadcasting conversation.title-updated for {event.aggregate_id}")

        message = create_message(
            message_type="control.conversation.title-updated",
            payload={
                "oldTitle": event.old_title,
                "newTitle": event.new_title,
            },
            conversation_id=event.aggregate_id,
        )
        await self._manager.broadcast_to_conversation(event.aggregate_id, message)


# =============================================================================
# MESSAGE HANDLERS
# =============================================================================


class MessageAddedWebSocketHandler(DomainEventHandler[MessageAddedDomainEvent]):
    """Broadcasts message added event to WebSocket clients.

    This is the primary handler for streaming chat messages to clients.
    When an assistant message is added, it gets broadcast as data.content.complete.

    Note: Empty assistant messages (pending/streaming) are skipped to avoid
    interfering with the real-time streaming flow in the orchestrator.
    """

    def __init__(self, connection_manager: ConnectionManager):
        super().__init__()
        self._manager = connection_manager

    async def handle_async(self, event: MessageAddedDomainEvent) -> None:
        """Broadcast message added to all participants.

        Args:
            event: The domain event
        """
        # For assistant messages, only broadcast if content is present
        # Empty content indicates a pending/streaming message that will be
        # streamed via the orchestrator's _run_agent_stream method
        if event.role == "assistant":
            if not event.content or not event.content.strip():
                log.debug(f"📡 Skipping empty assistant message broadcast for {event.message_id[:8]}...")
                return

            log.info(f"📡 Broadcasting message-added for {event.aggregate_id}, message={event.message_id[:8]}...")
            payload = ContentCompletePayload(
                messageId=event.message_id,
                role="assistant",
                fullContent=event.content,
            )
            message = create_message(
                message_type="data.content.complete",
                payload=payload.model_dump(by_alias=True),
                conversation_id=event.aggregate_id,
            )
        else:
            log.info(f"📡 Broadcasting message-added for {event.aggregate_id}, message={event.message_id[:8]}...")
            # For user messages, send acknowledgment
            payload_ack = MessageAckPayload(messageId=event.message_id)
            message = create_message(
                message_type="data.message.ack",
                payload=payload_ack.model_dump(by_alias=True),
                conversation_id=event.aggregate_id,
            )

        await self._manager.broadcast_to_conversation(event.aggregate_id, message)


class MessageStatusUpdatedWebSocketHandler(DomainEventHandler[MessageStatusUpdatedDomainEvent]):
    """Broadcasts message status updated event to WebSocket clients."""

    def __init__(self, connection_manager: ConnectionManager):
        super().__init__()
        self._manager = connection_manager

    async def handle_async(self, event: MessageStatusUpdatedDomainEvent) -> None:
        """Broadcast message status update to all participants.

        Args:
            event: The domain event
        """
        log.debug(f"📡 Broadcasting message-status-updated for message {event.message_id[:8]}...")

        message = create_message(
            message_type="data.message.status",
            payload={
                "messageId": event.message_id,
                "status": event.new_status,
            },
            conversation_id=event.aggregate_id,
        )
        await self._manager.broadcast_to_conversation(event.aggregate_id, message)


# =============================================================================
# TOOL EXECUTION HANDLERS (Phase 3)
# =============================================================================


class ToolCallAddedWebSocketHandler(DomainEventHandler[ToolCallAddedDomainEvent]):
    """Broadcasts tool call event to WebSocket clients.

    When the AI agent decides to call a tool, this handler notifies the
    connected client. For client-side tools, the client will execute the
    tool and send back the result via data.tool.result.
    """

    def __init__(self, connection_manager: ConnectionManager):
        super().__init__()
        self._manager = connection_manager

    async def handle_async(self, event: ToolCallAddedDomainEvent) -> None:
        """Broadcast tool call to all participants.

        Args:
            event: The domain event
        """
        log.info(f"📡 Broadcasting tool-call for {event.aggregate_id}, call_id={event.call_id[:8]}..., tool={event.tool_name}")

        payload = ToolCallPayload(
            callId=event.call_id,
            toolName=event.tool_name,
            arguments=event.arguments,
        )
        message = create_message(
            message_type="data.tool.call",
            payload=payload.model_dump(by_alias=True),
            conversation_id=event.aggregate_id,
        )
        await self._manager.broadcast_to_conversation(event.aggregate_id, message)


class ToolResultAddedWebSocketHandler(DomainEventHandler[ToolResultAddedDomainEvent]):
    """Broadcasts tool result event to WebSocket clients.

    When a tool execution completes (server-side or client-side), this handler
    notifies connected clients with the result for UI display.
    """

    def __init__(self, connection_manager: ConnectionManager):
        super().__init__()
        self._manager = connection_manager

    async def handle_async(self, event: ToolResultAddedDomainEvent) -> None:
        """Broadcast tool result to all participants.

        Args:
            event: The domain event
        """
        log.info(f"📡 Broadcasting tool-result for {event.aggregate_id}, call_id={event.call_id[:8]}..., success={event.success}")

        payload = ToolResultPayload(
            callId=event.call_id,
            toolName=event.tool_name,
            success=event.success,
            result=event.result,
            executionTimeMs=int(event.execution_time_ms) if event.execution_time_ms else None,
        )
        message = create_message(
            message_type="data.tool.result",
            payload=payload.model_dump(by_alias=True),
            conversation_id=event.aggregate_id,
        )
        await self._manager.broadcast_to_conversation(event.aggregate_id, message)
