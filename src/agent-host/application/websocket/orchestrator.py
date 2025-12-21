"""Conversation Orchestrator - Bridge between WebSocket and Agent/Domain layers.

DEPRECATED: This module is deprecated and will be removed in a future version.
Use application.orchestrator.Orchestrator instead, which provides a slim
coordinator that delegates to specialized handlers.

Migration:
    # Before
    from application.websocket.orchestrator import ConversationOrchestrator

    # After
    from application.orchestrator import Orchestrator

The new Orchestrator maintains the same public interface but uses a cleaner
architecture with extracted handlers for messages, widgets, flows, and models.

---

The orchestrator is responsible for:
1. Initializing agent context when a WebSocket connection is established
2. Processing conversation templates (proactive flow)
3. Routing client events to domain commands via Mediator (CQRS)
4. Translating domain events and agent events to WebSocket protocol messages

Architecture:
    WebSocket Handler → Orchestrator → Mediator → Domain Commands/Queries
                                    ↓
                              Agent Execution → AgentEvents
                                    ↓
                            Protocol Messages → WebSocket → Client

The orchestrator uses the Mediator pattern consistently with the rest of the codebase,
ensuring that all state changes go through proper domain commands and emit domain events.

Note: The core data classes (OrchestratorState, ItemExecutionState, ConversationContext)
have been extracted to application.orchestrator.context for better modularity.
"""

import asyncio
import logging
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from neuroglia.mediation import Mediator

from application.agents import Agent, AgentEventType, AgentRunContext, ToolExecutionRequest, ToolExecutionResult
from application.orchestrator.context import (
    ConversationContext,
    ItemExecutionState,
    OrchestratorState,
)
from application.protocol.control import (
    ConversationConfigPayload,
    ItemContextPayload,
)
from application.protocol.core import create_message
from application.protocol.data import ContentChunkPayload, ContentCompletePayload, ToolCallPayload, ToolResultPayload
from application.websocket.connection import Connection
from infrastructure.llm_provider_factory import LlmProviderFactory

if TYPE_CHECKING:
    from application.services.tool_provider_client import ToolProviderClient
    from application.websocket.manager import ConnectionManager

log = logging.getLogger(__name__)


# Re-export for backwards compatibility (deprecated - import from application.orchestrator instead)
__all__ = [
    "ConversationOrchestrator",
    "ConversationContext",
    "ItemExecutionState",
    "OrchestratorState",
]


class ConversationOrchestrator:
    """Orchestrates conversation flow between WebSocket and Agent/Domain layers.

    DEPRECATED: This class is deprecated. Use application.orchestrator.Orchestrator instead.

    This is the central coordinator that:
    - Loads conversation context on WebSocket connect
    - Determines flow type (reactive vs proactive)
    - Dispatches domain commands via Mediator
    - Translates agent events to protocol messages
    - Manages conversation state machine

    Usage:
        # DEPRECATED - use the new Orchestrator instead:
        # from application.orchestrator import Orchestrator

        orchestrator = ConversationOrchestrator(mediator, connection_manager)

        # On WebSocket connect
        await orchestrator.initialize(connection, conversation_id)

        # On user message
        await orchestrator.handle_user_message(connection, content)

        # On widget response
        await orchestrator.handle_widget_response(connection, widget_id, value)
    """

    def __init__(
        self,
        mediator: Mediator,
        connection_manager: "ConnectionManager",
        agent: Agent,
        llm_provider_factory: LlmProviderFactory,
        tool_provider_client: "ToolProviderClient | None" = None,
    ):
        """Initialize the orchestrator.

        DEPRECATED: Use application.orchestrator.Orchestrator instead.

        Args:
            mediator: Neuroglia Mediator for CQRS command/query dispatch
            connection_manager: WebSocket connection manager for sending messages
            agent: Agent abstraction for LLM execution
            llm_provider_factory: Factory for selecting LLM provider based on model
            tool_provider_client: Client for fetching tools from Tools Provider
        """
        import warnings

        warnings.warn(
            "ConversationOrchestrator is deprecated. Use application.orchestrator.Orchestrator instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self._mediator = mediator
        self._connection_manager = connection_manager
        self._agent = agent
        self._llm_provider_factory = llm_provider_factory
        self._tool_provider_client = tool_provider_client

        # Active conversation contexts by connection_id
        self._contexts: dict[str, ConversationContext] = {}

        log.info("ConversationOrchestrator initialized with Agent and LlmProviderFactory")

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def llm_provider_factory(self) -> LlmProviderFactory:
        """Get the LLM provider factory for model selection."""
        return self._llm_provider_factory

    # =========================================================================
    # Agent Execution
    # =========================================================================

    async def _build_agent_context(
        self,
        context: ConversationContext,
        user_message: str,
    ) -> AgentRunContext:
        """Build AgentRunContext from conversation history.

        Loads the conversation messages from the read model and constructs
        an AgentRunContext for agent execution.

        Args:
            context: The orchestrator's conversation context
            user_message: The current user message to process

        Returns:
            AgentRunContext ready for agent.run_stream()
        """
        from application.agents import LlmMessage
        from application.queries import GetConversationQuery

        # Load conversation to get message history
        user_info = {"sub": context.user_id}
        result = await self._mediator.execute_async(
            GetConversationQuery(
                conversation_id=context.conversation_id,
                user_info=user_info,
            )
        )

        history: list[LlmMessage] = []
        if result.is_success and result.data:
            conv_dto = result.data
            # Convert stored messages to LlmMessage format
            for msg in conv_dto.messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")

                if role == "user":
                    history.append(LlmMessage.user(content))
                elif role == "assistant":
                    history.append(LlmMessage.assistant(content))
                elif role == "system":
                    history.append(LlmMessage.system(content))
                # Skip tool messages for now - they're included in context implicitly

        return AgentRunContext(
            user_message=user_message,
            conversation_history=history,
            tools=context.tools,  # Tools loaded from ToolProviderClient
            tool_executor=self._create_tool_executor(context),
            access_token=context.access_token,
            metadata={
                "conversation_id": context.conversation_id,
                "definition_id": context.definition_id,
            },
        )

    def _create_tool_executor(
        self,
        context: ConversationContext,
    ):
        """Create a tool executor function for the agent.

        This returns an async generator that the agent uses to execute tools
        by calling the Tools Provider service.

        Args:
            context: The conversation context

        Returns:
            An async generator function for tool execution
        """
        from collections.abc import AsyncIterator

        async def execute_tool(request: ToolExecutionRequest) -> AsyncIterator[ToolExecutionResult]:
            """Execute a tool via the Tools Provider service.

            Args:
                request: The tool execution request

            Yields:
                ToolExecutionResult with the tool's output or error
            """
            import time

            start_time = time.time()

            log.info(f"🔧 Tool execution requested: {request.tool_name}({request.arguments})")

            # Check if we have the required client and access token
            if not self._tool_provider_client:
                log.error("ToolProviderClient not configured - cannot execute tools")
                yield ToolExecutionResult(
                    call_id=request.call_id,
                    tool_name=request.tool_name,
                    success=False,
                    result=None,
                    error="Tool execution not available - ToolProviderClient not configured",
                    execution_time_ms=(time.time() - start_time) * 1000,
                )
                return

            if not context.access_token:
                log.error("No access token available - cannot execute tools")
                yield ToolExecutionResult(
                    call_id=request.call_id,
                    tool_name=request.tool_name,
                    success=False,
                    result=None,
                    error="Tool execution not available - no access token",
                    execution_time_ms=(time.time() - start_time) * 1000,
                )
                return

            try:
                # Call the Tools Provider service
                result = await self._tool_provider_client.execute_tool(
                    tool_name=request.tool_name,
                    arguments=request.arguments,
                    access_token=context.access_token,
                )

                execution_time_ms = (time.time() - start_time) * 1000

                # Check if the result indicates an error
                if isinstance(result, dict) and result.get("success") is False:
                    log.warning(f"🔧 Tool execution failed: {request.tool_name} - {result.get('error')}")
                    yield ToolExecutionResult(
                        call_id=request.call_id,
                        tool_name=request.tool_name,
                        success=False,
                        result=None,
                        error=result.get("error", "Unknown error"),
                        execution_time_ms=execution_time_ms,
                    )
                else:
                    log.info(f"🔧 Tool executed successfully: {request.tool_name} in {execution_time_ms:.2f}ms")
                    yield ToolExecutionResult(
                        call_id=request.call_id,
                        tool_name=request.tool_name,
                        success=True,
                        result=result,
                        error=None,
                        execution_time_ms=execution_time_ms,
                    )

            except Exception as e:
                execution_time_ms = (time.time() - start_time) * 1000
                log.error(f"🔧 Tool execution error: {request.tool_name} - {e}")
                yield ToolExecutionResult(
                    call_id=request.call_id,
                    tool_name=request.tool_name,
                    success=False,
                    result=None,
                    error=str(e),
                    execution_time_ms=execution_time_ms,
                )

        return execute_tool

    async def _run_agent_stream(
        self,
        connection: Connection,
        context: ConversationContext,
        user_message: str,
    ) -> str | None:
        """Execute agent and stream events to client.

        This is the core method that:
        1. Builds agent context from conversation history
        2. Invokes agent.run_stream() async generator
        3. Translates AgentEvents to WebSocket protocol messages
        4. Accumulates final response content

        Args:
            connection: The WebSocket connection
            context: The conversation context
            user_message: The user's message content

        Returns:
            The complete assistant response content, or None on error
        """
        try:
            # Set model override from definition before running agent
            if context.model:
                log.info(f"🔧 Setting model override from definition: {context.model}")
                provider = self._llm_provider_factory.get_provider_for_model(context.model)
                # Switch agent to use the correct provider
                self._agent.llm = provider
            else:
                # Clear any previous override to use default model
                self._agent.llm.set_model_override(None)
                log.debug("📌 Using default LLM model (no definition override)")

            # Build context for agent
            agent_context = await self._build_agent_context(context, user_message)

            # Track message ID and accumulated content
            message_id = str(uuid.uuid4())
            accumulated_content = ""
            chunk_sequence = 0

            # Stream agent events
            async for event in self._agent.run_stream(agent_context):
                log.debug(f"AgentEvent: {event.type.value}")

                if event.type == AgentEventType.RUN_STARTED:
                    # Disable chat input during streaming
                    await self._send_chat_input_enabled(connection, False)

                elif event.type == AgentEventType.LLM_RESPONSE_CHUNK:
                    # Stream content chunk to client
                    chunk = event.data.get("content", "")
                    accumulated_content += chunk
                    chunk_sequence += 1

                    chunk_message = create_message(
                        message_type="data.content.chunk",
                        payload=ContentChunkPayload(
                            content=chunk,
                            messageId=message_id,
                            final=False,
                        ).model_dump(by_alias=True, exclude_none=True),
                        conversation_id=context.conversation_id,
                    )
                    await self._connection_manager.send_to_connection(connection.connection_id, chunk_message)

                elif event.type == AgentEventType.TOOL_EXECUTION_STARTED:
                    # Notify client of tool call
                    tool_data = event.data
                    tool_message = create_message(
                        message_type="data.tool.call",
                        payload=ToolCallPayload(
                            callId=tool_data.get("call_id", str(uuid.uuid4())),
                            toolName=tool_data.get("tool_name", "unknown"),
                            arguments=tool_data.get("arguments", {}),
                        ).model_dump(by_alias=True, exclude_none=True),
                        conversation_id=context.conversation_id,
                    )
                    await self._connection_manager.send_to_connection(connection.connection_id, tool_message)

                elif event.type == AgentEventType.TOOL_EXECUTION_COMPLETED:
                    # Notify client of tool result
                    tool_data = event.data
                    result_message = create_message(
                        message_type="data.tool.result",
                        payload=ToolResultPayload(
                            callId=tool_data.get("call_id", str(uuid.uuid4())),
                            toolName=tool_data.get("tool_name", "unknown"),
                            success=tool_data.get("success", True),
                            result=tool_data.get("result"),
                            executionTimeMs=int(tool_data.get("execution_time_ms", 0)),
                        ).model_dump(by_alias=True, exclude_none=True),
                        conversation_id=context.conversation_id,
                    )
                    await self._connection_manager.send_to_connection(connection.connection_id, result_message)

                elif event.type == AgentEventType.RUN_COMPLETED:
                    # Send final chunk marker and content complete message
                    final_chunk = create_message(
                        message_type="data.content.chunk",
                        payload=ContentChunkPayload(
                            content="",
                            messageId=message_id,
                            final=True,
                        ).model_dump(by_alias=True, exclude_none=True),
                        conversation_id=context.conversation_id,
                    )
                    await self._connection_manager.send_to_connection(connection.connection_id, final_chunk)

                    complete_message = create_message(
                        message_type="data.content.complete",
                        payload=ContentCompletePayload(
                            messageId=message_id,
                            role="assistant",
                            fullContent=accumulated_content,
                        ).model_dump(by_alias=True, exclude_none=True),
                        conversation_id=context.conversation_id,
                    )
                    await self._connection_manager.send_to_connection(connection.connection_id, complete_message)

                    # Re-enable chat input after streaming completes
                    await self._send_chat_input_enabled(connection, True)

                elif event.type == AgentEventType.RUN_FAILED:
                    # Send error and stop
                    error_msg = event.data.get("error", "Unknown agent error")
                    log.error(f"Agent run failed: {error_msg}")
                    await self._send_error(connection, "AGENT_ERROR", error_msg)
                    # Re-enable chat input on error
                    await self._send_chat_input_enabled(connection, True)
                    return None

            return accumulated_content

        except Exception as e:
            log.exception(f"Error running agent stream: {e}")
            await self._send_error(connection, "AGENT_ERROR", str(e))
            # Re-enable chat input on exception
            await self._send_chat_input_enabled(connection, True)
            return None

    # =========================================================================
    # Lifecycle Management
    # =========================================================================

    async def initialize(
        self,
        connection: Connection,
        conversation_id: str,
    ) -> ConversationContext:
        """Initialize orchestration for a conversation.

        Called when a WebSocket connection is established with a conversation_id.
        Loads the conversation, definition, and template from the read model,
        then determines the appropriate flow.

        Args:
            connection: The WebSocket connection
            conversation_id: The conversation to orchestrate

        Returns:
            The initialized conversation context

        Raises:
            ValueError: If conversation not found or access denied
        """
        log.info(f"🎭 Initializing orchestrator for conversation {conversation_id}")

        # Load conversation from read model via query to get definition_id
        from application.queries import GetConversationQuery

        user_info = {"sub": connection.user_id}
        result = await self._mediator.execute_async(GetConversationQuery(conversation_id=conversation_id, user_info=user_info))

        if not result.is_success or not result.data:
            log.error(f"Conversation not found: {conversation_id}")
            raise ValueError(f"Conversation not found: {conversation_id}")

        conversation = result.data
        definition_id = conversation.definition_id or connection.definition_id

        log.info(f"🎭 Loaded conversation: id={conversation_id}, definition_id={definition_id}")

        # Create initial context
        context = ConversationContext(
            connection_id=connection.connection_id,
            conversation_id=conversation_id,
            user_id=connection.user_id,
            definition_id=definition_id,
        )

        # Load definition if present
        if definition_id:
            await self._load_definition_context(context, definition_id)

        # Load tools from Tools Provider if access token is available
        if connection.access_token and self._tool_provider_client:
            tool_count = await self.load_tools_for_context(context, connection.access_token)
            log.info(f"🔧 Loaded {tool_count} tools for conversation {conversation_id}")
        else:
            if not connection.access_token:
                log.warning("No access token available - tools will not be loaded")
            if not self._tool_provider_client:
                log.warning("ToolProviderClient not configured - tools will not be loaded")

        # Store context
        self._contexts[connection.connection_id] = context

        # Send conversation config to client
        await self._send_conversation_config(connection, context)

        # Set initial state but DON'T start proactive flow yet
        # Proactive flow will be triggered by start_proactive_flow_if_needed()
        # which must be called AFTER the WebSocket handshake is complete
        if context.is_proactive and context.has_template:
            context.state = OrchestratorState.PRESENTING
            # Don't start proactive flow here - wait for handshake to complete
            log.info("🎭 Proactive conversation detected, will start after handshake")
        else:
            context.state = OrchestratorState.READY
            # Don't enable chat input here either - wait for handshake
            log.info("🎭 Reactive conversation, will enable chat input after handshake")

        log.info(f"🎭 Orchestrator initialized: state={context.state.value}, proactive={context.is_proactive}")
        return context

    async def cleanup(self, connection_id: str) -> None:
        """Cleanup orchestrator state when connection closes.

        Args:
            connection_id: The connection to cleanup
        """
        context = self._contexts.pop(connection_id, None)
        if context:
            log.info(f"🎭 Orchestrator cleanup: conversation={context.conversation_id}")

    async def start_conversation_flow(self, connection: Connection) -> None:
        """Start the conversation flow after WebSocket handshake is complete.

        This method MUST be called after system.connection.established is sent.
        It initiates either the proactive (template-driven) or reactive (chat) flow.

        For proactive conversations:
        - Loads the first template item
        - Renders item contents (messages, widgets)
        - Respects enable_chat_input settings

        For reactive conversations:
        - Simply enables the chat input

        Args:
            connection: The WebSocket connection
        """
        context = self._contexts.get(connection.connection_id)
        if not context:
            log.error(f"No context for connection {connection.connection_id}")
            return

        log.info(f"🎭 Starting conversation flow: conversation={context.conversation_id}, proactive={context.is_proactive}")

        if context.is_proactive and context.has_template:
            # Start proactive flow (template-driven)
            await self._run_proactive_flow(connection, context)
        else:
            # Reactive flow - just enable chat input
            await self._send_chat_input_enabled(connection, True)
            context.state = OrchestratorState.READY

    def get_context(self, connection_id: str) -> ConversationContext | None:
        """Get the conversation context for a connection.

        Args:
            connection_id: The connection ID

        Returns:
            The context or None if not found
        """
        return self._contexts.get(connection_id)

    async def load_tools_for_context(self, context: ConversationContext, access_token: str) -> int:
        """Load tools from ToolProviderClient into the conversation context.

        Args:
            context: The conversation context to load tools into
            access_token: User's access token for authentication

        Returns:
            Number of tools loaded
        """
        if not self._tool_provider_client:
            log.warning("ToolProviderClient not configured - no tools available")
            return 0

        try:
            from domain.models.tool import Tool

            # Fetch tools from Tools Provider
            tool_data = await self._tool_provider_client.get_tools(access_token)
            tools = [Tool.from_bff_response(t) for t in tool_data]

            # Apply tool filtering from agent config if configured
            agent_config = self._agent.config
            if agent_config.tool_whitelist:
                tools = [t for t in tools if t.name in agent_config.tool_whitelist]
            if agent_config.tool_blacklist:
                tools = [t for t in tools if t.name not in agent_config.tool_blacklist]

            # Convert to LLM tool definitions for agent use
            from application.agents import LlmToolDefinition

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

            # Store in context
            context.tools = llm_tools
            context.access_token = access_token

            log.info(f"🔧 Loaded {len(llm_tools)} tools for conversation {context.conversation_id[:8]}...")
            return len(llm_tools)

        except Exception as e:
            log.error(f"Failed to load tools: {e}")
            return 0

    async def get_tool_count(self, connection_id: str) -> int:
        """Get the number of tools available for a connection.

        Args:
            connection_id: The connection ID

        Returns:
            Number of tools, or 0 if context not found
        """
        context = self._contexts.get(connection_id)
        if context:
            return len(context.tools)
        return 0

    async def get_definition_allow_model_selection(self, definition_id: str | None, user_id: str) -> bool:
        """Check if a definition allows model selection.

        Args:
            definition_id: The definition ID to check
            user_id: The user ID for access check

        Returns:
            True if model selection is allowed, False otherwise
        """
        if not definition_id:
            return True  # Default to allowing model selection

        from application.queries.definition.get_definitions_query import GetDefinitionQuery

        user_info = {"sub": user_id}
        result = await self._mediator.execute_async(GetDefinitionQuery(definition_id=definition_id, user_info=user_info))

        if not result.is_success or result.data is None:
            return True  # Default to allowing if definition not found

        return result.data.allow_model_selection

    async def get_definition_info_from_conversation(
        self,
        conversation_id: str,
        user_id: str,
    ) -> tuple[str | None, str | None, bool]:
        """Get definition info from a conversation.

        Looks up the conversation and returns its associated definition details.

        Args:
            conversation_id: The conversation ID to look up
            user_id: The user ID for access check

        Returns:
            Tuple of (definition_id, model, allow_model_selection)
        """
        from application.queries import GetConversationQuery
        from application.queries.definition.get_definitions_query import GetDefinitionQuery

        user_info = {"sub": user_id}

        # First get the conversation to find definition_id
        result = await self._mediator.execute_async(GetConversationQuery(conversation_id=conversation_id, user_info=user_info))
        if not result.is_success or not result.data:
            return None, None, True

        definition_id = result.data.definition_id
        if not definition_id:
            return None, None, True

        # Now get the definition details
        def_result = await self._mediator.execute_async(GetDefinitionQuery(definition_id=definition_id, user_info=user_info))
        if not def_result.is_success or not def_result.data:
            return definition_id, None, True

        definition = def_result.data
        return definition_id, definition.model, definition.allow_model_selection

    # =========================================================================
    # Client Event Handlers (called from WebSocket handlers)
    # =========================================================================

    async def handle_user_message(
        self,
        connection: Connection,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Handle a user message from the client.

        Dispatches a domain command to process the message, then streams
        agent response back to the client.

        Args:
            connection: The WebSocket connection
            content: The message content
            metadata: Optional message metadata
        """
        context = self._contexts.get(connection.connection_id)
        if not context:
            log.error(f"No context for connection {connection.connection_id}")
            await self._send_error(connection, "NO_CONTEXT", "Conversation not initialized")
            return

        if context.state not in (OrchestratorState.READY, OrchestratorState.SUSPENDED):
            log.warning(f"Cannot process message in state {context.state}")
            await self._send_error(connection, "INVALID_STATE", f"Cannot send message in state: {context.state}")
            return

        context.state = OrchestratorState.PROCESSING
        context.last_activity = datetime.now(UTC)

        try:
            # Send acknowledgment
            ack_message = create_message(
                message_type="data.message.ack",
                payload={"status": "received"},
                conversation_id=context.conversation_id,
            )
            await self._connection_manager.send_to_connection(connection.connection_id, ack_message)

            # Persist user message via domain command
            from application.commands import SendMessageCommand

            send_result = await self._mediator.execute_async(
                SendMessageCommand(
                    conversation_id=context.conversation_id,
                    content=content,
                    user_info={"sub": context.user_id},
                )
            )

            assistant_message_id: str | None = None
            if not send_result.is_success:
                log.warning(f"Failed to persist user message: {send_result.errors}")
                # Continue anyway - agent can still respond
            elif send_result.data:
                # Capture the assistant message ID for completion later
                assistant_message_id = send_result.data.assistant_message_id

            # Run agent and stream response
            response_content = await self._run_agent_stream(connection, context, content)

            # Persist assistant message if we got a response and have message ID
            if response_content and assistant_message_id:
                from application.commands.conversation.complete_message_command import CompleteMessageCommand

                # Complete the pending assistant message with the final content
                complete_result = await self._mediator.execute_async(
                    CompleteMessageCommand(
                        conversation_id=context.conversation_id,
                        message_id=assistant_message_id,
                        content=response_content,
                        user_info={"sub": context.user_id},
                    )
                )

                if not complete_result.is_success:
                    log.warning(f"Failed to complete assistant message: {complete_result.errors}")

            context.state = OrchestratorState.READY

        except Exception as e:
            log.exception(f"Error processing message: {e}")
            context.state = OrchestratorState.ERROR
            await self._send_error(connection, "PROCESSING_ERROR", str(e))

    async def handle_widget_response(
        self,
        connection: Connection,
        widget_id: str,
        item_id: str,
        value: Any,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Handle a widget response from the client.

        For proactive conversations:
        1. Records the response in the current item state
        2. Tracks which required widgets have been answered
        3. Advances to next item when all required widgets are answered

        Args:
            connection: The WebSocket connection
            widget_id: The widget that was responded to
            item_id: The item containing the widget
            value: The response value
            metadata: Optional response metadata
        """
        context = self._contexts.get(connection.connection_id)
        if not context:
            log.error(f"No context for connection {connection.connection_id}")
            return

        log.info(f"📝 Widget response: widget={widget_id}, item={item_id}, value={value}")

        context.last_activity = datetime.now(UTC)

        # Send acknowledgment
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

        # Track response in item state
        if context.current_item_state and context.current_item_state.item_id == item_id:
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

            # Check if all required widgets are answered (and confirmed if needed)
            if item_state.is_complete:
                log.info(f"📋 Item {item_id} complete, all requirements met")
                item_state.completed_at = datetime.now(UTC)

                # Dispatch domain commands to persist responses
                await self._persist_item_response(connection, context, item_state)

                # Advance to next item
                if context.is_proactive and context.has_template:
                    await self._advance_to_next_item(connection, context)
                else:
                    context.state = OrchestratorState.READY
            else:
                # Still waiting for more responses (or confirmation)
                pending = item_state.pending_widget_ids
                needs_confirm = item_state.require_user_confirmation and not item_state.user_confirmed
                log.debug(f"📋 Item {item_id} still waiting: widgets={pending}, needs_confirm={needs_confirm}")
        else:
            # Response for a different item (shouldn't happen normally)
            log.warning(f"Widget response for unexpected item: expected={context.current_item_state.item_id if context.current_item_state else 'None'}, got={item_id}")

            # For reactive mode, just go back to ready
            if not context.is_proactive:
                context.state = OrchestratorState.READY

    async def _persist_item_response(
        self,
        connection: Connection,
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

            # Build widget responses
            widget_responses = [
                WidgetResponse(
                    widget_id=widget_id,
                    value=value,
                    content_id=widget_id,  # Use widget_id as content_id for now
                    # TODO: Add scoring logic here when we have correct_answer access
                    is_correct=None,
                    score=None,
                    max_score=None,
                )
                for widget_id, value in item_state.widget_responses.items()
            ]

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

    async def handle_flow_start(self, connection: Connection) -> None:
        """Handle explicit flow start request from client.

        For proactive conversations, this triggers the template flow.
        For reactive, this is a no-op (flow starts with first message).

        Args:
            connection: The WebSocket connection
        """
        context = self._contexts.get(connection.connection_id)
        if not context:
            log.error(f"No context for connection {connection.connection_id}")
            return

        log.info(f"▶️ Flow start requested: conversation={context.conversation_id}")

        if context.is_proactive and context.has_template:
            if context.state == OrchestratorState.READY:
                context.state = OrchestratorState.PRESENTING
                asyncio.create_task(self._run_proactive_flow(connection, context))
        else:
            # Reactive mode - just ensure chat input is enabled
            await self._send_chat_input_enabled(connection, True)

    async def handle_flow_pause(self, connection: Connection, reason: str | None = None) -> None:
        """Handle flow pause request from client.

        Args:
            connection: The WebSocket connection
            reason: Optional pause reason
        """
        context = self._contexts.get(connection.connection_id)
        if not context:
            return

        log.info(f"⏸️ Flow paused: conversation={context.conversation_id}, reason={reason}")
        context.state = OrchestratorState.PAUSED

        # TODO: Dispatch PauseConversationCommand
        # Acknowledge pause
        pause_ack = create_message(
            message_type="control.conversation.pause",
            payload={
                "reason": reason or "user_requested",
                "pausedAt": datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            },
            conversation_id=context.conversation_id,
        )
        await self._connection_manager.send_to_connection(connection.connection_id, pause_ack)

    async def handle_flow_cancel(self, connection: Connection, request_id: str | None = None) -> None:
        """Handle flow/request cancellation from client.

        Args:
            connection: The WebSocket connection
            request_id: Optional specific request to cancel
        """
        context = self._contexts.get(connection.connection_id)
        if not context:
            return

        log.info(f"🚫 Flow cancelled: conversation={context.conversation_id}")

        # TODO: Dispatch CancelOperationCommand if request_id provided
        # Otherwise, cancel current operation

        # Reset to ready state
        context.state = OrchestratorState.READY
        context.pending_widget_id = None
        context.pending_tool_call_id = None

    async def handle_model_change(self, connection: Connection, model_id: str) -> None:
        """Handle model change request from client.

        Updates the conversation context's model so subsequent agent runs use
        the newly selected model.

        Args:
            connection: The WebSocket connection
            model_id: Qualified model ID (e.g., "openai:gpt-4o", "ollama:llama3.2:3b")

        Raises:
            ValueError: If the model is not available
        """
        context = self._contexts.get(connection.connection_id)
        if not context:
            raise ValueError("No active conversation context")

        # Validate the model is available via the factory
        try:
            # This will raise if the provider/model is not available
            self._llm_provider_factory.get_provider_for_model(model_id)
        except Exception as e:
            log.error(f"Model {model_id} is not available: {e}")
            raise ValueError(f"Model '{model_id}' is not available") from e

        # Update the context
        old_model = context.model
        context.model = model_id
        log.info(f"🔄 Model changed for conversation {context.conversation_id[:8]}...: {old_model} → {model_id}")

    # =========================================================================
    # Internal: Load Context
    # =========================================================================

    async def _load_definition_context(self, context: ConversationContext, definition_id: str) -> None:
        """Load definition details into context.

        Fetches the AgentDefinition from the read model, and if it has an associated
        ConversationTemplate, loads that as well to determine proactive/reactive flow.

        Args:
            context: The conversation context to populate
            definition_id: The definition ID to load
        """
        from application.queries.definition.get_definitions_query import GetDefinitionQuery
        from application.queries.template.get_templates_query import GetTemplateQuery

        # Set definition_id immediately
        context.definition_id = definition_id

        # Build a minimal user_info for the query (orchestrator uses connection.user_id)
        user_info = {"sub": context.user_id}

        # Load definition via query
        result = await self._mediator.execute_async(GetDefinitionQuery(definition_id=definition_id, user_info=user_info))

        if not result.is_success or result.data is None:
            log.warning(f"⚠️ Definition not found or access denied: {definition_id}")
            # Fallback to reactive mode
            context.is_proactive = False
            context.has_template = False
            return

        definition = result.data
        context.definition_name = definition.name
        context.model = definition.model  # LLM model override from definition (e.g., "openai:gpt-4o")
        context.allow_model_selection = definition.allow_model_selection  # Whether users can change model
        context.has_template = definition.has_template

        # If definition has a template, load it to determine proactive flow
        if definition.conversation_template_id:
            context.template_id = definition.conversation_template_id

            template_result = await self._mediator.execute_async(
                GetTemplateQuery(
                    template_id=definition.conversation_template_id,
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
                log.warning(f"⚠️ Template not found: {definition.conversation_template_id}")
                context.is_proactive = False
        else:
            # No template - reactive conversation
            context.is_proactive = False

        log.debug(f"✅ Definition loaded: {definition_id}, name={context.definition_name}, model={context.model}, proactive={context.is_proactive}")

    # =========================================================================
    # Internal: Protocol Message Sending
    # =========================================================================

    async def _send_conversation_config(self, connection: Connection, context: ConversationContext) -> None:
        """Send conversation configuration to client.

        Uses template config if available, otherwise applies sensible defaults.

        Args:
            connection: The WebSocket connection
            context: The conversation context
        """
        tc = context.template_config  # Shorthand for template config dict

        config_payload = ConversationConfigPayload(
            templateId=context.template_id or "default",
            templateName=context.definition_name or "Conversation",
            totalItems=context.total_items or 1,
            displayMode="append",  # DisplayMode literal
            showConversationHistory=True,
            allowBackwardNavigation=tc.get("allow_backward_navigation", not context.is_proactive),
            allowConcurrentItemWidgets=False,
            allowSkip=tc.get("allow_navigation", not context.is_proactive),
            enableChatInputInitially=tc.get("enable_chat_input_initially", not context.is_proactive),
            displayProgressIndicator=tc.get("display_progress_indicator", context.is_proactive),
            displayFinalScoreReport=tc.get("display_final_score_report", False),
            continueAfterCompletion=tc.get("continue_after_completion", True),
        )

        config_message = create_message(
            message_type="control.conversation.config",
            payload=config_payload.model_dump(by_alias=True, exclude_none=True),
            conversation_id=context.conversation_id,
        )

        await self._connection_manager.send_to_connection(connection.connection_id, config_message)

    async def _send_chat_input_enabled(self, connection: Connection, enabled: bool) -> None:
        """Send chat input state to client.

        Args:
            connection: The WebSocket connection
            enabled: Whether chat input should be enabled
        """
        context = self._contexts.get(connection.connection_id)
        if not context:
            return

        message = create_message(
            message_type="control.flow.chatInput",
            payload={"enabled": enabled},
            conversation_id=context.conversation_id,
        )
        await self._connection_manager.send_to_connection(connection.connection_id, message)

    async def _send_error(self, connection: Connection, code: str, message: str) -> None:
        """Send error message to client.

        Args:
            connection: The WebSocket connection
            code: Error code
            message: Error message
        """
        context = self._contexts.get(connection.connection_id)
        error_message = create_message(
            message_type="system.error",
            payload={
                "category": "business",
                "code": code,
                "message": message,
                "isRetryable": True,
            },
            conversation_id=context.conversation_id if context else None,
        )
        await self._connection_manager.send_to_connection(connection.connection_id, error_message)

    async def _stream_agent_response(
        self,
        connection: Connection,
        context: ConversationContext,
        content: str,
    ) -> None:
        """Stream content to client in chunks.

        Args:
            connection: The WebSocket connection
            context: The conversation context
            content: The content to stream
        """
        # Generate a message ID for this content
        message_id = f"msg_{uuid.uuid4().hex[:12]}"

        # For demonstration, stream in chunks
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

            # Small delay to simulate streaming
            await asyncio.sleep(0.02)

        # Send completion message
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

    # =========================================================================
    # Internal: Proactive Flow
    # =========================================================================

    async def _run_proactive_flow(self, connection: Connection, context: ConversationContext) -> None:
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
            await self._send_chat_input_enabled(connection, enable_chat_initially)

            # Send introduction message if configured
            intro_message = context.template_config.get("introduction_message")
            if intro_message:
                await self._stream_agent_response(connection, context, intro_message)

            # Present the first item
            await self._present_item(connection, context, 0)

        except Exception as e:
            log.exception(f"Error in proactive flow: {e}")
            context.state = OrchestratorState.ERROR
            await self._send_error(connection, "FLOW_ERROR", str(e))

    async def _present_item(
        self,
        connection: Connection,
        context: ConversationContext,
        item_index: int,
    ) -> None:
        """Present a template item to the client.

        Loads the item from the template and renders each ItemContent:
        - Message widgets: Stream as agent response
        - Interactive widgets: Send control.widget.render

        Args:
            connection: The WebSocket connection
            context: The conversation context
            item_index: The 0-based index of the item to present
        """
        from application.queries import GetTemplateItemQuery

        if not context.template_id:
            log.error("No template_id in context for proactive flow")
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
                await self._complete_proactive_flow(connection, context)
                return
            else:
                log.error(f"Failed to load item {item_index}: {result.errors}")
                await self._send_error(connection, "ITEM_LOAD_FAILED", f"Failed to load item {item_index}")
                return

        item = result.data
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
        await self._send_item_context(connection, context, item_index, item)

        # Process each content in order
        sorted_contents = sorted(item.contents, key=lambda c: c.order)
        for content in sorted_contents:
            await self._render_item_content(connection, context, item, content)

        # If user confirmation is required, send a confirmation button widget
        if item.require_user_confirmation:
            await self._send_confirmation_widget(connection, context, item)

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
            await self._send_chat_input_enabled(connection, item.enable_chat_input)

    async def _render_item_content(
        self,
        connection: Connection,
        context: ConversationContext,
        item,  # ConversationItemDto
        content,  # ItemContentDto
    ) -> None:
        """Render a single ItemContent to the client.

        Args:
            connection: The WebSocket connection
            context: The conversation context
            item: The parent ConversationItemDto
            content: The ItemContentDto to render
        """

        log.debug(f"📦 Rendering content {content.id}: type={content.widget_type}, templated={content.is_templated}")

        # Get the stem content (static or generate from template)
        stem = await self._get_content_stem(context, content, item)

        if content.widget_type == "message":
            # Message type: stream as agent response
            if stem:
                await self._stream_agent_response(connection, context, stem)
        else:
            # Interactive widget: send widget.render message
            await self._send_widget_render(connection, context, item, content, stem)

    async def _get_content_stem(
        self,
        context: ConversationContext,
        content,  # ItemContentDto
        item=None,  # ConversationItemDto (optional, for instructions)
    ) -> str | None:
        """Get the stem content for an ItemContent.

        If content is templated, generates via LLM using item.instructions.
        Otherwise returns static stem with Jinja-style variable substitution.

        Args:
            context: The conversation context
            content: The ItemContentDto
            item: The parent ConversationItemDto (for instructions)

        Returns:
            The stem text, or None if unavailable
        """
        if not content.is_templated:
            # Static content - apply Jinja-style variable substitution if present
            if content.stem:
                return self._render_jinja_template(content.stem, context)
            return content.stem

        # Templated content: generate via LLM using item.instructions
        generated_stem = await self._generate_templated_content(context, content, item)
        if generated_stem:
            return generated_stem

        # Fallback to static stem if generation failed
        if content.stem:
            log.warning(f"Templated content {content.id} falling back to static stem after generation failure")
            return self._render_jinja_template(content.stem, context)

        log.warning(f"Templated content {content.id} has no stem and generation failed")
        return None

    def _render_jinja_template(self, template: str, context: ConversationContext) -> str:
        """Render a Jinja-style template string with context variables.

        Supports {{ variable }} syntax for variable substitution.

        Available variables:
        - user_id: The user's ID
        - user_name: The user's display name
        - conversation_id: The conversation ID
        - agent_name: The agent's display name
        - current_item: Current item index (1-based)
        - total_items: Total number of items
        - timestamp: Current timestamp

        Args:
            template: The template string with {{ variable }} placeholders
            context: The conversation context

        Returns:
            The rendered string with variables substituted
        """
        from jinja2 import BaseLoader, Environment, UndefinedError

        try:
            # Create a Jinja2 environment with safe defaults
            env = Environment(loader=BaseLoader(), autoescape=True)

            # Build template context from available ConversationContext fields
            template_vars = {
                "user_id": context.user_id or "",
                "user_name": context.user_id or "User",  # Use user_id as fallback name
                "conversation_id": context.conversation_id or "",
                "agent_name": context.definition_name or "Agent",  # Use definition_name
                "current_item": (context.current_item_index or 0) + 1,  # 1-based for display
                "total_items": context.total_items or 0,
                "timestamp": datetime.now(UTC).isoformat(),
            }

            # Render the template
            jinja_template = env.from_string(template)
            return jinja_template.render(**template_vars)

        except UndefinedError as e:
            log.warning(f"Undefined variable in template: {e}")
            return template  # Return original if variable missing
        except Exception as e:
            log.error(f"Error rendering Jinja template: {e}")
            return template  # Return original on any error

    async def _generate_templated_content(
        self,
        context: ConversationContext,
        content,  # ItemContentDto
        item=None,  # ConversationItemDto
    ) -> str | None:
        """Generate templated content using LLM.

        Uses item.instructions (if available) to guide content generation.
        Falls back to source_id lookup if no instructions provided.

        Note: LLM generation uses the LlmProviderFactory directly rather than
        going through the Agent, as templated content generation is a simple
        one-shot request without tool calling or conversation context.

        Args:
            context: The conversation context
            content: The ItemContentDto with is_templated=True
            item: The parent ConversationItemDto

        Returns:
            Generated content string, or None if generation failed
        """
        # Build the generation prompt
        instructions = getattr(item, "instructions", None) if item else None
        if not instructions and not content.source_id:
            log.debug(f"Templated content {content.id} has no instructions or source_id, skipping generation")
            return None

        try:
            # Build prompt for LLM
            prompt_parts = []

            if instructions:
                # Render instructions with Jinja variables
                rendered_instructions = self._render_jinja_template(instructions, context)
                prompt_parts.append(rendered_instructions)

            if content.source_id:
                # TODO: Fetch SkillTemplate by source_id and incorporate its prompt
                prompt_parts.append(f"Content type: {content.source_id}")

            if content.widget_type != "message":
                prompt_parts.append(f"Generate content suitable for a {content.widget_type} widget.")

            if not prompt_parts:
                return None

            full_prompt = "\n\n".join(prompt_parts)
            log.debug(f"Generating templated content with prompt: {full_prompt[:200]}...")

            # Use LlmProviderFactory directly for simple content generation
            generated = await self._generate_with_llm(context, full_prompt)
            return generated

        except Exception as e:
            log.exception(f"Error generating templated content: {e}")
            return None

    async def _generate_with_llm(self, context: ConversationContext, prompt: str) -> str | None:
        """Generate content using the LLM provider.

        Uses the model configured in the conversation context for a simple
        one-shot text generation.

        Args:
            context: The conversation context with model configuration
            prompt: The generation prompt

        Returns:
            Generated content string, or None if generation failed
        """
        try:
            from application.agents.llm_provider import LlmMessage, LlmMessageRole

            # Get the model from context (uses definition's model or default)
            model_id = context.model or "openai:gpt-4o-mini"

            # Get the appropriate LLM provider
            llm_provider = self._llm_provider_factory.get_provider_for_model(model_id)

            # Build a simple message list for generation
            messages = [
                LlmMessage(role=LlmMessageRole.SYSTEM, content="You are a helpful assistant generating educational content."),
                LlmMessage(role=LlmMessageRole.USER, content=prompt),
            ]

            # Generate response (non-streaming for simplicity)
            response = await llm_provider.chat(messages)

            return response.content if response else None

        except Exception as e:
            log.exception(f"Error in LLM content generation: {e}")
            return None

    async def _send_widget_render(
        self,
        connection: Connection,
        context: ConversationContext,
        item,  # ConversationItemDto
        content,  # ItemContentDto
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

    async def _send_confirmation_widget(
        self,
        connection: Connection,
        context: ConversationContext,
        item,  # ConversationItemDto
    ) -> None:
        """Send a confirmation button widget for items requiring user confirmation.

        Args:
            connection: The WebSocket connection
            context: The conversation context
            item: The ConversationItemDto that requires confirmation
        """
        from application.protocol.widgets.base import WidgetConstraints, WidgetLayout, WidgetRenderPayload

        # Generate a unique widget ID for the confirmation button
        confirmation_widget_id = f"{item.id}-confirm"

        # Build the render payload for a button widget
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

    async def _complete_proactive_flow(
        self,
        connection: Connection,
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
        if completion_message:
            await self._stream_agent_response(connection, context, completion_message)

        # Check if we should continue with free chat after completion
        continue_after = context.template_config.get("continue_after_completion", False)
        if continue_after:
            context.state = OrchestratorState.READY
            await self._send_chat_input_enabled(connection, True)
            log.info("🎭 Proactive flow complete, continuing with free chat")
        else:
            context.state = OrchestratorState.COMPLETED
            await self._send_chat_input_enabled(connection, False)
            log.info("🎭 Proactive flow complete, conversation ended")

        # TODO: Send final score report if configured
        # if context.template_config.get("display_final_score_report"):
        #     await self._send_score_report(connection, context)

    async def _advance_to_next_item(
        self,
        connection: Connection,
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
            await self._complete_proactive_flow(connection, context)
        else:
            # Present next item
            await self._present_item(connection, context, next_index)

    async def _send_item_context(
        self,
        connection: Connection,
        context: ConversationContext,
        item_index: int,
        item=None,  # Optional ConversationItemDto for additional data
    ) -> None:
        """Send item context to client.

        Args:
            connection: The WebSocket connection
            context: The conversation context
            item_index: The item index
            item: Optional item DTO for additional metadata
        """
        # Use item data if provided, otherwise use defaults
        item_id = item.id if item else f"item-{item_index}"
        item_title = item.title if item else f"Item {item_index + 1}"
        enable_chat = item.enable_chat_input if item else True
        time_limit = item.time_limit_seconds if item else None

        item_context = ItemContextPayload(
            itemId=item_id,
            itemIndex=item_index,
            totalItems=max(context.total_items, 1),
            itemTitle=item_title,
            enableChatInput=enable_chat,
            timeLimitSeconds=time_limit,
            showRemainingTime=bool(time_limit),
            widgetCompletionBehavior="readonly",
            conversationDeadline=None,
        )

        context_message = create_message(
            message_type="control.item.context",
            payload=item_context.model_dump(by_alias=True, exclude_none=True),
            conversation_id=context.conversation_id,
        )
        await self._connection_manager.send_to_connection(connection.connection_id, context_message)


# =============================================================================
# Factory / DI Configuration
# =============================================================================


def configure_orchestrator(builder: Any) -> None:
    """Configure the ConversationOrchestrator in the service collection.

    This should be called during application startup after Mediator and
    ConnectionManager are configured.

    Args:
        builder: The application builder
    """
    from neuroglia.hosting.abstractions import ApplicationBuilderBase

    if not isinstance(builder, ApplicationBuilderBase):
        log.warning("Builder is not ApplicationBuilderBase, skipping orchestrator configuration")
        return

    # Create the orchestrator after DI resolution
    # Note: For proper DI, this would use a factory pattern, but for now
    # we create it during configure() and register as singleton
    log.info("✅ ConversationOrchestrator configuration placeholder added")
    # Actual wiring is done in main.py after all services are registered
