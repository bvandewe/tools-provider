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
    - Mediator: For querying template items and persisting messages
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
        send_panel_header: Any = None,  # Callable for sending panel header updates
        generate_score_report: Any = None,  # Callable for generating final score report
    ) -> None:
        """Initialize the FlowRunner.

        Args:
            mediator: Mediator for executing queries and commands
            item_presenter: Presenter for individual items
            stream_response: Callback for streaming agent responses
            send_error: Callback for sending error messages
            send_chat_input_enabled: Callback for enabling/disabling chat input
            send_panel_header: Callback for sending panel header updates (progress, title, score)
            generate_score_report: Callback for generating final score report via LLM
        """
        self._mediator = mediator
        self._item_presenter = item_presenter
        self._stream_response = stream_response
        self._send_error = send_error
        self._send_chat_input_enabled = send_chat_input_enabled
        self._send_panel_header = send_panel_header
        self._generate_score_report = generate_score_report

    async def run_proactive_flow(
        self,
        connection: "Connection",
        context: ConversationContext,
    ) -> None:
        """Run the proactive conversation flow.

        This method executes the template-driven flow where the agent
        leads the conversation, presenting items and collecting responses.

        Flow:
        1. Send introduction message (if configured) - persisted as virtual message
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

            # Send and persist introduction message if configured
            intro_message = context.template_config.get("introduction_message")
            if intro_message:
                await self._send_and_persist_virtual_message(connection, context, intro_message, message_type="intro")

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
        log.info(f"🔄 [advance_to_next_item] current_item_index={context.current_item_index}, next_index={next_index}, total_items={context.total_items}")

        if next_index >= context.total_items:
            # All items completed
            log.info("🔄 [advance_to_next_item] All items completed, calling complete_flow")
            await self.complete_flow(connection, context)
        else:
            # Present next item
            log.info(f"🔄 [advance_to_next_item] Presenting next item at index {next_index}")
            await self._present_item_at_index(connection, context, next_index)

    async def complete_flow(
        self,
        connection: "Connection",
        context: ConversationContext,
    ) -> None:
        """Complete the proactive conversation flow.

        Sends completion message, optional score report, and transitions to final state.
        Virtual messages are persisted to the conversation.
        The completion status is persisted via CompleteConversationCommand.

        Args:
            connection: The WebSocket connection
            context: The conversation context
        """
        from application.commands.conversation import CompleteConversationCommand

        log.info(f"🎭 Completing proactive flow: conversation={context.conversation_id}")

        # Generate and stream final score report if configured
        display_score_report = context.template_config.get("display_final_score_report", False)
        if display_score_report and self._generate_score_report:
            await self._generate_score_report(connection, context)
            log.info(f"📊 Generated final score report for {context.conversation_id}")

        # Send and persist completion message if configured (after score report)
        completion_message = context.template_config.get("completion_message")
        if completion_message:
            await self._send_and_persist_virtual_message(connection, context, completion_message, message_type="completion")

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
                # Hide all chat input buttons for completed conversations
                await self._send_chat_input_enabled(connection, False, hide_all=True)
            log.info("🎭 Proactive flow complete, conversation ended")

            # Persist the completion status to the domain
            try:
                await self._mediator.execute_async(
                    CompleteConversationCommand(
                        conversation_id=context.conversation_id,
                        summary={"template_completed": True, "total_items": context.total_items},
                        user_info={"sub": context.user_id},
                    )
                )
                log.debug(f"📝 Persisted completion status for {context.conversation_id}")
            except Exception as e:
                log.warning(f"Failed to persist completion status: {e}")

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

        # Send panel header update with progress and title
        if self._send_panel_header:
            await self._send_panel_header(
                connection,
                context,
                item_id=item.id,
                item_index=item_index,
                item_title=item.title,
            )

        # Delegate to item presenter
        await self._item_presenter.present_item(connection, context, item, item_index)

    async def _send_and_persist_virtual_message(
        self,
        connection: "Connection",
        context: ConversationContext,
        content: str,
        message_type: str = "virtual",
    ) -> None:
        """Stream a virtual message to the client and persist it.

        Virtual messages are system-generated content (intro, completion, etc.)
        that should appear as regular assistant messages.

        Args:
            connection: The WebSocket connection
            context: The conversation context
            content: The message content
            message_type: Type of virtual message (intro, completion, report)
        """
        from application.commands.conversation import AddVirtualMessageCommand

        # Stream to client
        if self._stream_response:
            await self._stream_response(connection, context, content)

        # Persist via command
        try:
            await self._mediator.execute_async(
                AddVirtualMessageCommand(
                    conversation_id=context.conversation_id,
                    content=content,
                    message_type=message_type,
                    user_info={"sub": context.user_id},
                )
            )
            log.debug(f"📝 Persisted {message_type} virtual message for {context.conversation_id}")
        except Exception as e:
            log.warning(f"Failed to persist virtual message: {e}")
