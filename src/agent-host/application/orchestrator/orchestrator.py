"""Conversation Orchestrator - Slim coordinator for conversation flow.

This is the main orchestrator that coordinates all conversation logic:
- Initializing conversation context on WebSocket connect
- Routing messages to appropriate handlers
- Managing conversation state machine
- Coordinating agent execution and template flows

Architecture:
    WebSocket Handler → Orchestrator → Handlers → Domain Commands
                                    ↓
                              Agent Execution → AgentEvents
                                    ↓
                            Protocol Messages → WebSocket → Client

The orchestrator delegates actual work to specialized handlers and senders,
keeping this class focused on coordination and routing.
"""

import asyncio
import logging
import uuid
from typing import TYPE_CHECKING, Any

from neuroglia.mediation import Mediator

from application.agents import Agent
from application.orchestrator.agent import AgentRunner, StreamHandler, ToolExecutor
from application.orchestrator.context import ConversationContext, OrchestratorState
from application.orchestrator.handlers import FlowHandler, MessageHandler, ModelHandler, WidgetHandler
from application.orchestrator.protocol import ConfigSender, ContentSender, WidgetSender
from application.orchestrator.template import ContentGenerator, FlowRunner, ItemPresenter, JinjaRenderer
from application.protocol.core import create_message
from application.protocol.data import ContentChunkPayload, ContentCompletePayload

if TYPE_CHECKING:
    from application.services.tool_provider_client import ToolProviderClient
    from application.websocket.connection import Connection
    from application.websocket.manager import ConnectionManager
    from infrastructure.llm_provider_factory import LlmProviderFactory

log = logging.getLogger(__name__)


class Orchestrator:
    """Conversation orchestrator - thin coordinator delegating to handlers.

    This class provides the public interface for conversation orchestration
    while delegating actual work to specialized handlers:

    - MessageHandler: User text message processing
    - WidgetHandler: Widget response handling
    - FlowHandler: Flow control (start/pause/cancel)
    - ModelHandler: LLM model selection
    - AgentRunner: Agent execution and streaming
    - ItemPresenter: Template item presentation
    - FlowRunner: Proactive flow execution

    Usage:
        orchestrator = Orchestrator(
            mediator=mediator,
            connection_manager=manager,
            agent=agent,
            llm_provider_factory=factory,
            tool_provider_client=client,
        )

        # On WebSocket connect
        await orchestrator.initialize(connection, conversation_id)

        # On user message
        await orchestrator.handle_user_message(connection, content)
    """

    def __init__(
        self,
        mediator: Mediator,
        connection_manager: "ConnectionManager",
        agent: Agent,
        llm_provider_factory: "LlmProviderFactory",
        tool_provider_client: "ToolProviderClient | None" = None,
    ):
        """Initialize the orchestrator with all dependencies.

        Args:
            mediator: Neuroglia Mediator for CQRS command/query dispatch
            connection_manager: WebSocket connection manager
            agent: The Agent instance for LLM interactions
            llm_provider_factory: Factory for creating LLM providers
            tool_provider_client: Optional client for tool execution
        """
        self._mediator = mediator
        self._connection_manager = connection_manager
        self._agent = agent
        self._llm_provider_factory = llm_provider_factory
        self._tool_provider_client = tool_provider_client

        # Initialize handlers
        self._message_handler = MessageHandler(mediator, connection_manager)
        self._widget_handler = WidgetHandler(mediator, connection_manager)
        self._flow_handler = FlowHandler(connection_manager)
        self._model_handler = ModelHandler(llm_provider_factory)

        # Initialize protocol senders
        self._config_sender = ConfigSender(connection_manager)
        self._widget_sender = WidgetSender(connection_manager)
        self._content_sender = ContentSender(connection_manager)

        # Initialize template processors
        self._jinja_renderer = JinjaRenderer()
        self._content_generator = ContentGenerator(llm_provider_factory, self._jinja_renderer)

        # Note: ItemPresenter and FlowRunner need callbacks that are methods of self.
        # We initialize them here and they can access self's methods via bound method references.
        self._item_presenter = ItemPresenter(
            connection_manager=connection_manager,  # type: ignore[arg-type]  # ConnectionManager is compatible at runtime
            content_generator=self._content_generator,
            jinja_renderer=self._jinja_renderer,
            stream_response=self._stream_response,
            send_chat_input_enabled=self._send_chat_input_enabled,
            send_item_context=self._send_item_context,
        )

        # Initialize agent execution
        self._tool_executor = ToolExecutor(tool_provider_client)
        self._stream_handler = StreamHandler(connection_manager)
        self._agent_runner = AgentRunner(
            agent=agent,
            mediator=mediator,  # type: ignore[arg-type]  # Neuroglia Mediator is compatible at runtime
            connection_manager=connection_manager,  # type: ignore[arg-type]  # ConnectionManager is compatible at runtime
            llm_provider_factory=llm_provider_factory,
            tool_executor=self._tool_executor,
            send_chat_input_enabled=self._send_chat_input_enabled,
            send_error=self._send_error,
        )

        # Initialize flow runner
        self._flow_runner = FlowRunner(
            mediator=mediator,  # type: ignore[arg-type]  # Neuroglia Mediator is compatible at runtime
            item_presenter=self._item_presenter,
            stream_response=self._stream_response,
            send_error=self._send_error,
            send_chat_input_enabled=self._send_chat_input_enabled,
        )

        # Connection contexts (connection_id -> ConversationContext)
        self._contexts: dict[str, ConversationContext] = {}

    # =========================================================================
    # Public Properties
    # =========================================================================

    @property
    def llm_provider_factory(self) -> "LlmProviderFactory":
        """Get the LLM provider factory."""
        return self._llm_provider_factory

    # =========================================================================
    # Lifecycle Methods
    # =========================================================================

    async def initialize(self, connection: "Connection", conversation_id: str) -> None:
        """Initialize orchestrator for a new connection.

        Loads conversation context, tools, and prepares for message handling.

        Args:
            connection: The WebSocket connection
            conversation_id: The conversation ID to load
        """
        from application.queries import GetConversationQuery

        log.info(f"🎭 Initializing orchestrator for conversation {conversation_id}")

        # Load conversation from read model
        user_info = {"sub": connection.user_id}
        result = await self._mediator.execute_async(GetConversationQuery(conversation_id=conversation_id, user_info=user_info))

        if not result.is_success or not result.data:
            raise ValueError(f"Conversation {conversation_id} not found")

        conv_dto = result.data

        # Create context
        context = ConversationContext(
            connection_id=connection.connection_id,
            conversation_id=conversation_id,
            user_id=connection.user_id,
            definition_id=conv_dto.definition_id,
            access_token=connection.access_token,
        )

        # Load definition for template info
        if conv_dto.definition_id:
            await self._load_definition_context(context, conv_dto.definition_id, user_info)

        # Load tools
        await self._load_tools(context)

        # Store context
        self._contexts[connection.connection_id] = context

        log.info(f"✅ Orchestrator initialized: {context}")

    async def start_conversation_flow(self, connection: "Connection") -> None:
        """Start the conversation flow after initialization.

        For proactive conversations, begins presenting template items.
        For reactive conversations, enables chat input.

        Args:
            connection: The WebSocket connection
        """
        context = self._contexts.get(connection.connection_id)
        if not context:
            log.warning(f"No context for connection {connection.connection_id}")
            return

        # Send initial configuration
        await self._config_sender.send_conversation_config(connection, context)

        # Start flow based on mode
        if context.is_proactive and context.has_template:
            context.state = OrchestratorState.PRESENTING
            await self._flow_runner.run_proactive_flow(connection, context)
        else:
            context.state = OrchestratorState.READY
            await self._send_chat_input_enabled(connection, True)

    async def cleanup(self, connection_id: str) -> None:
        """Cleanup orchestrator state for a disconnected connection.

        Args:
            connection_id: The connection ID to cleanup
        """
        if connection_id in self._contexts:
            del self._contexts[connection_id]
            log.debug(f"Cleaned up context for connection {connection_id}")

    # =========================================================================
    # Message Handlers
    # =========================================================================

    async def handle_user_message(
        self,
        connection: "Connection",
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Handle a user message from the client.

        Args:
            connection: The WebSocket connection
            content: The message content
            metadata: Optional message metadata (messageId, timestamp, etc.)
        """
        context = self._contexts.get(connection.connection_id)
        if not context:
            await self._send_error(connection, "NO_CONTEXT", "No conversation context found")
            return

        await self._message_handler.handle_user_message(
            connection=connection,
            context=context,
            content=content,
            agent_runner=self._run_agent_stream,
            error_sender=self._send_error,
        )

    async def handle_widget_response(
        self,
        connection: "Connection",
        widget_id: str,
        value: Any,
        item_id: str | None = None,
        confirmation_required: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Handle a widget response from the client.

        Args:
            connection: The WebSocket connection
            widget_id: The widget ID
            value: The response value
            item_id: The item ID (optional, derived from context if not provided)
            confirmation_required: Whether confirmation is required
            metadata: Optional response metadata
        """
        context = self._contexts.get(connection.connection_id)
        if not context:
            await self._send_error(connection, "NO_CONTEXT", "No conversation context found")
            return

        # Derive item_id from context if not provided
        actual_item_id = item_id or (context.current_item_state.item_id if context.current_item_state else None)
        if not actual_item_id:
            await self._send_error(connection, "NO_ITEM", "No current item for widget response")
            return

        await self._widget_handler.handle_widget_response(
            connection=connection,
            context=context,
            widget_id=widget_id,
            item_id=actual_item_id,
            value=value,
            advance_callback=self._advance_to_next_item,
        )

    async def handle_flow_start(self, connection: "Connection") -> None:
        """Handle flow start request from client.

        Args:
            connection: The WebSocket connection
        """
        context = self._contexts.get(connection.connection_id)
        if not context:
            return

        await self._flow_handler.handle_flow_start(
            connection=connection,
            context=context,
            proactive_runner=self._flow_runner.run_proactive_flow,
            chat_input_sender=self._send_chat_input_enabled,
        )

    async def handle_flow_pause(self, connection: "Connection", reason: str | None = None) -> None:
        """Handle flow pause request from client.

        Args:
            connection: The WebSocket connection
            reason: Optional pause reason
        """
        context = self._contexts.get(connection.connection_id)
        if not context:
            return

        await self._flow_handler.handle_flow_pause(connection, context, reason)

    async def handle_flow_cancel(self, connection: "Connection", request_id: str | None = None) -> None:
        """Handle flow cancel request from client.

        Args:
            connection: The WebSocket connection
            request_id: Optional request ID being cancelled
        """
        context = self._contexts.get(connection.connection_id)
        if not context:
            return

        await self._flow_handler.handle_flow_cancel(connection, context, request_id)

    async def handle_model_change(self, connection: "Connection", model_id: str) -> None:
        """Handle model change request from client.

        Args:
            connection: The WebSocket connection
            model_id: The new model ID
        """
        context = self._contexts.get(connection.connection_id)
        if not context:
            return

        self._model_handler.handle_model_change(context, model_id)

    # =========================================================================
    # Query Methods (for ConnectionManager)
    # =========================================================================

    async def get_definition_info_from_conversation(
        self,
        conversation_id: str,
        user_id: str,
    ) -> tuple[str | None, str | None, bool]:
        """Get definition info for a conversation.

        Args:
            conversation_id: The conversation ID
            user_id: The user ID

        Returns:
            Tuple of (definition_id, model, allows_selection)
        """
        from application.queries import GetConversationQuery

        result = await self._mediator.execute_async(GetConversationQuery(conversation_id=conversation_id, user_info={"sub": user_id}))

        if not result.is_success or not result.data:
            return None, None, True

        conv_dto = result.data
        if not conv_dto.definition_id:
            return None, None, True

        # Get definition details
        from application.queries import GetDefinitionQuery

        def_result = await self._mediator.execute_async(GetDefinitionQuery(definition_id=conv_dto.definition_id, user_info={"sub": user_id}))

        if not def_result.is_success or not def_result.data:
            return conv_dto.definition_id, None, True

        def_dto = def_result.data
        return def_dto.id, def_dto.model, def_dto.allow_model_selection

    async def get_definition_allow_model_selection(self, definition_id: str, user_id: str) -> bool:
        """Check if a definition allows model selection.

        Args:
            definition_id: The definition ID
            user_id: The user ID

        Returns:
            True if model selection is allowed
        """
        from application.queries import GetDefinitionQuery

        result = await self._mediator.execute_async(GetDefinitionQuery(definition_id=definition_id, user_info={"sub": user_id}))

        if not result.is_success or not result.data:
            return True

        return result.data.allow_model_selection

    async def get_tool_count(self, connection_id: str) -> int:
        """Get the number of tools loaded for a connection.

        Args:
            connection_id: The connection ID

        Returns:
            Number of tools loaded
        """
        context = self._contexts.get(connection_id)
        return len(context.tools) if context else 0

    # =========================================================================
    # Private Helper Methods
    # =========================================================================

    async def _run_agent_stream(
        self,
        connection: "Connection",
        context: ConversationContext,
        user_message: str,
    ) -> str | None:
        """Run agent and stream response to client.

        Args:
            connection: The WebSocket connection
            context: The conversation context
            user_message: The user's message

        Returns:
            The accumulated response content, or None on error
        """
        return await self._agent_runner.run_stream(connection, context, user_message)

    async def _advance_to_next_item(
        self,
        connection: "Connection",
        context: ConversationContext,
    ) -> None:
        """Advance to the next template item.

        Args:
            connection: The WebSocket connection
            context: The conversation context
        """
        await self._flow_runner.advance_to_next_item(connection, context)

    async def _send_chat_input_enabled(self, connection: "Connection", enabled: bool) -> None:
        """Send chat input enabled/disabled message.

        Args:
            connection: The WebSocket connection
            enabled: Whether chat input should be enabled
        """
        message = create_message(
            message_type="control.chatInput.enabled",
            payload={"enabled": enabled},
            conversation_id=connection.conversation_id,
        )
        await self._connection_manager.send_to_connection(connection.connection_id, message)

    async def _send_error(self, connection: "Connection", code: str, message: str) -> None:
        """Send error message to client.

        Args:
            connection: The WebSocket connection
            code: Error code
            message: Error message
        """
        error_message = create_message(
            message_type="system.error",
            payload={
                "category": "server",
                "code": code,
                "message": message,
                "isRetryable": True,
            },
            conversation_id=connection.conversation_id,
        )
        await self._connection_manager.send_to_connection(connection.connection_id, error_message)

    async def _send_item_context(
        self,
        connection: "Connection",
        context: ConversationContext,
        item_index: int,
        item: Any = None,
    ) -> None:
        """Send item context to client via ConfigSender.

        Args:
            connection: The WebSocket connection
            context: The conversation context
            item_index: The 0-based item index
            item: Optional item DTO for additional metadata
        """
        await self._config_sender.send_item_context(connection, context, item_index, item)

    async def _stream_response(
        self,
        connection: "Connection",
        context: ConversationContext,
        content: str,
    ) -> None:
        """Stream content to client in chunks.

        Args:
            connection: The WebSocket connection
            context: The conversation context
            content: The content to stream
        """
        message_id = f"msg_{uuid.uuid4().hex[:12]}"
        chunk_size = 50

        for i in range(0, len(content), chunk_size):
            chunk = content[i : i + chunk_size]
            is_final = (i + chunk_size) >= len(content)

            chunk_message = create_message(
                message_type="data.content.chunk",
                payload=ContentChunkPayload(
                    content=chunk,
                    messageId=message_id,
                    final=is_final,
                ).model_dump(by_alias=True, exclude_none=True),
                conversation_id=context.conversation_id,
            )
            await self._connection_manager.send_to_connection(connection.connection_id, chunk_message)
            await asyncio.sleep(0.02)

        complete_message = create_message(
            message_type="data.content.complete",
            payload=ContentCompletePayload(
                messageId=message_id,
                role="assistant",
                fullContent=content,
            ).model_dump(by_alias=True, exclude_none=True),
            conversation_id=context.conversation_id,
        )
        await self._connection_manager.send_to_connection(connection.connection_id, complete_message)

    async def _load_definition_context(
        self,
        context: ConversationContext,
        definition_id: str,
        user_info: dict[str, Any],
    ) -> None:
        """Load definition and template information into context.

        Args:
            context: The conversation context to update
            definition_id: The definition ID
            user_info: User info dict for authorization
        """
        from application.queries import GetDefinitionQuery, GetTemplateQuery

        result = await self._mediator.execute_async(GetDefinitionQuery(definition_id=definition_id, user_info=user_info))

        if not result.is_success or not result.data:
            log.warning(f"Failed to load definition {definition_id}")
            context.is_proactive = False
            context.has_template = False
            return

        def_dto = result.data
        context.model = def_dto.model
        context.definition_id = def_dto.id
        context.definition_name = def_dto.name
        context.allow_model_selection = def_dto.allow_model_selection
        context.has_template = def_dto.has_template

        # If definition has a template, load it to determine proactive flow
        if def_dto.conversation_template_id:
            context.template_id = def_dto.conversation_template_id

            template_result = await self._mediator.execute_async(
                GetTemplateQuery(
                    template_id=def_dto.conversation_template_id,
                    user_info=user_info,
                    for_client=False,  # Full template for server-side processing
                )
            )

            if template_result.is_success and template_result.data:
                template = template_result.data
                context.is_proactive = template.agent_starts_first
                context.total_items = template.item_count
                context.template_config = {
                    "allow_navigation": template.allow_navigation,
                    "allow_backward_navigation": template.allow_backward_navigation,
                    "enable_chat_input_initially": template.enable_chat_input_initially,
                    "display_progress_indicator": template.display_progress_indicator,
                    "display_final_score_report": template.display_final_score_report,
                    "continue_after_completion": template.continue_after_completion,
                    "introduction_message": template.introduction_message,
                    "completion_message": template.completion_message,
                }
                log.info(f"📋 Template loaded: {template.name}, proactive={context.is_proactive}, items={context.total_items}")
            else:
                log.warning(f"⚠️ Template not found: {def_dto.conversation_template_id}")
                context.is_proactive = False
        else:
            # No template - reactive conversation
            context.is_proactive = False

        log.debug(f"✅ Definition loaded: {definition_id}, name={context.definition_name}, model={context.model}, proactive={context.is_proactive}")

    async def _load_tools(self, context: ConversationContext) -> None:
        """Load available tools for the context.

        Args:
            context: The conversation context to update
        """
        if not self._tool_provider_client or not context.access_token:
            log.debug("No tool provider client or access token - skipping tool load")
            return

        try:
            from application.agents import LlmToolDefinition
            from domain.models.tool import Tool

            # Fetch tools from Tools Provider
            tool_data = await self._tool_provider_client.get_tools(
                access_token=context.access_token,
            )
            tools = [Tool.from_bff_response(t) for t in tool_data]

            # Apply tool filtering from agent config if configured
            agent_config = self._agent.config
            if agent_config.tool_whitelist:
                tools = [t for t in tools if t.name in agent_config.tool_whitelist]
            if agent_config.tool_blacklist:
                tools = [t for t in tools if t.name not in agent_config.tool_blacklist]

            # Convert to LLM tool definitions for agent use
            llm_tools = []
            for tool in tools:
                llm_tool = LlmToolDefinition(
                    name=tool.name,
                    description=tool.description,
                    parameters={
                        "type": "object",
                        "properties": {p.name: p.to_json_schema() for p in tool.parameters},
                        "required": [p.name for p in tool.parameters if p.required],
                    },
                )
                llm_tools.append(llm_tool)

            context.tools = llm_tools
            log.info(f"🔧 Loaded {len(llm_tools)} tools for conversation")
        except Exception as e:
            log.warning(f"Failed to load tools: {e}")
            context.tools = []
