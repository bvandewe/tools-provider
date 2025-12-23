"""Widget handler for widget interactions and responses.

This handler processes widget responses from clients, tracks completion
state, and coordinates with domain commands to persist responses.
"""

import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from neuroglia.mediation import Mediator

from application.orchestrator.context import ConversationContext, ItemExecutionState, OrchestratorState
from application.protocol.core import create_message

if TYPE_CHECKING:
    from application.websocket.connection import Connection
    from application.websocket.manager import ConnectionManager

log = logging.getLogger(__name__)


class WidgetHandler:
    """Handles widget responses and confirmation flows.

    Responsibilities:
    - Tracks widget responses in item state
    - Determines when items are complete (all required widgets answered)
    - Persists responses via domain commands
    - Coordinates item advancement in proactive mode

    This handler is crucial for template-based conversations where
    users interact with widgets to provide structured responses.
    """

    def __init__(
        self,
        mediator: Mediator,
        connection_manager: "ConnectionManager",
    ):
        """Initialize the widget handler.

        Args:
            mediator: Neuroglia Mediator for CQRS command/query dispatch
            connection_manager: WebSocket connection manager for sending messages
        """
        self._mediator = mediator
        self._connection_manager = connection_manager

    async def handle_widget_response(
        self,
        connection: "Connection",
        context: ConversationContext,
        widget_id: str,
        item_id: str,
        value: Any,
        advance_callback: Callable[["Connection", ConversationContext], Awaitable[None]] | None = None,
        score_callback: Callable[["Connection", ConversationContext, "ItemExecutionState"], Awaitable[None]] | None = None,
        metadata: dict[str, Any] | None = None,
        batch_mode: bool = False,
    ) -> None:
        """Handle a widget response from the client.

        For proactive conversations:
        1. Records the response in the current item state
        2. Tracks which required widgets have been answered
        3. Scores the response using LLM (if score_callback provided)
        4. Advances to next item when all required widgets are answered

        Args:
            connection: The WebSocket connection
            context: The conversation context
            widget_id: The widget that was responded to
            item_id: The item containing the widget
            value: The response value
            advance_callback: Callback to advance to next item (for proactive mode)
            score_callback: Callback to score item response using LLM
            metadata: Optional response metadata
            batch_mode: If True, only record the response without checking completion
        """
        log.info(f"📝 [handle_widget_response] START widget={widget_id}, item={item_id}, value={value}, batch_mode={batch_mode}")
        log.info(f"📝 [handle_widget_response] context.is_proactive={context.is_proactive}, has_template={context.has_template}")

        context.last_activity = datetime.now(UTC)

        # Send acknowledgment
        await self._send_response_ack(connection, context, widget_id, item_id)

        # Track response in item state
        if not context.current_item_state or context.current_item_state.item_id != item_id:
            # Response for a different item (shouldn't happen normally)
            log.warning(f"Widget response for unexpected item: expected={context.current_item_state.item_id if context.current_item_state else 'None'}, got={item_id}")
            # For reactive mode, just go back to ready
            if not context.is_proactive:
                context.state = OrchestratorState.READY
            return

        item_state = context.current_item_state

        # Check if this is a confirmation button click
        confirmation_widget_id = f"{item_id}-confirm"
        if widget_id == confirmation_widget_id:
            log.info(f"📝 User confirmed item {item_id}")
            item_state.user_confirmed = True
        else:
            # Store the response
            item_state.widget_responses[widget_id] = value

            # Mark widget as answered if it was required
            if widget_id in item_state.required_widget_ids:
                item_state.answered_widget_ids.add(widget_id)
                log.info(f"📝 Required widget answered: {widget_id} ({len(item_state.answered_widget_ids)}/{len(item_state.required_widget_ids)})")
            else:
                log.info(f"📝 Non-required widget response stored: {widget_id}")

        # In batch mode, just record the response and return (don't check completion)
        if batch_mode:
            log.debug(f"📝 Batch mode - recorded response for {widget_id}, waiting for confirmation")
            return

        # Check if all required widgets are answered (and confirmed if needed)
        log.info(
            f"📝 [handle_widget_response] Checking is_complete: required={item_state.required_widget_ids}, answered={item_state.answered_widget_ids}, require_confirm={item_state.require_user_confirmation}, user_confirmed={item_state.user_confirmed}"
        )
        if item_state.is_complete:
            log.info(f"📋 Item {item_id} complete, all requirements met, advance_callback={advance_callback is not None}")
            item_state.completed_at = datetime.now(UTC)

            # Score the response using LLM (if callback provided)
            if score_callback:
                await score_callback(connection, context, item_state)
                log.info(f"🎯 Scored item {item_id}: result={item_state.scoring_result}")

            # Dispatch domain commands to persist responses (including scoring)
            await self.persist_item_response(connection, context, item_state)

            # Advance to next item in proactive mode
            if context.is_proactive and context.has_template and advance_callback:
                await advance_callback(connection, context)
            else:
                context.state = OrchestratorState.READY
        else:
            # Still waiting for more responses (or confirmation)
            pending = item_state.pending_widget_ids
            needs_confirm = item_state.require_user_confirmation and not item_state.user_confirmed
            log.debug(f"📋 Item {item_id} still waiting: widgets={pending}, needs_confirm={needs_confirm}")

    async def _send_response_ack(
        self,
        connection: "Connection",
        context: ConversationContext,
        widget_id: str,
        item_id: str,
    ) -> None:
        """Send widget response acknowledgment to client."""
        ack_message = create_message(
            message_type="data.response.ack",
            payload={
                "widgetId": widget_id,
                "itemId": item_id,
                "status": "received",
            },
            conversation_id=context.conversation_id,
        )
        await self._connection_manager.send_to_connection(connection.connection_id, ack_message)

    async def persist_item_response(
        self,
        connection: "Connection",
        context: ConversationContext,
        item_state: ItemExecutionState,
    ) -> None:
        """Persist item responses to the conversation aggregate via domain commands.

        Dispatches RecordItemResponseCommand and AdvanceTemplateCommand to persist
        the item responses and advance the template progress.

        Args:
            connection: The WebSocket connection
            context: The conversation context
            item_state: The completed item execution state
        """
        from application.commands.conversation import (
            AdvanceTemplateCommand,
            RecordItemResponseCommand,
            WidgetResponse,
        )

        if not context.conversation_id:
            log.error("Cannot persist item response: no conversation_id in context")
            return

        try:
            # Calculate response time
            response_time_ms = None
            if item_state.started_at and item_state.completed_at:
                delta = item_state.completed_at - item_state.started_at
                response_time_ms = int(delta.total_seconds() * 1000)

            # Extract scoring data if available
            scoring = item_state.scoring_result or {}
            is_correct = scoring.get("is_correct")
            score = scoring.get("score")
            max_score = scoring.get("max_score")

            # Build widget responses with scoring data and widget configurations
            widget_responses = []
            for widget_id, value in item_state.widget_responses.items():
                widget_config = item_state.widget_configs.get(widget_id, {})
                widget_responses.append(
                    WidgetResponse(
                        widget_id=widget_id,
                        value=value,
                        content_id=widget_id,  # Use widget_id as content_id for now
                        widget_type=widget_config.get("widget_type"),
                        stem=widget_config.get("stem"),
                        options=widget_config.get("options"),
                        is_correct=is_correct,
                        score=score,
                        max_score=max_score,
                    )
                )

            # Dispatch RecordItemResponseCommand
            user_info = {"sub": context.user_id} if context.user_id else None
            record_result = await self._mediator.execute_async(
                RecordItemResponseCommand(
                    conversation_id=context.conversation_id,
                    item_id=item_state.item_id,
                    item_index=item_state.item_index,
                    responses=widget_responses,
                    response_time_ms=response_time_ms,
                    user_info=user_info,
                )
            )

            if not record_result.is_success:
                log.error(f"Failed to record item response: {record_result.errors}")
            else:
                log.info(f"✅ Persisted item response for {item_state.item_id}")

            # Dispatch AdvanceTemplateCommand
            advance_result = await self._mediator.execute_async(
                AdvanceTemplateCommand(
                    conversation_id=context.conversation_id,
                    user_info=user_info,
                )
            )

            if not advance_result.is_success:
                log.error(f"Failed to advance template: {advance_result.errors}")
            else:
                log.info(f"✅ Advanced template progress for conversation {context.conversation_id}")

        except Exception as e:
            log.exception(f"Error persisting item response: {e}")
            # Don't fail the flow - the response is still tracked in memory
