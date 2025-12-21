"""Agent runner for executing agents and streaming events.

This module provides the AgentRunner class which handles the execution of
agents, building context from conversation history, and translating agent
events to WebSocket protocol messages.
"""

import logging
import uuid
from typing import TYPE_CHECKING, Any, Protocol

from application.agents import Agent, AgentEventType, AgentRunContext
from application.orchestrator.agent.tool_executor import ToolExecutor
from application.orchestrator.context import ConversationContext
from application.protocol.core import ProtocolMessage, create_message
from application.protocol.data import ContentChunkPayload, ContentCompletePayload, ToolCallPayload, ToolResultPayload

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

    async def send_to_connection(self, connection_id: str, message: ProtocolMessage[Any]) -> bool:
        """Send a message to a specific connection."""
        ...


class LlmProviderFactoryProtocol(Protocol):
    """Protocol for LLM provider factory interface."""

    def get_provider_for_model(self, model_id: str) -> Any:
        """Get the appropriate provider for a given model ID."""
        ...


class AgentRunner:
    """Executes agents and streams events to WebSocket clients.

    The AgentRunner is the core class that:
    1. Builds agent context from conversation history
    2. Invokes agent.run_stream() async generator
    3. Translates AgentEvents to WebSocket protocol messages
    4. Accumulates final response content

    Example:
        >>> runner = AgentRunner(agent, mediator, connection_manager, llm_factory, tool_executor)
        >>> response = await runner.run_stream(connection, context, "Hello!")
        >>> print(response)  # "Hello! How can I help you?"
    """

    def __init__(
        self,
        agent: Agent,
        mediator: MediatorProtocol,
        connection_manager: ConnectionManagerProtocol,
        llm_provider_factory: LlmProviderFactoryProtocol,
        tool_executor: ToolExecutor,
        send_chat_input_enabled: Any = None,
        send_error: Any = None,
    ) -> None:
        """Initialize the AgentRunner.

        Args:
            agent: The agent instance to run
            mediator: Mediator for executing queries
            connection_manager: Manager for WebSocket connections
            llm_provider_factory: Factory for creating LLM providers
            tool_executor: Executor for tool calls
            send_chat_input_enabled: Callback for enabling/disabling chat input
            send_error: Callback for sending error messages
        """
        self._agent = agent
        self._mediator = mediator
        self._connection_manager = connection_manager
        self._llm_provider_factory = llm_provider_factory
        self._tool_executor = tool_executor
        self._send_chat_input_enabled = send_chat_input_enabled
        self._send_error = send_error

    async def run_stream(
        self,
        connection: "Connection",
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

            # Stream agent events
            async for event in self._agent.run_stream(agent_context):
                log.debug(f"AgentEvent: {event.type.value}")

                if event.type == AgentEventType.RUN_STARTED:
                    # Disable chat input during streaming
                    if self._send_chat_input_enabled:
                        await self._send_chat_input_enabled(connection, False)

                elif event.type == AgentEventType.LLM_RESPONSE_CHUNK:
                    # Stream content chunk to client
                    chunk = event.data.get("content", "")
                    accumulated_content += chunk

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
                    await self._send_tool_call(connection, context, event.data)

                elif event.type == AgentEventType.TOOL_EXECUTION_COMPLETED:
                    # Notify client of tool result
                    await self._send_tool_result(connection, context, event.data)

                elif event.type == AgentEventType.RUN_COMPLETED:
                    # Send final chunk marker and content complete message
                    await self._send_stream_complete(connection, context, message_id, accumulated_content)

                    # Re-enable chat input after streaming completes
                    if self._send_chat_input_enabled:
                        await self._send_chat_input_enabled(connection, True)

                elif event.type == AgentEventType.RUN_FAILED:
                    # Send error and stop
                    error_msg = event.data.get("error", "Unknown agent error")
                    log.error(f"Agent run failed: {error_msg}")
                    if self._send_error:
                        await self._send_error(connection, "AGENT_ERROR", error_msg)
                    # Re-enable chat input on error
                    if self._send_chat_input_enabled:
                        await self._send_chat_input_enabled(connection, True)
                    return None

            return accumulated_content

        except Exception as e:
            log.exception(f"Error running agent stream: {e}")
            if self._send_error:
                await self._send_error(connection, "AGENT_ERROR", str(e))
            # Re-enable chat input on exception
            if self._send_chat_input_enabled:
                await self._send_chat_input_enabled(connection, True)
            return None

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

        # Create tool executor function
        tool_executor_fn = self._tool_executor.create_executor(access_token=context.access_token)

        return AgentRunContext(
            user_message=user_message,
            conversation_history=history,
            tools=context.tools,  # Tools loaded from ToolProviderClient
            tool_executor=tool_executor_fn,
            access_token=context.access_token,
            metadata={
                "conversation_id": context.conversation_id,
                "definition_id": context.definition_id,
            },
        )

    async def _send_tool_call(
        self,
        connection: "Connection",
        context: ConversationContext,
        tool_data: dict,
    ) -> None:
        """Send tool call notification to client.

        Args:
            connection: The WebSocket connection
            context: The conversation context
            tool_data: Tool call data from agent event
        """
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

    async def _send_tool_result(
        self,
        connection: "Connection",
        context: ConversationContext,
        tool_data: dict,
    ) -> None:
        """Send tool result notification to client.

        Args:
            connection: The WebSocket connection
            context: The conversation context
            tool_data: Tool result data from agent event
        """
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

    async def _send_stream_complete(
        self,
        connection: "Connection",
        context: ConversationContext,
        message_id: str,
        accumulated_content: str,
    ) -> None:
        """Send stream completion messages to client.

        Args:
            connection: The WebSocket connection
            context: The conversation context
            message_id: The message ID for this stream
            accumulated_content: The full accumulated content
        """
        # Send final chunk marker
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

        # Send content complete message
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
