"""WebSocket Controller for Agent Host Protocol v1.0.0.

Provides the /ws WebSocket endpoint for real-time communication.
Handles connection lifecycle, message routing, and authentication.
"""

import logging
from typing import Any

from fastapi import Query, WebSocket, WebSocketDisconnect
from fastapi.routing import APIRouter
from pydantic import ValidationError

from api.dependencies import get_ws_access_token, get_ws_current_user
from application.protocol.core import ProtocolMessage
from application.websocket.connection import Connection
from application.websocket.manager import ConnectionManager
from application.websocket.router import MessageRouter, create_router_with_handlers

log = logging.getLogger(__name__)

# Create router for WebSocket endpoint
router = APIRouter(tags=["WebSocket"])


async def _parse_message(data: dict[str, Any]) -> ProtocolMessage[Any] | None:
    """Parse incoming JSON into a ProtocolMessage.

    Args:
        data: Raw JSON dict from WebSocket

    Returns:
        Parsed ProtocolMessage or None if parsing fails
    """
    try:
        return ProtocolMessage.model_validate(data)
    except ValidationError as e:
        log.error(f"Failed to parse message: {e}")
        return None


async def _handle_connection(
    connection: Connection,
    connection_manager: ConnectionManager,
    message_router: MessageRouter,
) -> None:
    """Handle the WebSocket receive loop.

    Continuously receives messages and routes them to handlers until
    the connection is closed.

    Args:
        connection: The active connection
        connection_manager: For sending responses
        message_router: For routing messages to handlers
    """
    websocket = connection.websocket

    while True:
        try:
            # Receive JSON message
            data = await websocket.receive_json()

            # Parse into protocol message
            message = await _parse_message(data)
            if message is None:
                log.warning(f"Received unparseable message from {connection.connection_id[:8]}...")
                continue

            # Route to handler
            await message_router.route(connection, message)

        except WebSocketDisconnect as e:
            log.info(f"WebSocket disconnected: {connection.connection_id[:8]}... (code: {e.code})")
            break
        except Exception as e:
            log.exception(f"Error in WebSocket receive loop: {e}")
            break


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str | None = Query(None, description="JWT access token"),
    conversation_id: str | None = Query(None, alias="conversationId", description="Conversation ID to join"),
    definition_id: str | None = Query(None, alias="definitionId", description="Agent definition ID"),
) -> None:
    """WebSocket endpoint for real-time protocol communication.

    Establishes a WebSocket connection with the Agent Host for:
    - Real-time chat messaging
    - Widget interactions
    - Control plane updates
    - System notifications

    Authentication:
        - Session cookie (browser): Uses existing session from OAuth2 login
        - Token query param (API): JWT access token for programmatic access

    Query Parameters:
        token: Optional JWT access token
        conversationId: Optional conversation ID to join/resume
        definitionId: Optional agent definition ID for new conversations

    Protocol:
        See docs/specs/websocket-protocol-v1.md for full specification.

    Close Codes:
        1000: Normal close
        1008: Policy violation (auth failure)
        1011: Internal error
        1012: Service restart
        4000-4999: Application-specific errors
    """
    # Get services from app state
    service_provider = getattr(websocket.app.state, "services", None)
    if service_provider is None:
        log.error("Service provider not found in app state")
        await websocket.close(code=1011, reason="Service provider not configured")
        return

    # Get ConnectionManager from DI
    connection_manager: ConnectionManager | None = None
    try:
        connection_manager = service_provider.get_required_service(ConnectionManager)
    except Exception as e:
        log.error(f"ConnectionManager not found: {e}")
        await websocket.close(code=1011, reason="Connection manager not configured")
        return

    # Type narrowing - connection_manager is guaranteed to be non-None at this point
    assert connection_manager is not None

    # Authenticate user
    try:
        user = await get_ws_current_user(websocket, token)
    except Exception as e:
        log.warning(f"WebSocket authentication failed: {e}")
        await websocket.close(code=1008, reason="Authentication failed")
        return

    user_id = user.get("sub", user.get("preferred_username", "unknown"))
    log.info(f"WebSocket connection request from user: {user_id}")

    # Extract access token for external API calls (e.g., Tools Provider)
    # Priority: query param token > session access token
    access_token: str | None = None
    try:
        access_token = await get_ws_access_token(websocket, token)
    except Exception as e:
        log.warning(f"Could not get access token for tools: {e}")
        # Continue without access token - tools won't be loaded

    # Create message router with handlers
    message_router = create_router_with_handlers(connection_manager)

    # Connect and start handling
    connection: Connection | None = None
    try:
        connection = await connection_manager.connect(
            websocket=websocket,
            user_id=user_id,
            conversation_id=conversation_id,
            definition_id=definition_id,
            access_token=access_token,
        )

        log.info(f"🔌 WebSocket connected: {connection}")

        # Main receive loop
        await _handle_connection(connection, connection_manager, message_router)

    except WebSocketDisconnect as e:
        log.info(f"WebSocket disconnected during setup: code={e.code}")
    except Exception as e:
        log.exception(f"Unexpected error in WebSocket handler: {e}")
    finally:
        # Cleanup connection
        if connection:
            await connection_manager.disconnect(
                connection.connection_id,
                reason="handler_exit",
                code=1000,
            )


class WebSocketController:
    """Controller class for WebSocket endpoints.

    This class serves as a container for the WebSocket router to integrate
    with the Neuroglia controller discovery system.

    Note: Unlike REST controllers that use classy_fastapi decorators,
    WebSocket endpoints must use a raw APIRouter due to FastAPI/Starlette
    limitations with class-based WebSocket handlers.
    """

    # The router is exported for registration in main.py
    router = router

    @staticmethod
    def get_router() -> APIRouter:
        """Get the WebSocket router for manual registration.

        Returns:
            FastAPI APIRouter with WebSocket endpoints
        """
        return router
