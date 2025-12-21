"""Item presentation for template-driven conversations.

This module provides the ItemPresenter class which handles presenting
individual template items to clients, including rendering content,
sending widgets, and managing item state.
"""

import logging
from typing import TYPE_CHECKING, Any, Protocol

from application.orchestrator.context import ConversationContext, ItemExecutionState, OrchestratorState
from application.orchestrator.template.content_generator import ContentGenerator
from application.orchestrator.template.jinja_renderer import JinjaRenderer

if TYPE_CHECKING:
    from application.websocket.connection import Connection

log = logging.getLogger(__name__)


class ConnectionManagerProtocol(Protocol):
    """Protocol for connection manager interface."""

    async def send_to_connection(self, connection_id: str, message: dict) -> bool:
        """Send a message to a specific connection."""
        ...


class ItemPresenter:
    """Presents template items to WebSocket clients.

    Handles the presentation of template items including:
    - Rendering message content (streamed as agent response)
    - Sending interactive widgets
    - Sending confirmation buttons
    - Managing item execution state

    This class depends on:
    - ContentGenerator: For generating templated content
    - JinjaRenderer: For variable substitution in static content
    - ConnectionManager: For sending messages to clients

    Example:
        >>> presenter = ItemPresenter(
        ...     connection_manager=conn_mgr,
        ...     content_generator=content_gen,
        ...     jinja_renderer=jinja_renderer,
        ...     stream_response=stream_fn,
        ...     send_chat_input_enabled=chat_fn,
        ... )
        >>> await presenter.present_item(connection, context, item)
    """

    def __init__(
        self,
        connection_manager: ConnectionManagerProtocol,
        content_generator: ContentGenerator,
        jinja_renderer: JinjaRenderer | None = None,
        stream_response: Any = None,  # Callable for streaming agent responses
        send_chat_input_enabled: Any = None,  # Callable for chat input control
        send_item_context: Any = None,  # Callable for sending item context
    ) -> None:
        """Initialize the ItemPresenter.

        Args:
            connection_manager: Manager for WebSocket connections
            content_generator: Generator for LLM-based content
            jinja_renderer: Optional renderer for Jinja templates
            stream_response: Callback for streaming agent responses
            send_chat_input_enabled: Callback for enabling/disabling chat input
            send_item_context: Callback for sending item context to client
        """
        self._connection_manager = connection_manager
        self._content_generator = content_generator
        self._jinja_renderer = jinja_renderer or JinjaRenderer()
        self._stream_response = stream_response
        self._send_chat_input_enabled = send_chat_input_enabled
        self._send_item_context = send_item_context

    async def present_item(
        self,
        connection: "Connection",
        context: ConversationContext,
        item: Any,  # ConversationItemDto
        item_index: int,
    ) -> None:
        """Present a template item to the client.

        Renders each ItemContent in the item:
        - Message widgets: Stream as agent response
        - Interactive widgets: Send control.widget.render

        Args:
            connection: The WebSocket connection
            context: The conversation context
            item: The ConversationItemDto to present
            item_index: The 0-based index of the item
        """
        log.info(f"📋 Presenting item {item_index}: {item.id} - {item.title}")

        # Update context with item execution state
        context.current_item_index = item_index
        context.current_item_state = ItemExecutionState(
            item_id=item.id,
            item_index=item_index,
            required_widget_ids=set(c.id for c in item.contents if c.required and c.widget_type != "message"),
            require_user_confirmation=item.require_user_confirmation,
            confirmation_button_text=item.confirmation_button_text,
        )

        # Send item context to client
        if self._send_item_context:
            await self._send_item_context(connection, context, item_index, item)

        # Process each content in order
        sorted_contents = sorted(item.contents, key=lambda c: c.order)
        for content in sorted_contents:
            await self.render_content(connection, context, item, content)

        # If user confirmation is required, send a confirmation button widget
        if item.require_user_confirmation:
            await self.send_confirmation_widget(connection, context, item)

        # Update orchestrator state
        if context.current_item_state.required_widget_ids or item.require_user_confirmation:
            # Waiting for widget responses (and/or confirmation)
            context.state = OrchestratorState.SUSPENDED
            widget_count = len(context.current_item_state.required_widget_ids)
            confirm_str = " + confirmation" if item.require_user_confirmation else ""
            log.info(f"📋 Item {item_index} presented, waiting for {widget_count} required widgets{confirm_str}")
        else:
            # No required widgets (informational item), auto-advance after a short delay
            context.state = OrchestratorState.READY
            log.info(f"📋 Item {item_index} is informational, enabling chat input")
            # Enable chat input based on item setting
            if self._send_chat_input_enabled:
                await self._send_chat_input_enabled(connection, item.enable_chat_input)

    async def render_content(
        self,
        connection: "Connection",
        context: ConversationContext,
        item: Any,  # ConversationItemDto
        content: Any,  # ItemContentDto
    ) -> None:
        """Render a single ItemContent to the client.

        Args:
            connection: The WebSocket connection
            context: The conversation context
            item: The parent ConversationItemDto
            content: The ItemContentDto to render
        """
        content_id = getattr(content, "id", "unknown")
        widget_type = getattr(content, "widget_type", "message")
        is_templated = getattr(content, "is_templated", False)

        log.debug(f"📦 Rendering content {content_id}: type={widget_type}, templated={is_templated}")

        # Get the stem content (static or generate from template)
        stem = await self._get_content_stem(context, content, item)

        if widget_type == "message":
            # Message type: stream as agent response
            if stem and self._stream_response:
                await self._stream_response(connection, context, stem)
        else:
            # Interactive widget: send widget.render message
            await self.send_widget_render(connection, context, item, content, stem)

    async def _get_content_stem(
        self,
        context: ConversationContext,
        content: Any,  # ItemContentDto
        item: Any = None,  # ConversationItemDto
    ) -> str | None:
        """Get the stem content for an ItemContent.

        If content is templated, generates via LLM using item.instructions.
        For structured widgets (multiple_choice), also applies generated
        options, correct_answer, and explanation to the content object.
        Otherwise returns static stem with Jinja-style variable substitution.

        Args:
            context: The conversation context
            content: The ItemContentDto
            item: The parent ConversationItemDto (for instructions)

        Returns:
            The stem text, or None if unavailable
        """
        is_templated = getattr(content, "is_templated", False)
        static_stem = getattr(content, "stem", None)
        content_id = getattr(content, "id", "unknown")

        if not is_templated:
            # Static content - apply Jinja-style variable substitution if present
            if static_stem:
                return self._jinja_renderer.render(static_stem, context)
            return static_stem

        # Templated content: generate via LLM using item.instructions
        generated = await self._content_generator.generate(context, content, item)
        if generated:
            # Apply structured fields to content for widget rendering
            if generated.options is not None:
                content.options = generated.options
                log.debug(f"Applied {len(generated.options)} generated options to {content_id}")
            if generated.correct_answer is not None:
                content.correct_answer = generated.correct_answer
                log.debug(f"Applied generated correct_answer to {content_id}")
            if generated.explanation is not None:
                content.explanation = generated.explanation
                log.debug(f"Applied generated explanation to {content_id}")

            if generated.stem:
                return generated.stem

        # Fallback to static stem if generation failed
        if static_stem:
            log.warning(f"Templated content {content_id} falling back to static stem after generation failure")
            return self._jinja_renderer.render(static_stem, context)

        log.warning(f"Templated content {content_id} has no stem and generation failed")
        return None

    async def send_widget_render(
        self,
        connection: "Connection",
        context: ConversationContext,
        item: Any,  # ConversationItemDto
        content: Any,  # ItemContentDto
        stem: str | None,
    ) -> None:
        """Send a widget.render control message to the client.

        Args:
            connection: The WebSocket connection
            context: The conversation context
            item: The parent ConversationItemDto
            content: The ItemContentDto
            stem: The resolved stem text
        """
        from application.protocol import create_message
        from application.protocol.widgets.base import WidgetConstraints, WidgetLayout, WidgetRenderPayload

        # Build the render payload with options at top level, widget_config for settings
        render_payload = WidgetRenderPayload(
            itemId=item.id,
            widgetId=content.id,
            widgetType=content.widget_type,
            stem=stem,
            options=content.options if hasattr(content, "options") else None,
            widgetConfig=content.widget_config,
            required=content.required,
            skippable=content.skippable,
            initialValue=content.initial_value,
            showUserResponse=content.show_user_response,
            layout=WidgetLayout(mode="flow"),
            constraints=WidgetConstraints(
                moveable=False,
                resizable=False,
                dismissable=content.skippable,
            ),
        )

        widget_message = create_message(
            message_type="control.widget.render",
            payload=render_payload.model_dump(by_alias=True, exclude_none=True),
            conversation_id=context.conversation_id,
        )

        await self._connection_manager.send_to_connection(connection.connection_id, widget_message)
        log.debug(f"📤 Sent widget.render for {content.id} ({content.widget_type})")

    async def send_confirmation_widget(
        self,
        connection: "Connection",
        context: ConversationContext,
        item: Any,  # ConversationItemDto
    ) -> None:
        """Send a confirmation button widget for items requiring user confirmation.

        Args:
            connection: The WebSocket connection
            context: The conversation context
            item: The ConversationItemDto that requires confirmation
        """
        from application.protocol import create_message
        from application.protocol.widgets.base import WidgetConstraints, WidgetLayout, WidgetRenderPayload

        # Generate a unique widget ID for the confirmation button
        confirmation_widget_id = f"{item.id}-confirm"

        # Build the render payload for a submit button widget
        render_payload = WidgetRenderPayload(
            itemId=item.id,
            widgetId=confirmation_widget_id,
            widgetType="button",
            stem=None,  # No stem text for confirmation button
            options=None,
            widgetConfig={
                "label": item.confirmation_button_text,
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
        log.debug(f"📤 Sent confirmation button widget for item {item.id} with text '{item.confirmation_button_text}'")
