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


class MediatorProtocol(Protocol):
    """Protocol for mediator interface."""

    async def execute_async(self, query: Any) -> Any:
        """Execute a query asynchronously."""
        ...


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
        mediator: MediatorProtocol | None = None,
        jinja_renderer: JinjaRenderer | None = None,
        stream_response: Any = None,  # Callable for streaming agent responses
        send_chat_input_enabled: Any = None,  # Callable for chat input control
        send_item_context: Any = None,  # Callable for sending item context
    ) -> None:
        """Initialize the ItemPresenter.

        Args:
            connection_manager: Manager for WebSocket connections
            content_generator: Generator for LLM-based content
            mediator: Mediator for executing domain commands
            jinja_renderer: Optional renderer for Jinja templates
            stream_response: Callback for streaming agent responses
            send_chat_input_enabled: Callback for enabling/disabling chat input
            send_item_context: Callback for sending item context to client
        """
        self._connection_manager = connection_manager
        self._content_generator = content_generator
        self._mediator = mediator
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

        # Extract stem and correct answer from item contents for scoring
        # Use the first non-message content's stem/correct_answer
        item_stem = ""
        correct_answer = None
        for content in item.contents:
            if content.widget_type != "message":
                if content.stem:
                    item_stem = content.stem
                if content.correct_answer:
                    correct_answer = content.correct_answer
                break  # Use first interactive content

        # Display widget types that don't collect user responses
        # These should NOT be in required_widget_ids even if marked required
        display_widget_types = {
            "message",
            "text_display",
            "image_display",
            "video",
            "chart",
            "data_table",
            "document_viewer",
            "sticky_note",
            "graph_topology",
        }

        # Update context with item execution state
        context.current_item_index = item_index
        context.current_item_state = ItemExecutionState(
            item_id=item.id,
            item_index=item_index,
            required_widget_ids=set(c.id for c in item.contents if c.required and c.widget_type not in display_widget_types),
            require_user_confirmation=item.require_user_confirmation,
            confirmation_button_text=item.confirmation_button_text,
            item_title=item.title or f"Item {item_index + 1}",
            item_stem=item_stem,
            provide_feedback=item.provide_feedback,
            correct_answer=correct_answer,
        )

        # Send item context to client
        if self._send_item_context:
            await self._send_item_context(connection, context, item_index, item)

        # Process each content in order
        sorted_contents = sorted(item.contents, key=lambda c: c.order)
        log.info(f"📋 [present_item] Processing {len(sorted_contents)} contents in order:")
        for i, c in enumerate(sorted_contents):
            log.info(f"   [{i}] id={c.id}, widget_type={c.widget_type}, order={c.order}, required={c.required}")

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
            # Handle chat input based on item setting when waiting for widgets
            if self._send_chat_input_enabled:
                if item.enable_chat_input:
                    await self._send_chat_input_enabled(connection, True)
                else:
                    # Chat disabled while waiting for widget interaction
                    await self._send_chat_input_enabled(connection, False, placeholder="Use the options above to respond")
        else:
            # No required widgets (informational item), auto-advance after a short delay
            context.state = OrchestratorState.READY
            log.info(f"📋 Item {item_index} is informational, enabling chat input")
            # Enable chat input based on item setting
            if self._send_chat_input_enabled:
                if item.enable_chat_input:
                    await self._send_chat_input_enabled(connection, True)
                else:
                    # Chat disabled for this item - show appropriate placeholder
                    await self._send_chat_input_enabled(connection, False, placeholder="Use the options above to respond")

    async def render_content(
        self,
        connection: "Connection",
        context: ConversationContext,
        item: Any,  # ConversationItemDto
        content: Any,  # ItemContentDto
    ) -> None:
        """Render a single ItemContent to the client.

        Renders the content and persists it as a message for conversation history.

        Args:
            connection: The WebSocket connection
            context: The conversation context
            item: The parent ConversationItemDto
            content: The ItemContentDto to render
        """
        content_id = getattr(content, "id", "unknown")
        widget_type = getattr(content, "widget_type", "message")
        is_templated = getattr(content, "is_templated", False)
        content_order = getattr(content, "order", -1)

        log.info(f"📦 [render_content] START content_id={content_id}, widget_type={widget_type}, order={content_order}, templated={is_templated}")

        # Get the stem content (static or generate from template)
        stem = await self._get_content_stem(context, content, item)
        log.debug(f"📦 [render_content] stem resolved: stem_length={len(stem) if stem else 0}")

        if widget_type == "message":
            # Message type: stream as agent response
            log.info(f"📤 [render_content] Streaming message content for {content_id}")
            if stem and self._stream_response:
                await self._stream_response(connection, context, stem)
            # Persist message content
            await self._persist_content_message(context, item, content, stem)
        else:
            # Interactive widget: send widget.render message
            log.info(f"📤 [render_content] Sending widget.render for {content_id} (widget_type={widget_type})")
            await self.send_widget_render(connection, context, item, content, stem)
            log.info(f"📤 [render_content] SENT widget.render for {content_id}")
            # Persist widget content with full widget structure
            await self._persist_content_message(context, item, content, stem)

        log.info(f"📦 [render_content] END content_id={content_id}")

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

        Also stores widget configuration in context for later persistence.

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

        # Store widget configuration in context for later persistence
        if context.current_item_state:
            context.current_item_state.widget_configs[content.id] = {
                "widget_type": content.widget_type,
                "stem": stem,
                "options": content.options if hasattr(content, "options") else None,
                "widget_config": content.widget_config,
            }

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

    async def _persist_content_message(
        self,
        context: ConversationContext,
        item: Any,  # ConversationItemDto
        content: Any,  # ItemContentDto
        stem: str | None,
    ) -> None:
        """Persist content as a message for conversation history.

        This ensures that item content (message and widget content) is persisted
        so it can be displayed when resuming a conversation.

        Args:
            context: The conversation context
            item: The parent ConversationItemDto
            content: The ItemContentDto being rendered
            stem: The resolved stem text
        """
        if not self._mediator:
            log.debug("No mediator available, skipping content persistence")
            return

        if not stem:
            log.debug(f"No stem content to persist for {content.id}")
            return

        from application.commands.conversation import AddContentMessageCommand, WidgetConfig

        try:
            widget_type = getattr(content, "widget_type", "message")
            content_id = getattr(content, "id", "unknown")
            item_index = context.current_item_index

            # Build widget config for non-message content types
            widget_config = None
            if widget_type != "message":
                # Include full widget structure for read-only display on resume
                widget_config = WidgetConfig(
                    widget_id=content_id,
                    widget_type=widget_type,
                    item_id=item.id,
                    item_index=item_index,
                    stem=stem,
                    options=getattr(content, "options", None),
                    correct_answer=getattr(content, "correct_answer", None),
                    widget_config=getattr(content, "widget_config", None),
                    required=getattr(content, "required", False),
                    skippable=getattr(content, "skippable", False),
                    initial_value=getattr(content, "initial_value", None),
                    show_user_response=getattr(content, "show_user_response", True),
                )

            # Persist the content message
            await self._mediator.execute_async(
                AddContentMessageCommand(
                    conversation_id=context.conversation_id,
                    content=stem,
                    role="assistant",
                    item_id=item.id,
                    item_index=item_index,
                    widget_config=widget_config,
                    message_type="item_content" if widget_type == "message" else "widget_content",
                    metadata={
                        "content_id": content_id,
                        "widget_type": widget_type,
                        "item_title": item.title,
                    },
                    user_info={"sub": context.user_id},
                )
            )
            log.debug(f"📝 Persisted content message {content_id} for item {item.id}")

        except Exception as e:
            log.warning(f"Failed to persist content message: {e}")
