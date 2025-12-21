"""Control Plane Message Handlers.

Handles control-level protocol messages for:
- Conversation configuration and state
- Widget state management
- Widget validation
- Flow control (start, pause, resume, cancel)
- Navigation (next, previous, skip)

These handlers receive messages from clients and interact with the domain layer
to manage conversation state.
"""

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from application.protocol.control import (
    ConversationConfigPayload,
    FlowCancelPayload,
    FlowPausePayload,
    FlowStartPayload,
    ItemContextPayload,
    NavigationPayload,
    WidgetDismissedPayload,
    WidgetMovedPayload,
    WidgetResizedPayload,
    WidgetStatePayload,
    WidgetValidationPayload,
)
from application.protocol.core import ProtocolMessage, create_message
from application.websocket.connection import Connection
from application.websocket.handlers.base import BaseHandler

if TYPE_CHECKING:
    from application.websocket.manager import ConnectionManager

log = logging.getLogger(__name__)


# =============================================================================
# CONVERSATION HANDLERS
# =============================================================================


class ConversationConfigHandler(BaseHandler[ConversationConfigPayload]):
    """Handles control.conversation.config messages.

    This message is typically sent from the server to the client, but the client
    may also request configuration refresh.
    """

    payload_type = ConversationConfigPayload

    def __init__(self, connection_manager: "ConnectionManager"):
        """Initialize with reference to connection manager.

        Args:
            connection_manager: The ConnectionManager for sending responses
        """
        super().__init__()
        self._manager = connection_manager

    async def process(
        self,
        connection: Connection,
        message: ProtocolMessage[Any],
        payload: ConversationConfigPayload,
    ) -> None:
        """Process conversation config request.

        Args:
            connection: The connection that sent the message
            message: The full protocol message
            payload: The validated config payload
        """
        log.info(f"📋 Conversation config received from {connection.connection_id[:8]}... for template {payload.template_id}")

        # Store config in connection context for reference
        # This allows other handlers to access the conversation settings
        if not hasattr(connection, "conversation_config"):
            connection.conversation_config = {}  # type: ignore[attr-defined]
        connection.conversation_config = payload.model_dump()  # type: ignore[attr-defined]

        log.debug(f"Stored conversation config: template={payload.template_name}, items={payload.total_items}")


# =============================================================================
# WIDGET STATE HANDLERS
# =============================================================================


class WidgetStateHandler(BaseHandler[WidgetStatePayload]):
    """Handles control.widget.state messages.

    Server sends these to control widget interactivity:
    - active: Widget is editable
    - readonly: Widget displays value but not editable
    - disabled: Widget is grayed out
    - hidden: Widget is not visible
    """

    payload_type = WidgetStatePayload

    def __init__(self, connection_manager: "ConnectionManager"):
        """Initialize with reference to connection manager.

        Args:
            connection_manager: The ConnectionManager for broadcasting
        """
        super().__init__()
        self._manager = connection_manager

    async def process(
        self,
        connection: Connection,
        message: ProtocolMessage[Any],
        payload: WidgetStatePayload,
    ) -> None:
        """Process widget state update.

        Args:
            connection: The connection that sent the message
            message: The full protocol message
            payload: The validated state payload
        """
        log.info(f"🔄 Widget state update: widget={payload.widget_id}, state={payload.state}")

        # If this is from the server (via domain event handler), broadcast to all participants
        # The connection might be the trigger, broadcast to all in the conversation
        if connection.conversation_id:
            state_message = create_message(
                message_type="control.widget.state",
                payload=payload.model_dump(by_alias=True),
                conversation_id=connection.conversation_id,
            )
            await self._manager.broadcast_to_conversation(connection.conversation_id, state_message)
        else:
            # Single connection update
            state_message = create_message(
                message_type="control.widget.state",
                payload=payload.model_dump(by_alias=True),
            )
            await self._manager.send_to_connection(connection.connection_id, state_message)


class WidgetValidationHandler(BaseHandler[WidgetValidationPayload]):
    """Handles control.widget.validation messages.

    Server sends these after validating a widget response:
    - valid: Response is acceptable
    - invalid: Response has validation errors with messages
    """

    payload_type = WidgetValidationPayload

    def __init__(self, connection_manager: "ConnectionManager"):
        """Initialize with reference to connection manager.

        Args:
            connection_manager: The ConnectionManager for sending responses
        """
        super().__init__()
        self._manager = connection_manager

    async def process(
        self,
        connection: Connection,
        message: ProtocolMessage[Any],
        payload: WidgetValidationPayload,
    ) -> None:
        """Process widget validation result.

        Args:
            connection: The connection that sent the message
            message: The full protocol message
            payload: The validated validation payload
        """
        log.info(f"✅ Widget validation: widget={payload.widget_id}, valid={payload.valid}")

        # Send validation result back to the client
        validation_message = create_message(
            message_type="control.widget.validation",
            payload=payload.model_dump(by_alias=True),
            conversation_id=connection.conversation_id,
        )
        await self._manager.send_to_connection(connection.connection_id, validation_message)


class WidgetMovedHandler(BaseHandler[WidgetMovedPayload]):
    """Handles control.widget.moved messages from canvas mode.

    Client notifies server when user drags a widget to a new position.
    """

    payload_type = WidgetMovedPayload

    def __init__(self, connection_manager: "ConnectionManager"):
        """Initialize with reference to connection manager.

        Args:
            connection_manager: The ConnectionManager for broadcasting
        """
        super().__init__()
        self._manager = connection_manager

    async def process(
        self,
        connection: Connection,
        message: ProtocolMessage[Any],
        payload: WidgetMovedPayload,
    ) -> None:
        """Process widget move notification.

        Args:
            connection: The connection that sent the message
            message: The full protocol message
            payload: The validated move payload
        """
        log.debug(f"📍 Widget moved: widget={payload.widget_id}, position=({payload.position.x}, {payload.position.y})")

        # Broadcast to other participants in the conversation
        if connection.conversation_id:
            moved_message = create_message(
                message_type="control.widget.moved",
                payload=payload.model_dump(by_alias=True),
                conversation_id=connection.conversation_id,
            )
            # Broadcast but exclude the sender to avoid echo
            for conn in self._manager.get_conversation_connections(connection.conversation_id):
                if conn.connection_id != connection.connection_id:
                    await self._manager.send_to_connection(conn.connection_id, moved_message)


class WidgetResizedHandler(BaseHandler[WidgetResizedPayload]):
    """Handles control.widget.resized messages from canvas mode.

    Client notifies server when user resizes a widget.
    """

    payload_type = WidgetResizedPayload

    def __init__(self, connection_manager: "ConnectionManager"):
        """Initialize with reference to connection manager.

        Args:
            connection_manager: The ConnectionManager for broadcasting
        """
        super().__init__()
        self._manager = connection_manager

    async def process(
        self,
        connection: Connection,
        message: ProtocolMessage[Any],
        payload: WidgetResizedPayload,
    ) -> None:
        """Process widget resize notification.

        Args:
            connection: The connection that sent the message
            message: The full protocol message
            payload: The validated resize payload
        """
        log.debug(f"📐 Widget resized: widget={payload.widget_id}, dimensions=({payload.dimensions.width}x{payload.dimensions.height})")

        # Broadcast to other participants in the conversation
        if connection.conversation_id:
            resized_message = create_message(
                message_type="control.widget.resized",
                payload=payload.model_dump(by_alias=True),
                conversation_id=connection.conversation_id,
            )
            for conn in self._manager.get_conversation_connections(connection.conversation_id):
                if conn.connection_id != connection.connection_id:
                    await self._manager.send_to_connection(conn.connection_id, resized_message)


class WidgetDismissedHandler(BaseHandler[WidgetDismissedPayload]):
    """Handles control.widget.dismissed messages.

    Client notifies server when user dismisses a widget.
    """

    payload_type = WidgetDismissedPayload

    def __init__(self, connection_manager: "ConnectionManager"):
        """Initialize with reference to connection manager.

        Args:
            connection_manager: The ConnectionManager for handling dismissal
        """
        super().__init__()
        self._manager = connection_manager

    async def process(
        self,
        connection: Connection,
        message: ProtocolMessage[Any],
        payload: WidgetDismissedPayload,
    ) -> None:
        """Process widget dismissal.

        Args:
            connection: The connection that sent the message
            message: The full protocol message
            payload: The validated dismissal payload
        """
        log.info(f"❌ Widget dismissed: widget={payload.widget_id}, action={payload.action}")

        # TODO: Dispatch domain command to record dismissal
        # For now, just acknowledge by broadcasting state change to hidden
        state_payload = WidgetStatePayload(
            widgetId=payload.widget_id,
            state="hidden",
            reason=f"dismissed:{payload.action}",
        )
        state_message = create_message(
            message_type="control.widget.state",
            payload=state_payload.model_dump(by_alias=True),
            conversation_id=connection.conversation_id,
        )
        await self._manager.send_to_connection(connection.connection_id, state_message)


# =============================================================================
# FLOW CONTROL HANDLERS
# =============================================================================


class FlowStartHandler(BaseHandler[FlowStartPayload]):
    """Handles control.flow.start messages.

    Client requests to start the conversation flow (proactive agent mode).
    Delegates to Orchestrator for CQRS-based flow management.
    """

    payload_type = FlowStartPayload

    def __init__(self, connection_manager: "ConnectionManager"):
        """Initialize with reference to connection manager.

        Args:
            connection_manager: The ConnectionManager for sending responses
        """
        super().__init__()
        self._manager = connection_manager

    async def process(
        self,
        connection: Connection,
        message: ProtocolMessage[Any],
        payload: FlowStartPayload | dict[str, Any],
    ) -> None:
        """Process flow start request.

        Delegates to Orchestrator which:
        1. Validates flow can be started
        2. Dispatches StartFlowCommand via Mediator
        3. Sends first item context to client

        Args:
            connection: The connection that sent the message
            message: The full protocol message
            payload: The validated start payload (empty)
        """
        log.info(f"▶️ Flow start requested by {connection.connection_id[:8]}...")

        # Delegate to orchestrator for CQRS-based processing
        orchestrator = getattr(self._manager, "_orchestrator", None)
        if orchestrator:
            await orchestrator.handle_flow_start(connection=connection)
        else:
            # Fallback: send placeholder item context
            log.warning("No orchestrator configured - using fallback flow start")
            item_context = ItemContextPayload(
                itemId="item-1",
                itemIndex=0,
                totalItems=1,
                itemTitle="Getting Started",
                enableChatInput=True,
                timeLimitSeconds=None,
                showRemainingTime=False,
                widgetCompletionBehavior="readonly",
                conversationDeadline=None,
            )
            context_message = create_message(
                message_type="control.item.context",
                payload=item_context.model_dump(by_alias=True),
                conversation_id=connection.conversation_id,
            )
            await self._manager.send_to_connection(connection.connection_id, context_message)


class FlowPauseHandler(BaseHandler[FlowPausePayload]):
    """Handles control.flow.pause messages.

    Client requests to pause the current flow.
    Delegates to Orchestrator for CQRS-based state management.
    """

    payload_type = FlowPausePayload

    def __init__(self, connection_manager: "ConnectionManager"):
        """Initialize with reference to connection manager.

        Args:
            connection_manager: The ConnectionManager for sending responses
        """
        super().__init__()
        self._manager = connection_manager

    async def process(
        self,
        connection: Connection,
        message: ProtocolMessage[Any],
        payload: FlowPausePayload,
    ) -> None:
        """Process flow pause request.

        Delegates to Orchestrator which:
        1. Validates flow can be paused
        2. Dispatches PauseFlowCommand via Mediator
        3. Sends pause acknowledgment to client

        Args:
            connection: The connection that sent the message
            message: The full protocol message
            payload: The validated pause payload
        """
        log.info(f"⏸️ Flow pause requested: reason={payload.reason}")

        # Delegate to orchestrator for CQRS-based processing
        orchestrator = getattr(self._manager, "_orchestrator", None)
        if orchestrator:
            await orchestrator.handle_flow_pause(
                connection=connection,
                reason=payload.reason,
            )
        else:
            # Fallback: acknowledge the pause directly
            log.warning("No orchestrator configured - using fallback pause handling")
            pause_ack = create_message(
                message_type="control.flow.paused",
                payload={"reason": payload.reason, "pausedAt": datetime.now(UTC).isoformat()},
                conversation_id=connection.conversation_id,
            )
            await self._manager.send_to_connection(connection.connection_id, pause_ack)


class FlowCancelHandler(BaseHandler[FlowCancelPayload]):
    """Handles control.flow.cancel messages.

    Client requests to cancel the current operation.
    Delegates to Orchestrator for CQRS-based cancellation.
    """

    payload_type = FlowCancelPayload

    def __init__(self, connection_manager: "ConnectionManager"):
        """Initialize with reference to connection manager.

        Args:
            connection_manager: The ConnectionManager for sending responses
        """
        super().__init__()
        self._manager = connection_manager

    async def process(
        self,
        connection: Connection,
        message: ProtocolMessage[Any],
        payload: FlowCancelPayload,
    ) -> None:
        """Process flow cancel request.

        Delegates to Orchestrator which:
        1. Cancels any pending operations
        2. Dispatches CancelFlowCommand via Mediator
        3. Sends cancellation acknowledgment to client

        Args:
            connection: The connection that sent the message
            message: The full protocol message
            payload: The validated cancel payload
        """
        log.info(f"🚫 Flow cancel requested: request_id={payload.request_id}")

        # Delegate to orchestrator for CQRS-based processing
        orchestrator = getattr(self._manager, "_orchestrator", None)
        if orchestrator:
            await orchestrator.handle_flow_cancel(
                connection=connection,
                request_id=payload.request_id,
            )
        else:
            # Fallback: acknowledge the cancel directly
            log.warning("No orchestrator configured - using fallback cancel handling")
            cancel_ack = create_message(
                message_type="control.flow.cancelled",
                payload={"requestId": payload.request_id, "cancelledAt": datetime.now(UTC).isoformat()},
                conversation_id=connection.conversation_id,
            )
            await self._manager.send_to_connection(connection.connection_id, cancel_ack)


# =============================================================================
# NAVIGATION HANDLERS
# =============================================================================


class NavigationNextHandler(BaseHandler[NavigationPayload]):
    """Handles control.navigation.next messages.

    Client requests to advance to the next item.
    """

    payload_type = NavigationPayload

    def __init__(self, connection_manager: "ConnectionManager"):
        """Initialize with reference to connection manager.

        Args:
            connection_manager: The ConnectionManager for sending responses
        """
        super().__init__()
        self._manager = connection_manager

    async def process(
        self,
        connection: Connection,
        message: ProtocolMessage[Any],
        payload: NavigationPayload,
    ) -> None:
        """Process navigation next request.

        Args:
            connection: The connection that sent the message
            message: The full protocol message
            payload: The validated navigation payload
        """
        log.info(f"➡️ Navigation next from item={payload.current_item_id}")

        # TODO: Dispatch domain command to navigate to next item
        # For now, acknowledge the navigation
        # The actual item context update will come from a domain event handler


class NavigationPreviousHandler(BaseHandler[NavigationPayload]):
    """Handles control.navigation.previous messages.

    Client requests to go back to the previous item.
    """

    payload_type = NavigationPayload

    def __init__(self, connection_manager: "ConnectionManager"):
        """Initialize with reference to connection manager.

        Args:
            connection_manager: The ConnectionManager for sending responses
        """
        super().__init__()
        self._manager = connection_manager

    async def process(
        self,
        connection: Connection,
        message: ProtocolMessage[Any],
        payload: NavigationPayload,
    ) -> None:
        """Process navigation previous request.

        Args:
            connection: The connection that sent the message
            message: The full protocol message
            payload: The validated navigation payload
        """
        log.info(f"⬅️ Navigation previous from item={payload.current_item_id}")

        # TODO: Dispatch domain command to navigate to previous item
        # Validate that backward navigation is allowed per conversation config


class NavigationSkipHandler(BaseHandler[NavigationPayload]):
    """Handles control.navigation.skip messages.

    Client requests to skip the current item.
    """

    payload_type = NavigationPayload

    def __init__(self, connection_manager: "ConnectionManager"):
        """Initialize with reference to connection manager.

        Args:
            connection_manager: The ConnectionManager for sending responses
        """
        super().__init__()
        self._manager = connection_manager

    async def process(
        self,
        connection: Connection,
        message: ProtocolMessage[Any],
        payload: NavigationPayload,
    ) -> None:
        """Process navigation skip request.

        Args:
            connection: The connection that sent the message
            message: The full protocol message
            payload: The validated navigation payload
        """
        log.info(f"⏭️ Navigation skip from item={payload.current_item_id}, reason={payload.reason}")

        # TODO: Dispatch domain command to skip the current item
        # Validate that skip is allowed per conversation config


# =============================================================================
# MODEL CHANGE HANDLERS
# =============================================================================


class ModelChangeHandler(BaseHandler["ModelChangePayload"]):
    """Handles control.conversation.model messages.

    Client request to change the LLM model for the conversation.
    This allows the UI to present a model selector and let users switch models mid-conversation.
    """

    payload_type = None  # We'll validate manually to avoid circular import

    def __init__(self, connection_manager: "ConnectionManager"):
        """Initialize with reference to connection manager.

        Args:
            connection_manager: The ConnectionManager for sending responses
        """
        super().__init__()
        self._manager = connection_manager

    async def process(
        self,
        connection: Connection,
        message: ProtocolMessage[Any],
        payload: Any,
    ) -> None:
        """Process model change request.

        Updates the conversation context's model and sends acknowledgment.

        Args:
            connection: The connection that sent the message
            message: The full protocol message
            payload: The model change payload (validated manually)
        """
        from application.protocol.control import ModelChangePayload

        # Validate payload
        try:
            validated_payload = ModelChangePayload.model_validate(payload if isinstance(payload, dict) else payload.model_dump())
        except Exception as e:
            log.error(f"Invalid model change payload: {e}")
            return

        model_id = validated_payload.model_id
        log.info(f"🔄 Model change requested: {model_id} for connection {connection.connection_id[:8]}...")

        # Delegate to orchestrator
        orchestrator = self._manager.orchestrator
        if orchestrator is None:
            log.error("Orchestrator not available for model change")
            await self._send_ack(connection, model_id, success=False, message="Server not ready")
            return

        try:
            await orchestrator.handle_model_change(connection, model_id)
            await self._send_ack(connection, model_id, success=True)
        except Exception as e:
            log.error(f"Failed to change model: {e}")
            await self._send_ack(connection, model_id, success=False, message=str(e))

    async def _send_ack(
        self,
        connection: Connection,
        model_id: str,
        success: bool,
        message: str | None = None,
    ) -> None:
        """Send model change acknowledgment.

        Args:
            connection: The connection to send to
            model_id: The model ID from the request
            success: Whether the change was successful
            message: Optional message (e.g., error details)
        """
        from application.protocol.control import ModelChangeAckPayload
        from application.protocol.core import create_message

        ack_message = create_message(
            message_type="control.conversation.model.ack",
            payload=ModelChangeAckPayload(
                model_id=model_id,
                success=success,
                message=message,
            ).model_dump(by_alias=True, exclude_none=True),
        )
        await self._manager.send_to_connection(connection.connection_id, ack_message)
