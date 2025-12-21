"""Canvas Message Handlers.

Handles canvas-related protocol messages for:
- Element manipulation (create, update, delete)
- Connections between widgets
- Groups and layers
- Viewport control
- Presentation mode
- Bookmarks

These handlers receive messages from clients and manage canvas state.
"""

import logging
from typing import TYPE_CHECKING, Any

from application.protocol.canvas import (
    BookmarkNavigatePayload,
    ConnectionCreatedPayload,
    GroupToggledPayload,
    LayerToggledPayload,
    PresentationNavigatedPayload,
    SelectionPayload,
    ViewportChangedPayload,
)
from application.protocol.core import ProtocolMessage, create_message
from application.websocket.connection import Connection
from application.websocket.handlers.base import BaseHandler

if TYPE_CHECKING:
    from application.websocket.manager import ConnectionManager

log = logging.getLogger(__name__)


# =============================================================================
# VIEWPORT HANDLERS
# =============================================================================


class ViewportChangedHandler(BaseHandler[ViewportChangedPayload]):
    """Handles canvas.viewport.changed messages.

    Client sends when user pans or zooms the canvas.
    This is for synchronization with other viewers and analytics.
    """

    payload_type = ViewportChangedPayload

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
        payload: ViewportChangedPayload,
    ) -> None:
        """Process viewport changed notification.

        Args:
            connection: The connection that sent the message
            message: The full protocol message
            payload: The validated payload
        """
        log.debug(f"🖼️ Viewport changed by {connection.user_id}: pos=({payload.position.x}, {payload.position.y}), zoom={payload.zoom}")

        # TODO: Broadcast to other viewers in same conversation for collaboration
        # TODO: Store viewport state for session resumption

        # For now, just acknowledge
        # In collaborative mode, would broadcast to other users


# =============================================================================
# SELECTION HANDLERS
# =============================================================================


class SelectionChangedHandler(BaseHandler[SelectionPayload]):
    """Handles canvas.selection.changed messages.

    Client sends when user selects/deselects elements.
    Used for collaborative awareness (show what others have selected).
    """

    payload_type = SelectionPayload

    def __init__(self, connection_manager: "ConnectionManager"):
        super().__init__()
        self._manager = connection_manager

    async def process(
        self,
        connection: Connection,
        message: ProtocolMessage[Any],
        payload: SelectionPayload,
    ) -> None:
        """Process selection change notification.

        Args:
            connection: The connection that sent the message
            message: The full protocol message
            payload: The validated payload
        """
        widget_count = len(payload.widget_ids)
        group_count = len(payload.group_ids)
        conn_count = len(payload.connection_ids)

        log.debug(f"🎯 Selection changed by {connection.user_id}: {widget_count} widgets, {group_count} groups, {conn_count} connections")

        # TODO: In collaborative mode, broadcast selection to other users
        # Would show colored outlines around elements selected by others


# =============================================================================
# CONNECTION HANDLERS (User-initiated)
# =============================================================================


class ConnectionCreatedHandler(BaseHandler[ConnectionCreatedPayload]):
    """Handles canvas.connection.created messages.

    Client sends when user manually draws a connection between widgets.
    Server validates and persists the connection.
    """

    payload_type = ConnectionCreatedPayload

    def __init__(self, connection_manager: "ConnectionManager"):
        super().__init__()
        self._manager = connection_manager

    async def process(
        self,
        connection: Connection,
        message: ProtocolMessage[Any],
        payload: ConnectionCreatedPayload,
    ) -> None:
        """Process user-created connection.

        Args:
            connection: The connection that sent the message
            message: The full protocol message
            payload: The validated payload
        """
        log.info(f"🔗 Connection created by {connection.user_id}: {payload.source_widget_id} → {payload.target_widget_id}")

        # TODO: Validate that both widgets exist
        # TODO: Dispatch domain command to create connection
        # TODO: Broadcast connection to all viewers

        # Send acknowledgment
        ack_message = create_message(
            message_type="canvas.connection.created.ack",
            payload={
                "sourceWidgetId": payload.source_widget_id,
                "targetWidgetId": payload.target_widget_id,
                "accepted": True,
            },
            conversation_id=connection.conversation_id,
        )
        await self._manager.send_to_connection(connection.connection_id, ack_message)


# =============================================================================
# GROUP HANDLERS (User-initiated)
# =============================================================================


class GroupToggledHandler(BaseHandler[GroupToggledPayload]):
    """Handles canvas.group.toggled messages.

    Client sends when user expands/collapses a group.
    """

    payload_type = GroupToggledPayload

    def __init__(self, connection_manager: "ConnectionManager"):
        super().__init__()
        self._manager = connection_manager

    async def process(
        self,
        connection: Connection,
        message: ProtocolMessage[Any],
        payload: GroupToggledPayload,
    ) -> None:
        """Process group toggle notification.

        Args:
            connection: The connection that sent the message
            message: The full protocol message
            payload: The validated payload
        """
        state = "collapsed" if payload.collapsed else "expanded"
        log.debug(f"📁 Group {payload.group_id} {state} by {connection.user_id}")

        # TODO: Persist group state
        # TODO: Broadcast to other viewers


# =============================================================================
# LAYER HANDLERS (User-initiated)
# =============================================================================


class LayerToggledHandler(BaseHandler[LayerToggledPayload]):
    """Handles canvas.layer.toggled messages.

    Client sends when user shows/hides a layer.
    """

    payload_type = LayerToggledPayload

    def __init__(self, connection_manager: "ConnectionManager"):
        super().__init__()
        self._manager = connection_manager

    async def process(
        self,
        connection: Connection,
        message: ProtocolMessage[Any],
        payload: LayerToggledPayload,
    ) -> None:
        """Process layer visibility toggle.

        Args:
            connection: The connection that sent the message
            message: The full protocol message
            payload: The validated payload
        """
        state = "visible" if payload.visible else "hidden"
        log.debug(f"📄 Layer {payload.layer_id} now {state} for {connection.user_id}")

        # Layer visibility is typically per-user, not broadcast


# =============================================================================
# PRESENTATION HANDLERS
# =============================================================================


class PresentationNavigatedHandler(BaseHandler[PresentationNavigatedPayload]):
    """Handles canvas.presentation.navigated messages.

    Client sends when user navigates within a presentation.
    """

    payload_type = PresentationNavigatedPayload

    def __init__(self, connection_manager: "ConnectionManager"):
        super().__init__()
        self._manager = connection_manager

    async def process(
        self,
        connection: Connection,
        message: ProtocolMessage[Any],
        payload: PresentationNavigatedPayload,
    ) -> None:
        """Process presentation navigation.

        Args:
            connection: The connection that sent the message
            message: The full protocol message
            payload: The validated payload
        """
        log.info(f"🎬 Presentation {payload.presentation_id}: {payload.from_step} → {payload.to_step} ({payload.action}) by {connection.user_id}")

        # TODO: Track presentation progress for analytics
        # TODO: Emit domain event for presentation progress


# =============================================================================
# BOOKMARK HANDLERS
# =============================================================================


class BookmarkNavigateHandler(BaseHandler[BookmarkNavigatePayload]):
    """Handles canvas.bookmark.navigate messages.

    Client sends when user navigates to a bookmark.
    """

    payload_type = BookmarkNavigatePayload

    def __init__(self, connection_manager: "ConnectionManager"):
        super().__init__()
        self._manager = connection_manager

    async def process(
        self,
        connection: Connection,
        message: ProtocolMessage[Any],
        payload: BookmarkNavigatePayload,
    ) -> None:
        """Process bookmark navigation.

        Args:
            connection: The connection that sent the message
            message: The full protocol message
            payload: The validated payload
        """
        log.debug(f"🔖 Bookmark {payload.bookmark_id} navigated by {connection.user_id}")

        # Bookmarks are typically client-only navigation aids
        # May want to track for analytics
