"""System Message Handlers.

Handles system-level protocol messages:
- system.pong: Keepalive response from client
- system.connection.resume: Client reconnection request
"""

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from application.protocol.core import ProtocolMessage, create_message
from application.protocol.system import (
    SystemConnectionResumedPayload,
    SystemConnectionResumePayload,
    SystemPingPongPayload,
)
from application.websocket.connection import Connection
from application.websocket.handlers.base import BaseHandler

if TYPE_CHECKING:
    from application.websocket.manager import ConnectionManager

log = logging.getLogger(__name__)


class PongHandler(BaseHandler[SystemPingPongPayload]):
    """Handles system.pong messages from clients.

    Updates the connection's last activity time and resets missed pong counter.
    """

    payload_type = SystemPingPongPayload

    def __init__(self, connection_manager: "ConnectionManager"):
        """Initialize with reference to connection manager.

        Args:
            connection_manager: The ConnectionManager for updating connection state
        """
        super().__init__()
        self._manager = connection_manager

    async def process(
        self,
        connection: Connection,
        message: ProtocolMessage[Any],
        payload: SystemPingPongPayload,
    ) -> None:
        """Process pong response.

        Args:
            connection: The connection that sent the pong
            message: The full protocol message
            payload: The validated pong payload
        """
        self._manager.handle_pong(connection.connection_id)
        log.debug(f"🏓 Pong processed for {connection.connection_id[:8]}... (client time: {payload.timestamp})")


class ConnectionResumeHandler(BaseHandler[SystemConnectionResumePayload]):
    """Handles system.connection.resume messages from reconnecting clients.

    Validates the resume request and sends back a system.connection.resumed
    message with state validation results.
    """

    payload_type = SystemConnectionResumePayload

    def __init__(self, connection_manager: "ConnectionManager"):
        """Initialize with reference to connection manager.

        Args:
            connection_manager: The ConnectionManager for state management
        """
        super().__init__()
        self._manager = connection_manager

    async def process(
        self,
        connection: Connection,
        message: ProtocolMessage[Any],
        payload: SystemConnectionResumePayload,
    ) -> None:
        """Process resume request.

        Validates the client's state against server state and sends back
        confirmation with replay information if needed.

        Args:
            connection: The connection requesting resume
            message: The full protocol message
            payload: The validated resume payload
        """
        log.info(f"📥 Resume request from {connection.connection_id[:8]}... for conversation {payload.conversation_id}")

        # For Phase 1, we accept all resume requests but mark state as not replayed
        # Full resume with message replay will be implemented in Phase 4

        # Update connection's conversation context if not already set
        if not connection.conversation_id:
            connection.conversation_id = payload.conversation_id

        # Build resumed response
        resumed_payload = SystemConnectionResumedPayload(
            conversationId=payload.conversation_id,
            resumedFromMessageId=payload.last_message_id,
            currentItemIndex=payload.last_item_index,
            missedMessages=0,  # Phase 1: no message replay
            stateValid=True,  # Phase 1: always accept state
        )

        # Send resumed confirmation
        resumed_message = create_message(
            message_type="system.connection.resumed",
            payload=resumed_payload.model_dump(by_alias=True),
            conversation_id=payload.conversation_id,
        )
        await self._manager.send_to_connection(connection.connection_id, resumed_message)

        log.info(f"✅ Resume confirmed for {connection.connection_id[:8]}...")


class PingHandler(BaseHandler[SystemPingPongPayload]):
    """Handles system.ping messages from clients.

    Clients may send pings to verify connection; server responds with pong.
    """

    payload_type = SystemPingPongPayload

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
        payload: SystemPingPongPayload,
    ) -> None:
        """Process ping request and send pong response.

        Args:
            connection: The connection that sent the ping
            message: The full protocol message
            payload: The validated ping payload
        """
        log.debug(f"🏓 Ping received from {connection.connection_id[:8]}...")

        # Respond with pong
        pong_payload = SystemPingPongPayload(timestamp=datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z"))
        pong_message = create_message(
            message_type="system.pong",
            payload=pong_payload.model_dump(),
            conversation_id=connection.conversation_id,
        )
        await self._manager.send_to_connection(connection.connection_id, pong_message)
