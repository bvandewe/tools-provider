"""Chat service orchestrating conversation flow with Agent and tools.

This service is the high-level orchestrator that:
- Manages conversation state (Neuroglia Aggregate)
- Delegates message processing to the Agent abstraction
- Provides tool execution capability to the agent
- Streams events to the client

The Agent abstraction handles:
- LLM interaction (via LlmProvider)
- ReAct/tool-calling loop
- Response generation
"""

import json
import logging
import time
from typing import Any, AsyncIterator, Optional

import httpx
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.hosting.abstractions import ApplicationBuilderBase
from opentelemetry import trace

from application.agents import Agent, AgentEvent, AgentEventType, LlmMessage, LlmToolDefinition
from application.agents.base_agent import AgentRunContext, ToolExecutionRequest, ToolExecutionResult
from application.services.tool_provider_client import ToolProviderClient
from application.settings import Settings
from domain.entities.conversation import Conversation
from domain.models.message import Message, MessageRole, MessageStatus
from domain.models.tool import Tool
from infrastructure.adapters import OllamaError
from observability import tool_cache_hits, tool_cache_misses

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class ChatServiceError(Exception):
    """Custom exception for chat service errors with user-friendly messages."""

    def __init__(self, message: str, error_code: str, is_retryable: bool = False, details: Optional[dict] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.is_retryable = is_retryable
        self.details = details or {}

    def to_dict(self) -> dict:
        return {
            "message": self.message,
            "error_code": self.error_code,
            "is_retryable": self.is_retryable,
            "details": self.details,
        }


class ChatService:
    """
    Orchestrates the chat conversation flow using the Agent abstraction.

    Responsibilities:
    - Managing conversation state (Neuroglia Aggregate with Event Sourcing)
    - Delegating message processing to Agent
    - Providing tool execution callback to Agent
    - Translating Agent events to client stream events
    - Persisting messages to conversation

    The actual LLM interaction and tool-calling loop is handled by the Agent,
    making this service provider-agnostic.
    """

    def __init__(
        self,
        conversation_repository: Repository[Conversation, str],
        tool_provider_client: ToolProviderClient,
        agent: Agent,
        settings: Settings,
    ) -> None:
        """
        Initialize the chat service.

        Args:
            conversation_repository: Repository for conversation persistence (EventSourcing)
            tool_provider_client: Client for Tools Provider API
            agent: The agent implementation (e.g., ReActAgent)
            settings: Application settings
        """
        self._conversation_repo = conversation_repository
        self._tool_provider = tool_provider_client
        self._agent = agent
        self._settings = settings
        self._tools_cache: dict[str, list[Tool]] = {}

    def set_model_override(self, model: Optional[str]) -> None:
        """Set a temporary model override for this conversation.

        This method supports the multi-provider architecture. When a model ID
        is provided with a provider prefix (e.g., 'openai:gpt-4o', 'ollama:llama3'),
        it uses the factory to get the appropriate provider. Otherwise, it
        attempts to use the current provider's set_model_override method.

        Args:
            model: Model name to use (optionally prefixed with provider:), or None to clear override
        """
        from application.agents import LlmProvider

        logger.debug(f"🔄 set_model_override called with model='{model}'")

        if model is None:
            # Clear override on the current provider
            logger.debug("🔄 Clearing model override")
            if hasattr(self._agent, "_llm") and isinstance(self._agent._llm, LlmProvider):
                self._agent._llm.set_model_override(None)
            return

        # Check if model has a provider prefix
        if ":" in model:
            # Model is qualified (e.g., "openai:gpt-4o"), use factory singleton
            from infrastructure import get_provider_factory

            logger.info(f"🔄 Qualified model ID detected: '{model}', routing to factory")
            try:
                factory = get_provider_factory()
                if factory is None:
                    logger.error("🔄 LlmProviderFactory singleton not initialized!")
                    return

                provider = factory.get_provider_for_model(model)
                if provider and provider != self._agent._llm:
                    # Switch to the new provider
                    # Note: This requires the agent to accept provider changes at runtime
                    if hasattr(self._agent, "_llm"):
                        old_provider = type(self._agent._llm).__name__
                        self._agent._llm = provider
                        logger.info(f"🔄 Switched provider from {old_provider} to {type(provider).__name__} for model: {model}")
                elif provider:
                    # Same provider, just update the model override
                    actual_model = model.split(":", 1)[1]
                    provider.set_model_override(actual_model)
                    logger.info(f"🔄 Same provider, updated model override to: {actual_model}")
            except Exception as e:
                logger.warning(f"Failed to get provider for model '{model}': {e}", exc_info=True)
        else:
            # No provider prefix, use current provider's override
            logger.debug(f"🔄 Unqualified model ID: '{model}', using current provider override")
            if hasattr(self._agent, "_llm") and isinstance(self._agent._llm, LlmProvider):
                self._agent._llm.set_model_override(model)
                logger.info(f"🔄 Set model override to: {model}")
            else:
                logger.warning("Cannot set model override - LLM provider does not support it")

    async def get_or_create_conversation(
        self,
        user_id: str,
        conversation_id: Optional[str] = None,
    ) -> Conversation:
        """
        Get an existing conversation or create a new one.

        Args:
            user_id: The user ID
            conversation_id: Optional specific conversation ID

        Returns:
            The conversation
        """
        if conversation_id:
            conversation = await self._conversation_repo.get_async(conversation_id)
            if conversation and conversation.state.user_id == user_id:
                return conversation

        # Create new conversation with system prompt (Neuroglia pattern)
        conversation = Conversation(
            user_id=user_id,
            system_prompt=self._agent.config.system_prompt,
        )
        return await self._conversation_repo.add_async(conversation)

    async def get_tools(self, access_token: str, force_refresh: bool = False) -> list[Tool]:
        """
        Get available tools, using cache if available.

        Args:
            access_token: User's access token
            force_refresh: Force refresh from Tools Provider

        Returns:
            List of available tools
        """
        cache_key = "tools"  # Could use user-specific key if needed

        if not force_refresh and cache_key in self._tools_cache:
            tool_cache_hits.add(1)
            return self._tools_cache[cache_key]

        tool_cache_misses.add(1)

        try:
            tool_data = await self._tool_provider.get_tools(access_token)
            tools = [Tool.from_bff_response(t) for t in tool_data]

            # Debug: log parsed tool parameters
            for t in tools:
                logger.debug(f"Parsed Tool '{t.name}' has {len(t.parameters)} parameters: {[p.name for p in t.parameters]}")

            # Apply tool filtering from agent config
            if self._agent.config.tool_whitelist:
                tools = [t for t in tools if t.name in self._agent.config.tool_whitelist]
            if self._agent.config.tool_blacklist:
                tools = [t for t in tools if t.name not in self._agent.config.tool_blacklist]

            self._tools_cache[cache_key] = tools
            logger.debug(f"Cached {len(tools)} tools (filtered from config)")
            return tools
        except Exception as e:
            logger.error(f"Failed to fetch tools: {e}")
            # Return cached tools if available
            return self._tools_cache.get(cache_key, [])

    async def send_message(
        self,
        conversation: Conversation,
        user_message: str,
        access_token: str,
        model_id: Optional[str] = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Send a user message and stream the response using the Agent.

        This delegates the actual LLM interaction and tool-calling loop
        to the Agent abstraction, making the service LLM-agnostic.

        Flow:
        1. Add user message to conversation (Neuroglia Aggregate)
        2. Build AgentRunContext with history and tools
        3. Stream Agent events, translating to client format
        4. Persist assistant messages and tool results to conversation

        Args:
            conversation: The conversation (Neuroglia aggregate)
            user_message: The user's message
            access_token: User's access token for tool execution
            model_id: Optional model ID to use for this message

        Yields:
            Stream events for the client (SSE format)
        """
        # Set model override if specified
        if model_id:
            logger.info(f"🎯 Model override requested: {model_id}")
            self.set_model_override(model_id)
        else:
            logger.debug("📍 No model override specified, using default provider model")

        # Add user message to aggregate (via domain event)
        user_msg_id = conversation.add_user_message(user_message)
        await self._conversation_repo.update_async(conversation)

        yield {
            "event": "message_added",
            "data": {
                "message_id": user_msg_id,
                "role": "user",
                "content": user_message,
            },
        }

        # Get available tools and convert to LLM tool definitions
        tools = await self.get_tools(access_token)
        tool_definitions = [self._tool_to_llm_definition(t) for t in tools]

        # Get conversation context as LlmMessages
        # Note: We exclude system messages (agent adds its own from config)
        # and exclude the current user message (agent adds it from user_message param)
        context_messages = conversation.get_context_messages(max_messages=self._settings.conversation_history_max_messages)
        # Filter out system messages and the current user message we just added
        history_messages = [m for m in context_messages if m.role != MessageRole.SYSTEM and m.id != user_msg_id]
        llm_history = [self._message_to_llm_message(m) for m in history_messages]

        # Create tool executor that captures access_token
        async def tool_executor(request: ToolExecutionRequest) -> AsyncIterator[ToolExecutionResult]:
            """Execute a tool call via the Tools Provider."""
            yield await self._execute_tool(request, access_token)

        # Build the agent run context
        run_context = AgentRunContext(
            user_message=user_message,
            conversation_history=llm_history,
            tools=tool_definitions,
            tool_executor=tool_executor,
            access_token=access_token,
            metadata={
                "conversation_id": conversation.id(),
                "user_id": conversation.state.user_id,
            },
        )

        # Track current assistant message for persisting
        current_assistant_msg_id: Optional[str] = None
        current_assistant_content: str = ""

        # Run the agent and translate events
        try:
            async for event in self._agent.run_stream(run_context):
                # Handle state updates based on event type
                if event.type == AgentEventType.LLM_REQUEST_STARTED:
                    yield {"event": "assistant_thinking", "data": {}}

                elif event.type == AgentEventType.LLM_RESPONSE_CHUNK:
                    chunk = event.data.get("content", "")
                    current_assistant_content += chunk
                    yield {
                        "event": "content_chunk",
                        "data": {"content": chunk},
                    }

                elif event.type == AgentEventType.LLM_RESPONSE_COMPLETED:
                    # Create assistant message in aggregate
                    tool_calls = event.data.get("tool_calls", [])
                    status = MessageStatus.PENDING if tool_calls else MessageStatus.COMPLETED

                    current_assistant_msg_id = conversation.add_assistant_message(
                        content=current_assistant_content,
                        status=status,
                    )

                    # Add tool calls to message
                    for tc in tool_calls:
                        conversation.add_tool_call(
                            message_id=current_assistant_msg_id,
                            tool_name=tc.get("name", ""),
                            arguments=tc.get("arguments", {}),
                            call_id=tc.get("id", ""),
                        )

                    await self._conversation_repo.update_async(conversation)

                elif event.type == AgentEventType.TOOL_CALLS_DETECTED:
                    yield {
                        "event": "tool_calls_detected",
                        "data": {
                            "tool_calls": [
                                {
                                    "tool_name": tc.get("name", ""),
                                    "arguments": tc.get("arguments", {}),
                                }
                                for tc in event.data.get("tool_calls", [])
                            ]
                        },
                    }

                elif event.type == AgentEventType.TOOL_EXECUTION_STARTED:
                    yield {
                        "event": "tool_executing",
                        "data": {
                            "call_id": event.data.get("call_id", ""),
                            "tool_name": event.data.get("tool_name", ""),
                        },
                    }

                elif event.type == AgentEventType.TOOL_EXECUTION_COMPLETED:
                    result = event.data
                    yield {
                        "event": "tool_result",
                        "data": {
                            "call_id": result.get("call_id", ""),
                            "tool_name": result.get("tool_name", ""),
                            "success": result.get("success", True),
                            "result": result.get("result"),
                            "error": result.get("error"),
                            "execution_time_ms": result.get("execution_time_ms", 0),
                        },
                    }

                    # Add tool result to aggregate
                    if current_assistant_msg_id:
                        conversation.add_tool_result(
                            message_id=current_assistant_msg_id,
                            call_id=result.get("call_id", ""),
                            tool_name=result.get("tool_name", ""),
                            success=result.get("success", True),
                            result=result.get("result"),
                            error=result.get("error"),
                            execution_time_ms=result.get("execution_time_ms", 0),
                        )

                elif event.type == AgentEventType.TOOL_EXECUTION_FAILED:
                    yield {
                        "event": "tool_result",
                        "data": {
                            "call_id": event.data.get("call_id", ""),
                            "tool_name": event.data.get("tool_name", ""),
                            "success": False,
                            "error": event.data.get("error", "Unknown error"),
                        },
                    }

                elif event.type == AgentEventType.RUN_COMPLETED:
                    # Mark final assistant message as complete
                    if current_assistant_msg_id:
                        conversation.update_message_status(current_assistant_msg_id, MessageStatus.COMPLETED)
                    await self._conversation_repo.update_async(conversation)

                    yield {
                        "event": "message_complete",
                        "data": {
                            "message_id": current_assistant_msg_id,
                            "role": "assistant",
                            "content": current_assistant_content,
                        },
                    }

                elif event.type == AgentEventType.RUN_FAILED:
                    error = event.data.get("error", "Unknown error")
                    yield {
                        "event": "error",
                        "data": {"error": str(error)},
                    }

                elif event.type == AgentEventType.ITERATION_STARTED:
                    # Reset content for new iteration (after tool execution)
                    current_assistant_content = ""

        except OllamaError as e:
            # Handle Ollama-specific errors with user-friendly messages
            logger.error(f"Ollama error: {e.error_code} - {e.message}", exc_info=True)
            yield {
                "event": "error",
                "data": {
                    "error": e.message,
                    "error_code": e.error_code,
                    "is_retryable": e.is_retryable,
                    "details": e.details,
                },
            }
        except httpx.ConnectError as e:
            logger.error(f"Connection error: {e}", exc_info=True)
            yield {
                "event": "error",
                "data": {
                    "error": "Cannot connect to AI service. Please try again later.",
                    "error_code": "connection_error",
                    "is_retryable": True,
                },
            }
        except httpx.TimeoutException as e:
            logger.error(f"Timeout error: {e}", exc_info=True)
            yield {
                "event": "error",
                "data": {
                    "error": "Request timed out. The AI model may be busy.",
                    "error_code": "timeout",
                    "is_retryable": True,
                },
            }
        except Exception as e:
            logger.error(f"Agent execution failed: {e}", exc_info=True)
            yield {
                "event": "error",
                "data": {
                    "error": str(e),
                    "error_code": "unknown_error",
                    "is_retryable": False,
                },
            }

        # Final save and stream complete
        await self._conversation_repo.update_async(conversation)
        yield {"event": "stream_complete", "data": {}}

    async def _execute_tool(
        self,
        request: ToolExecutionRequest,
        access_token: str,
    ) -> ToolExecutionResult:
        """
        Execute a tool call via the Tools Provider.

        Args:
            request: Tool execution request from the agent
            access_token: User's access token for authentication

        Returns:
            The tool execution result
        """
        start_time = time.time()
        try:
            result = await self._tool_provider.execute_tool(
                tool_name=request.tool_name,
                arguments=request.arguments,
                access_token=access_token,
            )
            execution_time = (time.time() - start_time) * 1000

            return ToolExecutionResult(
                call_id=request.call_id,
                tool_name=request.tool_name,
                success=result.get("success", True),
                result=result.get("data", result.get("result", result)),
                error=result.get("error"),
                execution_time_ms=execution_time,
            )
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return ToolExecutionResult(
                call_id=request.call_id,
                tool_name=request.tool_name,
                success=False,
                result=None,
                error=str(e),
                execution_time_ms=execution_time,
            )

    def _tool_to_llm_definition(self, tool: Tool) -> LlmToolDefinition:
        """Convert a domain Tool to an LLM tool definition.

        Uses ToolParameter.to_json_schema() to preserve full schema information
        including 'items' for arrays and 'properties' for objects, which is
        required by OpenAI's API.
        """
        llm_def = LlmToolDefinition(
            name=tool.name,
            description=tool.description,
            parameters={
                "type": "object",
                "properties": {p.name: p.to_json_schema() for p in tool.parameters},
                "required": [p.name for p in tool.parameters if p.required],
            },
        )
        logger.debug(f"_tool_to_llm_definition for '{tool.name}': {len(tool.parameters)} params -> {llm_def.parameters}")
        return llm_def

    def _message_to_llm_message(self, message: Message) -> LlmMessage:
        """Convert a domain Message to an LlmMessage."""
        if message.role == MessageRole.SYSTEM:
            return LlmMessage.system(message.content)
        elif message.role == MessageRole.USER:
            return LlmMessage.user(message.content)
        elif message.role == MessageRole.ASSISTANT:
            # Handle tool calls if present
            if message.tool_calls:
                from application.agents import LlmToolCall

                tool_calls = [
                    LlmToolCall(
                        id=tc.call_id,
                        name=tc.tool_name,
                        arguments=tc.arguments,
                    )
                    for tc in message.tool_calls
                ]
                return LlmMessage.assistant(message.content, tool_calls=tool_calls)
            return LlmMessage.assistant(message.content)
        elif message.role == MessageRole.TOOL:
            # For tool results
            if message.tool_results:
                tr = message.tool_results[0]  # Use first tool result
                content = json.dumps(tr.result) if tr.success else f"Error: {tr.error}"
                return LlmMessage.tool_result(
                    tool_call_id=tr.call_id,
                    tool_name=tr.tool_name,
                    content=content,
                )
            return LlmMessage.user(message.content)  # Fallback
        else:
            return LlmMessage.user(message.content)

    def _translate_agent_event(
        self,
        event: AgentEvent,
        conversation: Conversation,
        current_msg_id: Optional[str],
    ) -> dict[str, Any]:
        """
        Translate an AgentEvent to client-friendly format.

        This is a passthrough for now but can be extended for
        custom event transformations.
        """
        return event.to_dict()

    async def clear_conversation(self, conversation: Conversation) -> Conversation:
        """
        Clear a conversation's messages (keeps system prompt).

        Args:
            conversation: The conversation to clear

        Returns:
            The cleared conversation
        """
        conversation.clear_messages(keep_system=True)
        await self._conversation_repo.update_async(conversation)
        return conversation

    async def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete a conversation.

        Args:
            conversation_id: The conversation ID

        Returns:
            True if deleted
        """
        conversation = await self._conversation_repo.get_async(conversation_id)
        if conversation:
            conversation.delete()
            await self._conversation_repo.remove_async(conversation_id)
            return True
        return False

    async def get_conversations(self, user_id: str) -> list[Conversation]:
        """
        Get all conversations for a user.

        Note: This queries the read model for efficiency.
        For full aggregates, use the EventSourcing repository.

        Args:
            user_id: The user ID

        Returns:
            List of conversations (as aggregates)
        """
        # For now, return empty - the read model repository should be used for queries
        # This method is kept for backward compatibility but queries should use CQRS
        return []

    @staticmethod
    def configure(builder: ApplicationBuilderBase) -> None:
        """
        Configure ChatService as a scoped service in the DI container.

        ChatService is registered as scoped because it depends on ConversationRepository
        which is also scoped (one repository instance per request scope).

        Args:
            builder: The application builder
        """
        from application.agents import Agent
        from application.settings import app_settings
        from domain.repositories import ConversationRepository

        builder.services.add_scoped(
            ChatService,
            implementation_factory=lambda sp: ChatService(
                conversation_repository=sp.get_required_service(ConversationRepository),
                tool_provider_client=sp.get_required_service(ToolProviderClient),
                agent=sp.get_required_service(Agent),
                settings=app_settings,
            ),
        )
        logger.info("Configured ChatService as scoped service")
