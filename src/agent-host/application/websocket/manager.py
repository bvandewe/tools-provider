"""WebSocket Connection Manager.

Manages all active WebSocket connections, providing:
- Connection lifecycle management (connect, disconnect)
- Message sending (to connection, user, conversation, broadcast)
- Heartbeat (ping/pong) mechanism
- Stale connection cleanup
- Integration with ConversationOrchestrator for agent execution

Follows the Neuroglia framework configure() pattern for DI registration.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from neuroglia.hosting.abstractions import ApplicationBuilderBase, HostedService
from starlette.websockets import WebSocket, WebSocketState

from application.protocol.core import ProtocolMessage, create_message
from application.protocol.enums import SERVER_CAPABILITIES, ConnectionCloseReason
from application.protocol.system import SystemConnectionClosePayload, SystemConnectionEstablishedPayload, SystemPingPongPayload
from application.websocket.connection import Connection
from application.websocket.state import ConnectionState

if TYPE_CHECKING:
    from application.orchestrator import Orchestrator

log = logging.getLogger(__name__)


class ConnectionManager(HostedService):
    """Manages WebSocket connections for the Agent Host.

    Implements HostedService for automatic lifecycle management:
    - start_async(): Starts heartbeat and cleanup background tasks
    - stop_async(): Stops tasks and gracefully closes all connections

    Handles:
    - Connection lifecycle (accept, track, disconnect)
    - Message delivery (single, user, conversation, broadcast)
    - Heartbeat mechanism with ping/pong
    - Stale connection cleanup
    - Integration with ConversationOrchestrator
    """

    def __init__(
        self,
        heartbeat_interval_seconds: float = 30.0,
        heartbeat_timeout_seconds: float = 10.0,
        max_missed_pongs: int = 3,
        cleanup_interval_seconds: float = 60.0,
        idle_timeout_seconds: float = 300.0,
    ):
        """Initialize the ConnectionManager.

        Args:
            heartbeat_interval_seconds: Interval between pings (default: 30s)
            heartbeat_timeout_seconds: Time to wait for pong response (default: 10s)
            max_missed_pongs: Max missed pongs before disconnect (default: 3)
            cleanup_interval_seconds: Interval for stale connection cleanup (default: 60s)
            idle_timeout_seconds: Idle time before connection is considered stale (default: 300s)
        """
        self._connections: dict[str, Connection] = {}  # TODO: PubSub for scaling
        self._user_connections: dict[str, set[str]] = {}  # user_id -> set of connection_ids
        self._conversation_connections: dict[str, set[str]] = {}  # conversation_id -> set of connection_ids

        # Configuration
        self._heartbeat_interval = heartbeat_interval_seconds
        self._heartbeat_timeout = heartbeat_timeout_seconds
        self._max_missed_pongs = max_missed_pongs
        self._cleanup_interval = cleanup_interval_seconds
        self._idle_timeout = idle_timeout_seconds

        # Background tasks
        self._heartbeat_task: asyncio.Task | None = None
        self._cleanup_task: asyncio.Task | None = None
        self._running = False

        # Event callbacks
        self._on_connect_callbacks: list[Callable[[Connection], Awaitable[None]]] = []
        self._on_disconnect_callbacks: list[Callable[[Connection, str | None], Awaitable[None]]] = []

        # Orchestrator reference (set via set_orchestrator after DI resolution)
        self._orchestrator: Orchestrator | None = None

        log.info("ConnectionManager initialized")

    def set_orchestrator(self, orchestrator: "Orchestrator") -> None:
        """Set the conversation orchestrator.

        This is called after DI resolution to avoid circular dependencies.

        Args:
            orchestrator: The Orchestrator instance
        """
        self._orchestrator = orchestrator
        log.info("ConnectionManager: Orchestrator linked")

    @staticmethod
    def configure(builder: ApplicationBuilderBase) -> None:
        """Configure ConnectionManager in the service collection.

        Follows Neuroglia framework pattern for service registration.
        Note: The ConversationOrchestrator is wired separately in main.py
        after the app is built, since it needs the Mediator from DI.

        Args:
            builder: The application builder
        """
        from application.settings import app_settings

        manager = ConnectionManager(
            heartbeat_interval_seconds=getattr(app_settings, "ws_heartbeat_interval", 30.0),
            heartbeat_timeout_seconds=getattr(app_settings, "ws_heartbeat_timeout", 10.0),
            max_missed_pongs=getattr(app_settings, "ws_max_missed_pongs", 3),
            cleanup_interval_seconds=getattr(app_settings, "ws_cleanup_interval", 60.0),
            idle_timeout_seconds=getattr(app_settings, "ws_idle_timeout", 300.0),
        )

        # Register as singleton for DI
        builder.services.add_singleton(ConnectionManager, singleton=manager)

        # Register as HostedService for automatic lifecycle management
        # This ensures start_async() is called during app startup and stop_async() during shutdown
        builder.services.add_singleton(HostedService, singleton=manager)

        log.info("✅ ConnectionManager configured as HostedService")

    # =========================================================================
    # Connection Lifecycle
    # =========================================================================

    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        conversation_id: str | None = None,
        definition_id: str | None = None,
        access_token: str | None = None,
    ) -> Connection:
        """Accept a new WebSocket connection and initialize orchestrator.

        This is the main entry point for WebSocket connections. It:
        1. Creates and registers the connection
        2. Sends system.connection.established message
        3. Initializes the ConversationOrchestrator (if conversation_id provided)
        4. Triggers proactive flow for template-based conversations

        For the two-phase flow:
        - Client first calls POST /chat/new → gets conversation_id + ws_url
        - Client then opens WebSocket with conversation_id
        - Orchestrator loads conversation context and starts flow

        Args:
            websocket: The Starlette WebSocket
            user_id: Authenticated user ID
            conversation_id: Conversation ID (required for orchestration)
            definition_id: Optional agent definition ID
            access_token: Optional access token for external API calls

        Returns:
            The created Connection object
        """
        # Create connection object
        connection = Connection(
            websocket=websocket,
            user_id=user_id,
            conversation_id=conversation_id,
            definition_id=definition_id,
            access_token=access_token,
        )

        # Accept the WebSocket
        await websocket.accept()
        connection.transition_to(ConnectionState.CONNECTED, "websocket_accepted")

        # Register in tracking structures
        self._connections[connection.connection_id] = connection
        self._user_connections.setdefault(user_id, set()).add(connection.connection_id)
        if conversation_id:
            self._conversation_connections.setdefault(conversation_id, set()).add(connection.connection_id)

        log.info(f"🔌 Connection established: {connection}")

        # Transition to authenticated (user is already authenticated at this point)
        connection.transition_to(ConnectionState.AUTHENTICATED, "user_verified")

        # Initialize orchestrator BEFORE sending established message
        # This loads tools so we can include tool count in the message
        if conversation_id and self._orchestrator:
            try:
                await self._orchestrator.initialize(connection, conversation_id)
                log.info(f"🎭 Orchestrator initialized for conversation {conversation_id}")
            except Exception as e:
                log.error(f"Failed to initialize orchestrator: {e}")
                # Send error but don't disconnect - allow client to retry
                error_message = create_message(
                    message_type="system.error",
                    payload={
                        "category": "server",
                        "code": "ORCHESTRATOR_INIT_FAILED",
                        "message": str(e),
                        "isRetryable": True,
                    },
                    conversation_id=conversation_id,
                )
                await self.send_to_connection(connection.connection_id, error_message)
        elif conversation_id and not self._orchestrator:
            log.warning("No orchestrator configured - conversation flow will not be managed")

        # Send connection established message (after orchestrator init so tools are loaded)
        await self._send_established_message(connection)

        # Transition to active
        connection.transition_to(ConnectionState.ACTIVE, "handshake_complete")

        # Start conversation flow AFTER handshake is complete
        # This ensures proactive messages are sent after the client is ready
        if conversation_id and self._orchestrator:
            try:
                await self._orchestrator.start_conversation_flow(connection)
            except Exception as e:
                log.error(f"Failed to start conversation flow: {e}")
                # Send error but don't disconnect
                error_message = create_message(
                    message_type="system.error",
                    payload={
                        "category": "server",
                        "code": "FLOW_START_FAILED",
                        "message": str(e),
                        "isRetryable": True,
                    },
                    conversation_id=conversation_id,
                )
                await self.send_to_connection(connection.connection_id, error_message)

        # Notify callbacks
        for callback in self._on_connect_callbacks:
            try:
                await callback(connection)
            except Exception as e:
                log.error(f"Error in on_connect callback: {e}")

        return connection

    async def disconnect(self, connection_id: str, reason: str | None = None, code: int = 1000) -> None:
        """Disconnect and cleanup a connection.

        Args:
            connection_id: The connection ID to disconnect
            reason: Optional reason for disconnection
            code: WebSocket close code (default: 1000 normal)
        """
        connection = self._connections.get(connection_id)
        if not connection:
            log.debug(f"Connection not found for disconnect: {connection_id}")
            return

        log.info(f"🔌 Disconnecting: {connection} (reason: {reason}, code: {code})")

        # Cleanup orchestrator state
        if self._orchestrator:
            try:
                await self._orchestrator.cleanup(connection_id)
            except Exception as e:
                log.error(f"Error cleaning up orchestrator: {e}")

        # Transition to closing
        connection.transition_to(ConnectionState.CLOSING, reason)

        # Map reason string to valid ConnectionCloseReason
        close_reason: ConnectionCloseReason = self._map_close_reason(reason)

        # Try to send close message if connection is still open
        try:
            if connection.websocket.client_state == WebSocketState.CONNECTED:
                close_payload = SystemConnectionClosePayload(
                    reason=close_reason,
                    code=code,
                )
                await self.send_to_connection(
                    connection_id,
                    create_message("system.connection.close", close_payload.model_dump(by_alias=True)),
                )
                await connection.websocket.close(code=code, reason=reason)
        except Exception as e:
            log.debug(f"Error during graceful close: {e}")

        # Transition to closed
        connection.state_machine.force_closed(reason)

        # Remove from tracking structures
        self._cleanup_connection_tracking(connection)

        # Notify callbacks
        for callback in self._on_disconnect_callbacks:
            try:
                await callback(connection, reason)
            except Exception as e:
                log.error(f"Error in on_disconnect callback: {e}")

    def _cleanup_connection_tracking(self, connection: Connection) -> None:
        """Remove connection from all tracking structures."""
        # Remove from main dict
        self._connections.pop(connection.connection_id, None)

        # Remove from user connections
        if connection.user_id in self._user_connections:
            self._user_connections[connection.user_id].discard(connection.connection_id)
            if not self._user_connections[connection.user_id]:
                del self._user_connections[connection.user_id]

        # Remove from conversation connections
        if connection.conversation_id and connection.conversation_id in self._conversation_connections:
            self._conversation_connections[connection.conversation_id].discard(connection.connection_id)
            if not self._conversation_connections[connection.conversation_id]:
                del self._conversation_connections[connection.conversation_id]

    def _map_close_reason(self, reason: str | None) -> ConnectionCloseReason:
        """Map a reason string to a valid ConnectionCloseReason.

        Args:
            reason: The reason string (may not be a valid enum value)

        Returns:
            A valid ConnectionCloseReason value
        """
        valid_reasons: set[ConnectionCloseReason] = {
            "user_logout",
            "session_expired",
            "server_shutdown",
            "conversation_complete",
            "idle_timeout",
        }
        if reason in valid_reasons:
            return reason  # type: ignore[return-value]
        # Default to idle_timeout for unknown reasons
        return "idle_timeout"

    async def _send_established_message(self, connection: Connection) -> None:
        """Send the connection established message with server capabilities.

        This message is sent immediately after WebSocket handshake completes.
        It includes server capabilities for protocol negotiation and model info.
        """
        # Get model information from the orchestrator's factory
        current_model: str | None = None
        available_models: list[dict[str, Any]] = []
        allow_model_selection = False
        definition_id = connection.definition_id
        definition_model: str | None = None
        definition_allows_selection = True

        if self._orchestrator:
            try:
                # If no definition_id on connection but we have conversation_id, look it up
                if not definition_id and connection.conversation_id:
                    definition_id, definition_model, definition_allows_selection = await self._orchestrator.get_definition_info_from_conversation(connection.conversation_id, connection.user_id)
                    # Update connection with discovered definition_id
                    if definition_id:
                        connection.definition_id = definition_id
                elif definition_id:
                    # Get definition info directly
                    definition_allows_selection = await self._orchestrator.get_definition_allow_model_selection(definition_id, connection.user_id)

                factory = self._orchestrator.llm_provider_factory

                # Convert ModelDefinition dataclasses to dicts for JSON serialization
                available_models = [
                    {
                        "provider": model.provider.value,
                        "id": model.id,
                        "qualifiedId": model.qualified_id,
                        "name": model.name,
                        "description": model.description,
                        "isDefault": model.is_default,
                    }
                    for model in factory.available_models
                ]

                # Current model is either:
                # 1. The definition's configured model (if set)
                # 2. The default provider's current model
                if definition_model:
                    current_model = definition_model
                else:
                    default_provider = factory.get_default_provider()
                    current_model = default_provider.current_model

                # Allow model selection if:
                # 1. There are multiple models available AND
                # 2. The definition allows model selection (or no definition)
                has_multiple_models = len(available_models) > 1
                allow_model_selection = has_multiple_models and definition_allows_selection
            except Exception as e:
                log.warning(f"Failed to get model info for established message: {e}")

        # Get tool count from orchestrator if available
        tool_count = 0
        if self._orchestrator:
            try:
                tool_count = await self._orchestrator.get_tool_count(connection.connection_id)
            except Exception as e:
                log.warning(f"Failed to get tool count for established message: {e}")

        payload = SystemConnectionEstablishedPayload(
            connectionId=connection.connection_id,
            conversationId=connection.conversation_id or "",
            userId=connection.user_id,
            definitionId=connection.definition_id,
            resuming=False,
            serverTime=datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            serverCapabilities=SERVER_CAPABILITIES,
            currentModel=current_model,
            availableModels=available_models,
            allowModelSelection=allow_model_selection,
            toolCount=tool_count,
        )
        message = create_message(
            message_type="system.connection.established",
            payload=payload.model_dump(by_alias=True),
            conversation_id=connection.conversation_id,
        )
        await self.send_to_connection(connection.connection_id, message)

    # =========================================================================
    # Message Sending
    # =========================================================================

    async def send_to_connection(self, connection_id: str, message: ProtocolMessage[Any]) -> bool:
        """Send a message to a specific connection.

        Args:
            connection_id: Target connection ID
            message: Protocol message to send

        Returns:
            True if sent successfully, False otherwise
        """
        connection = self._connections.get(connection_id)
        if not connection:
            log.debug(f"Cannot send - connection not found: {connection_id}")
            return False

        if not connection.can_send:
            log.debug(f"Cannot send - connection not in sendable state: {connection.state}")
            return False

        try:
            message_dict = message.model_dump(by_alias=True, exclude_none=True)
            await connection.websocket.send_json(message_dict)
            connection.last_sent_message_id = message.id
            connection.update_activity()
            log.debug(f"📤 Sent {message.type} to {connection.connection_id[:8]}...")
            return True
        except Exception as e:
            log.error(f"Failed to send message to {connection_id}: {e}")
            await self.disconnect(connection_id, reason="send_error", code=1011)
            return False

    async def send_to_user(self, user_id: str, message: ProtocolMessage[Any]) -> int:
        """Send a message to all connections for a user.

        Args:
            user_id: Target user ID
            message: Protocol message to send

        Returns:
            Number of connections message was sent to
        """
        connection_ids = self._user_connections.get(user_id, set())
        sent_count = 0
        for conn_id in list(connection_ids):
            if await self.send_to_connection(conn_id, message):
                sent_count += 1
        return sent_count

    async def broadcast_to_conversation(self, conversation_id: str, message: ProtocolMessage[Any]) -> int:
        """Broadcast a message to all connections in a conversation.

        Args:
            conversation_id: Target conversation ID
            message: Protocol message to send

        Returns:
            Number of connections message was sent to
        """
        connection_ids = self._conversation_connections.get(conversation_id, set())
        sent_count = 0
        for conn_id in list(connection_ids):
            if await self.send_to_connection(conn_id, message):
                sent_count += 1
        return sent_count

    async def broadcast_all(self, message: ProtocolMessage[Any]) -> int:
        """Broadcast a message to all active connections.

        Args:
            message: Protocol message to send

        Returns:
            Number of connections message was sent to
        """
        sent_count = 0
        for conn_id in list(self._connections.keys()):
            if await self.send_to_connection(conn_id, message):
                sent_count += 1
        return sent_count

    # =========================================================================
    # =========================================================================
    # HostedService Lifecycle
    # =========================================================================

    async def start_async(self) -> None:
        """Start background tasks (heartbeat, cleanup).

        Called automatically by the Neuroglia host during application startup.
        """
        if self._running:
            return

        self._running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        log.info("🚀 ConnectionManager started (heartbeat + cleanup tasks)")

    async def stop_async(self) -> None:
        """Stop background tasks and close all connections.

        Called automatically by the Neuroglia host during application shutdown.
        """
        self._running = False

        # Cancel background tasks
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Close all connections gracefully
        for conn_id in list(self._connections.keys()):
            await self.disconnect(conn_id, reason="server_shutdown", code=1012)

        log.info("🛑 ConnectionManager stopped (all connections closed)")

    # =========================================================================
    # Heartbeat & Cleanup Background Tasks
    # =========================================================================

    async def _heartbeat_loop(self) -> None:
        """Background task to send pings and detect dead connections."""
        log.debug("Heartbeat loop started")
        while self._running:
            try:
                await asyncio.sleep(self._heartbeat_interval)
                await self._send_pings()
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Error in heartbeat loop: {e}")

    async def _send_pings(self) -> None:
        """Send ping to all active connections."""
        timestamp = datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        ping_payload = SystemPingPongPayload(timestamp=timestamp)
        ping_message = create_message("system.ping", ping_payload.model_dump())

        for connection in list(self._connections.values()):
            if not connection.is_active:
                continue

            # Check for missed pongs from previous ping
            if connection.last_ping_sent and connection.last_pong_received:
                if connection.last_ping_sent > connection.last_pong_received:
                    connection.record_missed_pong()
                    if connection.missed_pongs >= self._max_missed_pongs:
                        log.warning(f"Connection {connection.connection_id} exceeded max missed pongs")
                        await self.disconnect(connection.connection_id, reason="heartbeat_timeout", code=1002)
                        continue

            # Send ping
            connection.record_ping_sent()
            await self.send_to_connection(connection.connection_id, ping_message)

    async def _cleanup_loop(self) -> None:
        """Background task to cleanup stale connections."""
        log.debug("Cleanup loop started")
        while self._running:
            try:
                await asyncio.sleep(self._cleanup_interval)
                await self._cleanup_stale_connections()
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Error in cleanup loop: {e}")

    async def _cleanup_stale_connections(self) -> None:
        """Remove connections that have been idle too long."""
        for connection in list(self._connections.values()):
            if connection.idle_seconds > self._idle_timeout:
                log.info(f"Cleaning up stale connection: {connection.connection_id}")
                await self.disconnect(connection.connection_id, reason="idle_timeout", code=1000)

    def handle_pong(self, connection_id: str) -> None:
        """Handle pong response from client.

        Args:
            connection_id: The connection that sent the pong
        """
        connection = self._connections.get(connection_id)
        if connection:
            connection.record_pong_received()
            log.debug(f"🏓 Pong received from {connection_id[:8]}...")

    # =========================================================================
    # Event Callbacks
    # =========================================================================

    def on_connect(self, callback: Callable[[Connection], Awaitable[None]]) -> None:
        """Register a callback for connection events.

        Args:
            callback: Async function to call when a connection is established
        """
        self._on_connect_callbacks.append(callback)

    def on_disconnect(self, callback: Callable[[Connection, str | None], Awaitable[None]]) -> None:
        """Register a callback for disconnection events.

        Args:
            callback: Async function to call when a connection is closed
        """
        self._on_disconnect_callbacks.append(callback)

    # =========================================================================
    # Query Methods
    # =========================================================================

    def get_connection(self, connection_id: str) -> Connection | None:
        """Get a connection by ID."""
        return self._connections.get(connection_id)

    def get_user_connections(self, user_id: str) -> list[Connection]:
        """Get all connections for a user."""
        conn_ids = self._user_connections.get(user_id, set())
        return [self._connections[cid] for cid in conn_ids if cid in self._connections]

    def get_conversation_connections(self, conversation_id: str) -> list[Connection]:
        """Get all connections for a conversation."""
        conn_ids = self._conversation_connections.get(conversation_id, set())
        return [self._connections[cid] for cid in conn_ids if cid in self._connections]

    @property
    def connection_count(self) -> int:
        """Get total number of active connections."""
        return len(self._connections)

    @property
    def user_count(self) -> int:
        """Get number of unique connected users."""
        return len(self._user_connections)

    @property
    def conversation_count(self) -> int:
        """Get number of active conversations."""
        return len(self._conversation_connections)

    def get_stats(self) -> dict[str, Any]:
        """Get connection statistics."""
        return {
            "connections": self.connection_count,
            "users": self.user_count,
            "conversations": self.conversation_count,
            "running": self._running,
        }
