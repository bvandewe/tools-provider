"""Widget protocol sender.

Handles sending:
- Widget render messages (control.widget.render)
- Confirmation button widgets
- Widget state updates
"""

import logging
from typing import TYPE_CHECKING, Any

from application.protocol.core import create_message
from application.protocol.widgets.base import WidgetConstraints, WidgetLayout, WidgetRenderPayload

if TYPE_CHECKING:
    from application.orchestrator.context import ConversationContext
    from application.websocket.connection import Connection
    from application.websocket.manager import ConnectionManager

log = logging.getLogger(__name__)


class WidgetSender:
    """Sends widget-related protocol messages to clients.

    This class encapsulates the logic for rendering widgets and
    managing widget interactions via the WebSocket protocol.

    Attributes:
        _connection_manager: The WebSocket connection manager

    Usage:
        sender = WidgetSender(connection_manager)
        await sender.send_widget_render(connection, context, item, content, stem)
        await sender.send_confirmation_widget(connection, context, item)
    """

    def __init__(self, connection_manager: "ConnectionManager"):
        """Initialize the widget sender.

        Args:
            connection_manager: The WebSocket connection manager for message delivery
        """
        self._connection_manager = connection_manager

    async def send_widget_render(
        self,
        connection: "Connection",
        context: "ConversationContext",
        item_id: str,
        widget_id: str,
        widget_type: str,
        stem: str | None = None,
        options: list[Any] | None = None,
        widget_config: dict[str, Any] | None = None,
        required: bool = False,
        skippable: bool = True,
        initial_value: Any = None,
        show_user_response: bool = True,
    ) -> None:
        """Send a widget.render control message to the client.

        Args:
            connection: The WebSocket connection
            context: The conversation context
            item_id: The parent item's ID
            widget_id: Unique widget identifier
            widget_type: Type of widget (e.g., "multiple_choice", "free_text")
            stem: The question/prompt text
            options: Choice options for widgets (multiple_choice, checkbox_group, dropdown)
            widget_config: Widget-specific behavior/display settings (shuffle_options, etc.)
            required: Whether response is required
            skippable: Whether widget can be skipped
            initial_value: Pre-populated value
            show_user_response: Whether to show response as chat bubble
        """
        # Build the render payload with options at top level
        render_payload = WidgetRenderPayload(
            itemId=item_id,
            widgetId=widget_id,
            widgetType=widget_type,
            stem=stem,
            options=options,
            widgetConfig=widget_config,
            required=required,
            skippable=skippable,
            initialValue=initial_value,
            showUserResponse=show_user_response,
            layout=WidgetLayout(mode="flow"),
            constraints=WidgetConstraints(
                moveable=False,
                resizable=False,
                dismissable=skippable,
            ),
        )

        widget_message = create_message(
            message_type="control.widget.render",
            payload=render_payload.model_dump(by_alias=True, exclude_none=True),
            conversation_id=context.conversation_id,
        )

        await self._connection_manager.send_to_connection(connection.connection_id, widget_message)
        log.debug(f"📤 Sent widget.render for {widget_id} ({widget_type})")

    async def send_widget_render_from_content(
        self,
        connection: "Connection",
        context: "ConversationContext",
        item: Any,  # ConversationItemDto
        content: Any,  # ItemContentDto
        stem: str | None,
    ) -> None:
        """Send a widget.render message from ItemContent data.

        Convenience method that extracts widget parameters from DTOs.

        Args:
            connection: The WebSocket connection
            context: The conversation context
            item: The parent ConversationItemDto
            content: The ItemContentDto
            stem: The resolved stem text
        """
        await self.send_widget_render(
            connection=connection,
            context=context,
            item_id=item.id,
            widget_id=content.id,
            widget_type=content.widget_type,
            stem=stem,
            options=content.options if hasattr(content, "options") else None,
            widget_config=content.widget_config,
            required=content.required,
            skippable=content.skippable,
            initial_value=content.initial_value,
            show_user_response=content.show_user_response,
        )

    async def send_confirmation_widget(
        self,
        connection: "Connection",
        context: "ConversationContext",
        item_id: str,
        button_text: str = "Submit",
    ) -> None:
        """Send a confirmation button widget for items requiring user confirmation.

        Args:
            connection: The WebSocket connection
            context: The conversation context
            item_id: The item ID that requires confirmation
            button_text: The text to display on the button
        """
        # Generate a unique widget ID for the confirmation button
        confirmation_widget_id = f"{item_id}-confirm"

        # Build the render payload for a button widget
        render_payload = WidgetRenderPayload(
            itemId=item_id,
            widgetId=confirmation_widget_id,
            widgetType="button",
            stem=None,  # No stem text for confirmation button
            options=None,
            widgetConfig={
                "label": button_text,
                "variant": "primary",
                "action": "confirm",
            },
            required=True,
            skippable=False,
            initialValue=None,
            showUserResponse=False,  # Don't show button click as a chat bubble
            layout=WidgetLayout(mode="flow"),
            constraints=WidgetConstraints(
                moveable=False,
                resizable=False,
                dismissable=False,
            ),
        )

        widget_message = create_message(
            message_type="control.widget.render",
            payload=render_payload.model_dump(by_alias=True, exclude_none=True),
            conversation_id=context.conversation_id,
        )

        await self._connection_manager.send_to_connection(connection.connection_id, widget_message)
        log.debug(f"📤 Sent confirmation button widget for item {item_id} with text '{button_text}'")

    async def send_confirmation_widget_from_item(
        self,
        connection: "Connection",
        context: "ConversationContext",
        item: Any,  # ConversationItemDto
    ) -> None:
        """Send a confirmation button widget from item DTO.

        Convenience method that extracts button text from the item.

        Args:
            connection: The WebSocket connection
            context: The conversation context
            item: The ConversationItemDto that requires confirmation
        """
        await self.send_confirmation_widget(
            connection=connection,
            context=context,
            item_id=item.id,
            button_text=item.confirmation_button_text,
        )

    async def send_widget_update(
        self,
        connection: "Connection",
        context: "ConversationContext",
        widget_id: str,
        state: str = "completed",
        value: Any = None,
    ) -> None:
        """Send a widget state update to the client.

        Args:
            connection: The WebSocket connection
            context: The conversation context
            widget_id: The widget to update
            state: New state ("completed", "disabled", "error")
            value: Optional new value
        """
        update_message = create_message(
            message_type="control.widget.update",
            payload={
                "widgetId": widget_id,
                "state": state,
                "value": value,
            },
            conversation_id=context.conversation_id,
        )

        await self._connection_manager.send_to_connection(connection.connection_id, update_message)
        log.debug(f"📤 Sent widget.update for {widget_id}: state={state}")
