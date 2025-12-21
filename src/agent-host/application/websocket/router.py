"""WebSocket Message Router.

Routes incoming protocol messages to appropriate handlers based on message type.
Supports middleware chain for cross-cutting concerns (auth, rate limiting, logging).
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from neuroglia.hosting.abstractions import ApplicationBuilderBase
from pydantic import ValidationError

from application.protocol.core import ProtocolMessage, create_message
from application.protocol.enums import ErrorCategory
from application.protocol.system import SystemErrorPayload
from application.websocket.connection import Connection
from application.websocket.handlers.base import BaseHandler

if TYPE_CHECKING:
    from application.websocket.manager import ConnectionManager

log = logging.getLogger(__name__)


# Type alias for middleware
Middleware = Callable[
    [Connection, ProtocolMessage[Any], Callable[[Connection, ProtocolMessage[Any]], Awaitable[None]]],
    Awaitable[None],
]


class MessageRouter:
    """Routes WebSocket messages to handlers.

    Features:
    - Type-based message routing
    - Middleware chain support
    - Error handling with protocol-compliant error messages
    - Handler registration (single and bulk)
    """

    def __init__(self):
        """Initialize the message router."""
        self._handlers: dict[str, BaseHandler] = {}
        self._middleware: list[Middleware] = []
        self._default_handler: BaseHandler | None = None

    @staticmethod
    def configure(builder: ApplicationBuilderBase) -> None:
        """Configure MessageRouter in the service collection.

        Creates the router and registers it as a singleton.
        Handler registration happens separately via create_router().

        Args:
            builder: The application builder
        """
        router = MessageRouter()
        builder.services.add_singleton(MessageRouter, singleton=router)
        log.info("✅ MessageRouter configured as singleton")

    def register_handler(self, message_type: str, handler: BaseHandler) -> None:
        """Register a handler for a specific message type.

        Args:
            message_type: The message type to handle (e.g., "system.pong")
            handler: The handler instance
        """
        if message_type in self._handlers:
            log.warning(f"Overwriting handler for message type: {message_type}")
        self._handlers[message_type] = handler
        log.debug(f"Registered handler for {message_type}: {handler.__class__.__name__}")

    def register_handlers(self, handlers: dict[str, BaseHandler]) -> None:
        """Register multiple handlers at once.

        Args:
            handlers: Dict mapping message types to handlers
        """
        for message_type, handler in handlers.items():
            self.register_handler(message_type, handler)

    def set_default_handler(self, handler: BaseHandler) -> None:
        """Set a default handler for unregistered message types.

        Args:
            handler: The fallback handler
        """
        self._default_handler = handler
        log.debug(f"Set default handler: {handler.__class__.__name__}")

    def add_middleware(self, middleware: Middleware) -> None:
        """Add middleware to the processing chain.

        Middleware is called in order of registration (first added = outermost).

        Args:
            middleware: Async function with signature:
                (connection, message, next) -> None
        """
        self._middleware.append(middleware)
        log.debug(f"Added middleware: {middleware.__name__ if hasattr(middleware, '__name__') else type(middleware)}")

    async def route(self, connection: Connection, message: ProtocolMessage[Any]) -> None:
        """Route a message through middleware chain to handler.

        Args:
            connection: The connection that sent the message
            message: The protocol message to route
        """
        log.debug(f"Routing message type: {message.type}")

        # Build middleware chain
        async def handler_invoke(conn: Connection, msg: ProtocolMessage[Any]) -> None:
            await self._invoke_handler(conn, msg)

        # Wrap handler in middleware chain (reverse order so first added = outermost)
        current_handler: Callable[[Connection, ProtocolMessage[Any]], Awaitable[None]] = handler_invoke

        for middleware in reversed(self._middleware):
            current_handler = self._wrap_middleware(middleware, current_handler)

        # Execute the chain
        await current_handler(connection, message)

    def _wrap_middleware(
        self,
        middleware: Middleware,
        next_handler: Callable[[Connection, ProtocolMessage[Any]], Awaitable[None]],
    ) -> Callable[[Connection, ProtocolMessage[Any]], Awaitable[None]]:
        """Wrap a handler with middleware.

        Creates a closure that properly captures the middleware and next handler.

        Args:
            middleware: The middleware to wrap
            next_handler: The next handler in the chain

        Returns:
            A wrapped handler function
        """

        async def wrapped(conn: Connection, msg: ProtocolMessage[Any]) -> None:
            await middleware(conn, msg, next_handler)

        return wrapped

    async def _invoke_handler(self, connection: Connection, message: ProtocolMessage[Any]) -> None:
        """Invoke the appropriate handler for a message.

        Args:
            connection: The connection that sent the message
            message: The protocol message to handle
        """
        handler = self._handlers.get(message.type)

        if handler is None:
            if self._default_handler:
                handler = self._default_handler
                log.debug(f"Using default handler for unregistered type: {message.type}")
            else:
                log.warning(f"No handler registered for message type: {message.type}")
                await self._send_error(
                    connection,
                    category="validation",
                    code="UNKNOWN_MESSAGE_TYPE",
                    message=f"No handler for message type: {message.type}",
                    is_retryable=False,
                )
                return

        try:
            await handler.handle(connection, message)
        except ValidationError as e:
            log.error(f"Validation error handling {message.type}: {e}")
            await self._send_error(
                connection,
                category="validation",
                code="INVALID_PAYLOAD",
                message=f"Invalid payload for {message.type}",
                details={"errors": e.errors()},
                is_retryable=False,
            )
        except Exception as e:
            log.exception(f"Error handling {message.type}: {e}")
            await self._send_error(
                connection,
                category="server",
                code="HANDLER_ERROR",
                message=f"Error processing {message.type}",
                is_retryable=True,
            )

    async def _send_error(
        self,
        connection: Connection,
        category: ErrorCategory,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
        is_retryable: bool = False,
        retry_after_ms: int | None = None,
    ) -> None:
        """Send an error message to the connection.

        Args:
            connection: The target connection
            category: Error category
            code: Error code
            message: Human-readable error message
            details: Additional error details
            is_retryable: Whether the operation can be retried
            retry_after_ms: Suggested retry delay in milliseconds
        """
        error_payload = SystemErrorPayload(
            category=category,
            code=code,
            message=message,
            details=details,
            isRetryable=is_retryable,
            retryAfterMs=retry_after_ms,
        )
        error_message = create_message(
            message_type="system.error",
            payload=error_payload.model_dump(by_alias=True),
            conversation_id=connection.conversation_id,
        )

        try:
            message_dict = error_message.model_dump(by_alias=True, exclude_none=True)
            await connection.websocket.send_json(message_dict)
        except Exception as e:
            log.error(f"Failed to send error message: {e}")

    def get_registered_types(self) -> list[str]:
        """Get list of all registered message types."""
        return list(self._handlers.keys())

    def has_handler(self, message_type: str) -> bool:
        """Check if a handler is registered for a message type."""
        return message_type in self._handlers

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"MessageRouter(handlers={len(self._handlers)}, middleware={len(self._middleware)})"


# =============================================================================
# Built-in Middleware
# =============================================================================


async def logging_middleware(
    connection: Connection,
    message: ProtocolMessage[Any],
    next_handler: Callable[[Connection, ProtocolMessage[Any]], Awaitable[None]],
) -> None:
    """Middleware that logs message processing.

    Args:
        connection: The connection
        message: The message being processed
        next_handler: The next handler in the chain
    """
    start = datetime.now(UTC)
    log.debug(f"📥 Processing {message.type} from {connection.connection_id[:8]}...")

    try:
        await next_handler(connection, message)
    finally:
        elapsed = (datetime.now(UTC) - start).total_seconds() * 1000
        log.debug(f"📤 Processed {message.type} in {elapsed:.2f}ms")


async def activity_middleware(
    connection: Connection,
    message: ProtocolMessage[Any],
    next_handler: Callable[[Connection, ProtocolMessage[Any]], Awaitable[None]],
) -> None:
    """Middleware that updates connection activity timestamp.

    Args:
        connection: The connection
        message: The message being processed
        next_handler: The next handler in the chain
    """
    connection.update_activity()
    await next_handler(connection, message)


def create_router_with_handlers(connection_manager: ConnectionManager) -> MessageRouter:
    """Factory function to create a fully configured MessageRouter.

    Creates the router and registers all handlers for:
    - System messages (ping, pong, resume)
    - Control plane (conversation, widget, flow, navigation)
    - Data plane (audit, messages, responses)
    - Canvas (viewport, selection, connections, groups, layers, presentation)

    Args:
        connection_manager: The ConnectionManager for handler dependencies

    Returns:
        Configured MessageRouter with all handlers registered
    """
    from application.websocket.handlers.canvas_handlers import (
        BookmarkNavigateHandler,
        ConnectionCreatedHandler,
        GroupToggledHandler,
        LayerToggledHandler,
        PresentationNavigatedHandler,
        SelectionChangedHandler,
        ViewportChangedHandler,
    )
    from application.websocket.handlers.control_handlers import (
        ConversationConfigHandler,
        FlowCancelHandler,
        FlowPauseHandler,
        FlowStartHandler,
        ModelChangeHandler,
        NavigationNextHandler,
        NavigationPreviousHandler,
        NavigationSkipHandler,
        WidgetDismissedHandler,
        WidgetMovedHandler,
        WidgetResizedHandler,
        WidgetStateHandler,
        WidgetValidationHandler,
    )
    from application.websocket.handlers.data_handlers import (
        AuditEventsHandler,
        ContentChunkAckHandler,
        MessageSendHandler,
        ResponseSubmitHandler,
        ToolResultHandler,
    )
    from application.websocket.handlers.system_handlers import (
        ConnectionResumeHandler,
        PingHandler,
        PongHandler,
    )
    from application.websocket.middleware.rate_limit import rate_limit_middleware

    router = MessageRouter()

    # Add built-in middleware (order matters: first added = outermost)
    router.add_middleware(activity_middleware)
    router.add_middleware(logging_middleware)
    router.add_middleware(rate_limit_middleware)  # Phase 3: Rate limiting for data messages

    # Register system handlers
    router.register_handlers(
        {
            "system.pong": PongHandler(connection_manager),
            "system.ping": PingHandler(connection_manager),
            "system.connection.resume": ConnectionResumeHandler(connection_manager),
        }
    )

    # Register control plane handlers
    router.register_handlers(
        {
            # Conversation
            "control.conversation.config": ConversationConfigHandler(connection_manager),
            "control.conversation.model": ModelChangeHandler(connection_manager),
            # Widget state and interaction
            "control.widget.state": WidgetStateHandler(connection_manager),
            "control.widget.validation": WidgetValidationHandler(connection_manager),
            "control.widget.moved": WidgetMovedHandler(connection_manager),
            "control.widget.resized": WidgetResizedHandler(connection_manager),
            "control.widget.dismissed": WidgetDismissedHandler(connection_manager),
            # Flow control
            "control.flow.start": FlowStartHandler(connection_manager),
            "control.flow.pause": FlowPauseHandler(connection_manager),
            "control.flow.cancel": FlowCancelHandler(connection_manager),
            # Navigation
            "control.navigation.next": NavigationNextHandler(connection_manager),
            "control.navigation.previous": NavigationPreviousHandler(connection_manager),
            "control.navigation.skip": NavigationSkipHandler(connection_manager),
        }
    )

    # Register data plane handlers
    router.register_handlers(
        {
            # Audit telemetry
            "data.audit.events": AuditEventsHandler(connection_manager),
            # User messages
            "data.message.send": MessageSendHandler(connection_manager),
            # Widget responses
            "data.response.submit": ResponseSubmitHandler(connection_manager),
            # Tool execution (Phase 3)
            "data.tool.result": ToolResultHandler(connection_manager),
            # Content streaming acknowledgment (optional, Phase 3)
            "data.content.chunk.ack": ContentChunkAckHandler(connection_manager),
        }
    )

    # Register canvas handlers (Phase 4)
    router.register_handlers(
        {
            # Viewport
            "canvas.viewport.changed": ViewportChangedHandler(connection_manager),
            # Selection
            "canvas.selection.changed": SelectionChangedHandler(connection_manager),
            # Connections (user-initiated)
            "canvas.connection.created": ConnectionCreatedHandler(connection_manager),
            # Groups
            "canvas.group.toggled": GroupToggledHandler(connection_manager),
            # Layers
            "canvas.layer.toggled": LayerToggledHandler(connection_manager),
            # Presentation
            "canvas.presentation.navigated": PresentationNavigatedHandler(connection_manager),
            # Bookmarks
            "canvas.bookmark.navigate": BookmarkNavigateHandler(connection_manager),
        }
    )

    log.info(f"✅ MessageRouter configured with {len(router.get_registered_types())} handlers")
    return router
