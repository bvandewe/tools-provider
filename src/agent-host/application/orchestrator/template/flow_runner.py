"""Flow runner for template-driven conversations.

This module provides the FlowRunner class which manages the execution
of proactive template-driven conversation flows, including item
progression and flow completion.
"""

import logging
from typing import TYPE_CHECKING, Any, Protocol

from application.orchestrator.context import ConversationContext, OrchestratorState

if TYPE_CHECKING:
    from application.websocket.connection import Connection

log = logging.getLogger(__name__)


class MediatorProtocol(Protocol):
    """Protocol for mediator interface."""

    async def execute_async(self, query: Any) -> Any:
        """Execute a query asynchronously."""
        ...


class ItemPresenterProtocol(Protocol):
    """Protocol for item presenter interface."""

    async def present_item(
        self,
        connection: Any,
        context: "ConversationContext",
        item: Any,
        item_index: int,
    ) -> None:
        """Present a template item to the client."""
        ...


class FlowRunner:
    """Runs proactive template-driven conversation flows.

    This class manages the overall flow of a template-driven conversation:
    - Starting the proactive flow with introduction
    - Loading and presenting items via ItemPresenter
    - Advancing through items
    - Completing the flow with completion message

    This class depends on:
    - Mediator: For querying template items
    - ItemPresenter: For presenting individual items
    - Callbacks: For streaming responses, sending errors, etc.

    Example:
        >>> runner = FlowRunner(
        ...     mediator=mediator,
        ...     item_presenter=presenter,
        ...     stream_response=stream_fn,
        ...     send_error=error_fn,
        ...     send_chat_input_enabled=chat_fn,
        ... )
        >>> await runner.run_proactive_flow(connection, context)
    """

    def __init__(
        self,
        mediator: MediatorProtocol,
        item_presenter: ItemPresenterProtocol,
        stream_response: Any = None,  # Callable for streaming agent responses
        send_error: Any = None,  # Callable for sending errors
        send_chat_input_enabled: Any = None,  # Callable for chat input control
    ) -> None:
        """Initialize the FlowRunner.

        Args:
            mediator: Mediator for executing queries
            item_presenter: Presenter for individual items
            stream_response: Callback for streaming agent responses
            send_error: Callback for sending error messages
            send_chat_input_enabled: Callback for enabling/disabling chat input
        """
        self._mediator = mediator
        self._item_presenter = item_presenter
        self._stream_response = stream_response
        self._send_error = send_error
        self._send_chat_input_enabled = send_chat_input_enabled

    async def run_proactive_flow(
        self,
        connection: "Connection",
        context: ConversationContext,
    ) -> None:
        """Run the proactive conversation flow.

        This method executes the template-driven flow where the agent
        leads the conversation, presenting items and collecting responses.

        Flow:
        1. Send introduction message (if configured)
        2. Disable chat input (per template config)
        3. Load and present the first item
        4. Wait for widget responses (handled by handle_widget_response)

        Args:
            connection: The WebSocket connection
            context: The conversation context
        """
        log.info(f"🎭 Starting proactive flow: conversation={context.conversation_id}, template={context.template_id}")

        try:
            # Disable chat input initially (per template config)
            enable_chat_initially = context.template_config.get("enable_chat_input_initially", False)
            if self._send_chat_input_enabled:
                await self._send_chat_input_enabled(connection, enable_chat_initially)

            # Send introduction message if configured
            intro_message = context.template_config.get("introduction_message")
            if intro_message and self._stream_response:
                await self._stream_response(connection, context, intro_message)

            # Present the first item
            await self._present_item_at_index(connection, context, 0)

        except Exception as e:
            log.exception(f"Error in proactive flow: {e}")
            context.state = OrchestratorState.ERROR
            if self._send_error:
                await self._send_error(connection, "FLOW_ERROR", str(e))

    async def advance_to_next_item(
        self,
        connection: "Connection",
        context: ConversationContext,
    ) -> None:
        """Advance to the next template item.

        Called when all required widgets in the current item have been answered.

        Args:
            connection: The WebSocket connection
            context: The conversation context
        """
        next_index = context.current_item_index + 1

        if next_index >= context.total_items:
            # All items completed
            await self.complete_flow(connection, context)
        else:
            # Present next item
            await self._present_item_at_index(connection, context, next_index)

    async def complete_flow(
        self,
        connection: "Connection",
        context: ConversationContext,
    ) -> None:
        """Complete the proactive conversation flow.

        Sends completion message and transitions to final state.

        Args:
            connection: The WebSocket connection
            context: The conversation context
        """
        log.info(f"🎭 Completing proactive flow: conversation={context.conversation_id}")

        # Send completion message if configured
        completion_message = context.template_config.get("completion_message")
        if completion_message and self._stream_response:
            await self._stream_response(connection, context, completion_message)

        # Check if we should continue with free chat after completion
        continue_after = context.template_config.get("continue_after_completion", False)
        if continue_after:
            context.state = OrchestratorState.READY
            if self._send_chat_input_enabled:
                await self._send_chat_input_enabled(connection, True)
            log.info("🎭 Proactive flow complete, continuing with free chat")
        else:
            context.state = OrchestratorState.COMPLETED
            if self._send_chat_input_enabled:
                await self._send_chat_input_enabled(connection, False)
            log.info("🎭 Proactive flow complete, conversation ended")

        # TODO: Send final score report if configured
        # if context.template_config.get("display_final_score_report"):
        #     await self._send_score_report(connection, context)

    async def _present_item_at_index(
        self,
        connection: "Connection",
        context: ConversationContext,
        item_index: int,
    ) -> None:
        """Load and present a template item by index.

        Args:
            connection: The WebSocket connection
            context: The conversation context
            item_index: The 0-based index of the item to present
        """
        from application.queries import GetTemplateItemQuery

        if not context.template_id:
            log.error("No template_id in context for proactive flow")
            if self._send_error:
                await self._send_error(connection, "NO_TEMPLATE", "Template not configured")
            return

        # Query the specific item
        user_info = {"sub": context.user_id}
        result = await self._mediator.execute_async(
            GetTemplateItemQuery(
                template_id=context.template_id,
                item_index=item_index,
                user_info=user_info,
                for_client=False,  # Server needs correct_answer for scoring
            )
        )

        if not result.is_success or result.data is None:
            # Check if we've completed all items
            if item_index >= context.total_items:
                await self.complete_flow(connection, context)
                return
            else:
                log.error(f"Failed to load item {item_index}: {result.errors}")
                if self._send_error:
                    await self._send_error(connection, "ITEM_LOAD_FAILED", f"Failed to load item {item_index}")
                return

        item = result.data

        # Delegate to item presenter
        await self._item_presenter.present_item(connection, context, item, item_index)
