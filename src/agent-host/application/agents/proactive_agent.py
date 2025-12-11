"""Proactive Agent implementation for Agent Host.

This module implements a proactive agent that drives interactive sessions,
presenting questions/tasks to users via client-side widgets and collecting
responses to continue the session.

Key Differences from ReActAgent:
- Proactive: Agent initiates with content, not just reacting to user
- Client Tools: Some tool calls trigger UI widgets instead of server execution
- Suspendable: Agent can pause waiting for user input, then resume
- Session-Aware: Tracks items completed, pending actions, session state

Flow:
1. Agent starts with session context (type, config, goals)
2. Agent generates content, may call client tools (widgets)
3. If client tool called: Suspend, emit CLIENT_ACTION, wait for response
4. On response: Resume, inject response, continue loop
5. Repeat until agent decides session is complete
"""

import logging
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from application.agents.agent_config import AgentConfig
from application.agents.base_agent import Agent, AgentError, AgentEvent, AgentEventType, AgentRunContext, AgentRunResult, ToolExecutionRequest
from application.agents.client_tools import (
    CLIENT_TOOL_NAMES,
    extract_widget_payload,
    get_all_client_tools,
    is_client_tool,
    validate_response,
)
from application.agents.llm_provider import LlmMessage, LlmProvider, LlmToolCall, LlmToolDefinition
from domain.models.session_models import ClientAction, ClientResponse, SessionConfig, SessionType

logger = logging.getLogger(__name__)


# =============================================================================
# System Prompts by Session Type
# =============================================================================

THOUGHT_SESSION_PROMPT = """You are a Socratic thinking partner helping the user explore ideas through guided reflection.

Your role:
- Ask thoughtful questions to help the user think deeply
- Guide self-discovery rather than providing direct answers
- Challenge assumptions constructively
- Help organize and structure thinking
- Build on the user's responses to go deeper

Session Guidelines:
- Start with open-ended questions about the topic
- Use follow-up questions to explore implications
- Present choices when there are clear decision points
- Request written reflections for complex ideas
- Synthesize and reflect back what you've learned from the user

Available widgets:
- present_choices: For decision points or perspectives to consider
- request_free_text: For reflections and extended thinking

Focus on the journey of thought, not reaching a predetermined destination."""

LEARNING_SESSION_PROMPT = """You are an educational AI tutor conducting a personalized learning session.

Your role:
- Guide the student through learning material step by step
- Present concepts clearly before assessing understanding
- Use multiple choice questions to check comprehension
- Use free text prompts for explanations and deeper thinking
- Use code editors for programming exercises
- Provide encouraging, constructive feedback on responses
- Adapt difficulty based on student performance

Session Guidelines:
- Start by introducing the topic and learning objectives
- Present content in digestible chunks
- After explaining a concept, assess understanding with a question
- Celebrate correct answers and gently correct mistakes
- Summarize key takeaways at the end

Available widgets:
- present_choices: For multiple choice questions (2-6 options)
- request_free_text: For written responses and explanations
- present_code_editor: For coding exercises

Always explain WHY an answer is correct or incorrect to reinforce learning."""

VALIDATION_SESSION_PROMPT = """You are a technical validator helping the user verify their solution or approach.

Your role:
- Present validation criteria clearly
- Guide through systematic checking
- Ask for specific information to validate
- Provide clear pass/fail feedback
- Suggest improvements when issues are found

Session Guidelines:
- Start by clarifying what is being validated
- Present validation steps in logical order
- Use multiple choice for yes/no decisions
- Use code editor when reviewing code
- Summarize validation results at the end

Available widgets:
- present_choices: For validation checkpoints (pass/fail/skip)
- request_free_text: For explanations or descriptions
- present_code_editor: For code review

Be precise and systematic in your validation approach."""

DEFAULT_PROACTIVE_PROMPT = """You are a proactive AI assistant guiding the user through an interactive session.

Your role:
- Drive the conversation forward with purposeful interactions
- Use widgets to collect user input at appropriate moments
- Process responses and continue the flow
- Complete the session objectives efficiently

Available widgets:
- present_choices: For multiple choice selections
- request_free_text: For free-form text input
- present_code_editor: For code input

Guide the user through a productive interaction."""

SESSION_TYPE_PROMPTS: dict[SessionType, str] = {
    SessionType.LEARNING: LEARNING_SESSION_PROMPT,
    SessionType.THOUGHT: THOUGHT_SESSION_PROMPT,
    SessionType.VALIDATION: VALIDATION_SESSION_PROMPT,
}


def get_system_prompt_for_session_type(session_type: SessionType, custom_prompt: str | None = None) -> str:
    """Get the system prompt for a session type.

    Args:
        session_type: Type of session
        custom_prompt: Optional custom prompt to use instead

    Returns:
        System prompt string
    """
    if custom_prompt:
        return custom_prompt
    return SESSION_TYPE_PROMPTS.get(session_type, DEFAULT_PROACTIVE_PROMPT)


# =============================================================================
# Proactive Agent Context
# =============================================================================


@dataclass
class ProactiveSessionContext:
    """Context for a proactive session.

    Extends the base AgentRunContext with session-specific information.

    Attributes:
        session_id: Unique session identifier
        session_type: Type of session (learning, thought, validation)
        config: Session configuration
        conversation_id: Linked conversation ID
        initial_message: Optional initial message/topic from user
        items_completed: Number of items/questions completed
        custom_system_prompt: Optional override for system prompt
        metadata: Additional session metadata
    """

    session_id: str
    session_type: SessionType
    config: SessionConfig
    conversation_id: str
    initial_message: str | None = None
    items_completed: int = 0
    custom_system_prompt: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SuspendedState:
    """State captured when agent suspends for client input.

    Allows the agent to resume exactly where it left off.

    Attributes:
        messages: Conversation messages at suspension point
        pending_tool_call: The client tool call waiting for response
        iteration: Current iteration number
        tool_calls_made: Total tool calls made so far
        start_time: When the run started (for total time tracking)
    """

    messages: list[LlmMessage]
    pending_tool_call: LlmToolCall
    iteration: int
    tool_calls_made: int
    start_time: float


# =============================================================================
# Proactive Agent
# =============================================================================


class ProactiveAgent(Agent):
    """Proactive agent that drives interactive sessions with client widgets.

    Unlike the reactive ReActAgent which responds to user messages, the
    ProactiveAgent initiates interactions, presents content/questions via
    widgets, and processes responses to continue the session.

    Key Features:
    - Session-type-specific behavior (learning, thought, validation)
    - Client tool interception (widgets instead of server execution)
    - Suspendable execution (pause for user input, resume with response)
    - Progress tracking (items completed, session state)

    Usage:
        agent = ProactiveAgent(llm_provider, config)
        context = ProactiveSessionContext(
            session_id="...",
            session_type=SessionType.LEARNING,
            config=session_config,
            conversation_id="...",
        )

        # Start session (will suspend on first widget)
        async for event in agent.start_session(context):
            if event.type == AgentEventType.RUN_SUSPENDED:
                # Widget displayed, waiting for user response
                break
            handle_event(event)

        # Resume with user's response
        response = ClientResponse(tool_call_id="...", data={"selection": "A"})
        async for event in agent.resume_with_response(response):
            handle_event(event)
    """

    def __init__(
        self,
        llm_provider: LlmProvider,
        config: AgentConfig | None = None,
    ) -> None:
        """Initialize the proactive agent.

        Args:
            llm_provider: The LLM provider to use
            config: Agent configuration (optional)
        """
        super().__init__(llm_provider, config)
        self._suspended_state: SuspendedState | None = None
        self._session_context: ProactiveSessionContext | None = None

    @property
    def is_suspended(self) -> bool:
        """Check if agent is currently suspended waiting for input."""
        return self._suspended_state is not None

    @property
    def pending_tool_call(self) -> LlmToolCall | None:
        """Get the pending tool call if suspended."""
        return self._suspended_state.pending_tool_call if self._suspended_state else None

    def _build_system_message_for_session(self, context: ProactiveSessionContext) -> LlmMessage:
        """Build session-specific system message.

        Args:
            context: Session context

        Returns:
            System message with session-appropriate prompt
        """
        prompt = get_system_prompt_for_session_type(context.session_type, context.custom_system_prompt)

        # Add session context to prompt
        prompt += f"\n\n---\nSession Info:\n- Type: {context.session_type.value}\n"
        prompt += f"- Items Completed: {context.items_completed}\n"

        if context.config.max_items:
            prompt += f"- Max Items: {context.config.max_items}\n"

        if context.initial_message:
            prompt += f"- Topic/Request: {context.initial_message}\n"

        return LlmMessage.system(prompt)

    def _get_combined_tools(self, server_tools: list[LlmToolDefinition] | None = None) -> list[LlmToolDefinition]:
        """Get combined list of client and server tools.

        Client tools are always included. Server tools are added if provided.

        Args:
            server_tools: Optional list of server-side tools

        Returns:
            Combined tool list for LLM
        """
        # Convert client tools to LlmToolDefinition format
        client_tools = []
        for ct in get_all_client_tools():
            client_tools.append(
                LlmToolDefinition(
                    name=ct.name,
                    description=ct.description,
                    parameters=ct.parameters,
                )
            )

        # Combine with server tools if provided
        all_tools = client_tools.copy()
        if server_tools:
            # Filter out any server tools that would conflict with client tool names
            for tool in server_tools:
                if tool.name not in CLIENT_TOOL_NAMES:
                    all_tools.append(tool)

        return all_tools

    async def start_session(self, context: ProactiveSessionContext) -> AsyncIterator[AgentEvent]:
        """Start a new proactive session.

        This initiates the proactive loop. The agent will generate content
        and may suspend when a client tool is called (widget needed).

        Args:
            context: The proactive session context

        Yields:
            Agent events as the session runs
        """
        self._session_context = context
        self._suspended_state = None

        # Create run context with session-specific setup
        run_context = AgentRunContext(
            user_message=context.initial_message or f"Start a {context.session_type.value} session.",
            conversation_history=[],
            tools=self._get_combined_tools(),
            metadata=context.metadata,
        )

        # Run the proactive loop
        async for event in self._proactive_loop(run_context, context):
            yield event

    async def resume_with_response(self, response: ClientResponse) -> AsyncIterator[AgentEvent]:
        """Resume a suspended session with a client response.

        Args:
            response: The client's response to the pending widget

        Yields:
            Agent events as the session continues

        Raises:
            AgentError: If not suspended or response doesn't match pending action
        """
        if not self._suspended_state:
            raise AgentError("Agent is not suspended", "invalid_state", is_retryable=False)

        if not self._session_context:
            raise AgentError("No session context", "invalid_state", is_retryable=False)

        # Validate response matches pending tool call
        pending = self._suspended_state.pending_tool_call
        if response.tool_call_id != pending.id:
            raise AgentError(
                f"Response tool_call_id {response.tool_call_id} doesn't match pending {pending.id}",
                "tool_call_mismatch",
                is_retryable=False,
            )

        # Validate and normalize the response
        validation = validate_response(pending.name, response.response)
        if not validation.is_valid:
            raise AgentError(
                f"Invalid response: {validation.error_message}",
                "invalid_response",
                is_retryable=True,
            )

        # Emit resume event
        yield AgentEvent(
            type=AgentEventType.RUN_RESUMED,
            data={
                "session_id": self._session_context.session_id,
                "tool_call_id": response.tool_call_id,
                "response": validation.normalized_value,
            },
        )

        # Create tool result message
        import json

        tool_result_content = json.dumps(validation.normalized_value)
        tool_result = LlmMessage.tool_result(
            tool_call_id=pending.id,
            tool_name=pending.name,
            content=tool_result_content,
        )

        # Restore state and add tool result
        messages = self._suspended_state.messages.copy()
        messages.append(tool_result)

        iteration = self._suspended_state.iteration
        tool_calls_made = self._suspended_state.tool_calls_made + 1
        start_time = self._suspended_state.start_time

        # Clear suspended state
        self._suspended_state = None

        # Continue the proactive loop
        run_context = AgentRunContext(
            user_message="",  # Not used in resume
            conversation_history=[],
            tools=self._get_combined_tools(),
            metadata=self._session_context.metadata,
        )

        async for event in self._continue_loop(run_context, self._session_context, messages, iteration, tool_calls_made, start_time):
            yield event

    async def _proactive_loop(
        self,
        context: AgentRunContext,
        session_context: ProactiveSessionContext,
    ) -> AsyncIterator[AgentEvent]:
        """Main proactive agent loop.

        Args:
            context: Run context with tools
            session_context: Session-specific context

        Yields:
            Agent events
        """
        start_time = time.time()
        tool_calls_made = 0

        # Emit run started
        yield AgentEvent(
            type=AgentEventType.RUN_STARTED,
            data={
                "session_id": session_context.session_id,
                "session_type": session_context.session_type.value,
                "tools_count": len(context.tools),
            },
        )

        # Build initial messages
        messages: list[LlmMessage] = [self._build_system_message_for_session(session_context)]

        # Add initial user message if provided
        if context.user_message:
            messages.append(LlmMessage.user(context.user_message))

        # Run the loop
        async for event in self._continue_loop(context, session_context, messages, 0, tool_calls_made, start_time):
            yield event

    async def _continue_loop(
        self,
        context: AgentRunContext,
        session_context: ProactiveSessionContext,
        messages: list[LlmMessage],
        start_iteration: int,
        tool_calls_made: int,
        start_time: float,
    ) -> AsyncIterator[AgentEvent]:
        """Continue the proactive loop from a given state.

        This is the core loop that handles LLM calls, tool detection,
        and client tool suspension.

        Args:
            context: Run context
            session_context: Session context
            messages: Current message history
            start_iteration: Starting iteration number
            tool_calls_made: Tool calls made so far
            start_time: Original start time

        Yields:
            Agent events
        """
        for iteration in range(start_iteration, self._config.max_iterations):
            current_iteration = iteration + 1

            # Emit iteration started
            yield AgentEvent(
                type=AgentEventType.ITERATION_STARTED,
                data={"iteration": current_iteration, "max_iterations": self._config.max_iterations},
                iteration=current_iteration,
            )

            # Emit LLM request started
            yield AgentEvent(
                type=AgentEventType.LLM_REQUEST_STARTED,
                data={"model": self._llm.model, "messages_count": len(messages)},
                iteration=current_iteration,
            )

            # Call LLM (streaming)
            assistant_content = ""
            tool_calls: list[LlmToolCall] = []
            assistant_msg_id = str(uuid4())

            try:
                if self._config.stream_responses:
                    async for chunk in self._llm.chat_stream(
                        messages=messages,
                        tools=context.tools if context.tools else None,
                    ):
                        if chunk.content:
                            assistant_content += chunk.content
                            yield AgentEvent(
                                type=AgentEventType.LLM_RESPONSE_CHUNK,
                                data={"content": chunk.content},
                                iteration=current_iteration,
                                message_id=assistant_msg_id,
                            )

                        if chunk.done:
                            if chunk.tool_calls:
                                tool_calls = chunk.tool_calls
                            break
                else:
                    # Non-streaming
                    response = await self._llm.chat(
                        messages=messages,
                        tools=context.tools if context.tools else None,
                    )
                    assistant_content = response.content
                    tool_calls = response.tool_calls or []

                    if assistant_content:
                        yield AgentEvent(
                            type=AgentEventType.LLM_RESPONSE_CHUNK,
                            data={"content": assistant_content},
                            iteration=current_iteration,
                            message_id=assistant_msg_id,
                        )

            except Exception as e:
                logger.error(f"LLM call failed: {e}")
                yield AgentEvent(
                    type=AgentEventType.RUN_FAILED,
                    data={
                        "error": str(e),
                        "iteration": current_iteration,
                        "total_time_ms": (time.time() - start_time) * 1000,
                    },
                )
                return

            # Add assistant message to history
            assistant_message = LlmMessage.assistant(
                content=assistant_content,
                tool_calls=tool_calls if tool_calls else None,
            )
            messages.append(assistant_message)

            # Emit LLM response completed
            yield AgentEvent(
                type=AgentEventType.LLM_RESPONSE_COMPLETED,
                data={
                    "content": assistant_content,
                    "has_tool_calls": bool(tool_calls),
                    "tool_calls_count": len(tool_calls),
                },
                iteration=current_iteration,
                message_id=assistant_msg_id,
            )

            # If no tool calls, session is complete
            if not tool_calls:
                yield AgentEvent(
                    type=AgentEventType.MESSAGE_ADDED,
                    data={
                        "message_id": assistant_msg_id,
                        "role": "assistant",
                        "content": assistant_content,
                    },
                    message_id=assistant_msg_id,
                )

                yield AgentEvent(
                    type=AgentEventType.ITERATION_COMPLETED,
                    data={"iteration": current_iteration, "finished": True},
                    iteration=current_iteration,
                )

                yield AgentEvent(
                    type=AgentEventType.RUN_COMPLETED,
                    data={
                        "success": True,
                        "response": assistant_content,
                        "tool_calls_made": tool_calls_made,
                        "iterations": current_iteration,
                        "total_time_ms": (time.time() - start_time) * 1000,
                        "session_id": session_context.session_id,
                    },
                )
                return

            # Process tool calls
            yield AgentEvent(
                type=AgentEventType.TOOL_CALLS_DETECTED,
                data={
                    "tool_calls": [{"id": tc.id, "name": tc.name, "arguments": tc.arguments} for tc in tool_calls],
                },
                iteration=current_iteration,
            )

            # Check for client tools (need to suspend)
            for tool_call in tool_calls:
                if is_client_tool(tool_call.name):
                    # This is a client tool - suspend and emit CLIENT_ACTION
                    widget_payload = extract_widget_payload(tool_call.name, tool_call.arguments)

                    # Create ClientAction for domain model
                    client_action = ClientAction(
                        tool_call_id=tool_call.id,
                        tool_name=tool_call.name,
                        widget_type=widget_payload.get("widget_type", "unknown"),
                        props=widget_payload,
                    )

                    # Save state for resume
                    self._suspended_state = SuspendedState(
                        messages=messages.copy(),
                        pending_tool_call=tool_call,
                        iteration=current_iteration,
                        tool_calls_made=tool_calls_made,
                        start_time=start_time,
                    )

                    # Emit client action event
                    yield AgentEvent(
                        type=AgentEventType.CLIENT_ACTION,
                        data={
                            "session_id": session_context.session_id,
                            "action": client_action.to_sse_payload(),
                        },
                        iteration=current_iteration,
                    )

                    # Emit suspended event
                    yield AgentEvent(
                        type=AgentEventType.RUN_SUSPENDED,
                        data={
                            "session_id": session_context.session_id,
                            "tool_call_id": tool_call.id,
                            "tool_name": tool_call.name,
                            "waiting_for": "client_response",
                        },
                        iteration=current_iteration,
                    )

                    # Exit loop - we're suspended
                    return

                else:
                    # Server-side tool - execute it
                    if context.tool_executor:
                        yield AgentEvent(
                            type=AgentEventType.TOOL_EXECUTION_STARTED,
                            data={
                                "call_id": tool_call.id,
                                "tool_name": tool_call.name,
                                "arguments": tool_call.arguments,
                            },
                            iteration=current_iteration,
                        )

                        request = ToolExecutionRequest(
                            call_id=tool_call.id,
                            tool_name=tool_call.name,
                            arguments=tool_call.arguments,
                        )

                        try:
                            async for result in context.tool_executor(request):
                                tool_calls_made += 1
                                messages.append(result.to_llm_message())

                                if result.success:
                                    yield AgentEvent(
                                        type=AgentEventType.TOOL_EXECUTION_COMPLETED,
                                        data={
                                            "call_id": result.call_id,
                                            "tool_name": result.tool_name,
                                            "result": result.result,
                                            "execution_time_ms": result.execution_time_ms,
                                        },
                                        iteration=current_iteration,
                                    )
                                else:
                                    yield AgentEvent(
                                        type=AgentEventType.TOOL_EXECUTION_FAILED,
                                        data={
                                            "call_id": result.call_id,
                                            "tool_name": result.tool_name,
                                            "error": result.error,
                                        },
                                        iteration=current_iteration,
                                    )
                                break  # One result per request

                        except Exception as e:
                            logger.error(f"Tool execution failed: {e}")
                            yield AgentEvent(
                                type=AgentEventType.TOOL_EXECUTION_FAILED,
                                data={
                                    "call_id": tool_call.id,
                                    "tool_name": tool_call.name,
                                    "error": str(e),
                                },
                                iteration=current_iteration,
                            )

            # Emit iteration completed
            yield AgentEvent(
                type=AgentEventType.ITERATION_COMPLETED,
                data={"iteration": current_iteration, "finished": False},
                iteration=current_iteration,
            )

        # Max iterations reached
        logger.warning(f"ProactiveAgent reached max iterations ({self._config.max_iterations})")
        yield AgentEvent(
            type=AgentEventType.RUN_COMPLETED,
            data={
                "success": True,
                "response": messages[-1].content if messages else "Session reached maximum iterations.",
                "tool_calls_made": tool_calls_made,
                "iterations": self._config.max_iterations,
                "total_time_ms": (time.time() - start_time) * 1000,
                "session_id": session_context.session_id,
                "max_iterations_reached": True,
            },
        )

    # ==========================================================================
    # Required Abstract Method Implementations
    # ==========================================================================

    async def run(self, context: AgentRunContext) -> AgentRunResult:
        """Run the agent (non-streaming).

        Note: For proactive agents, use start_session() instead.
        This method is provided for interface compatibility.

        Args:
            context: Run context

        Returns:
            Agent run result
        """
        start_time = time.time()
        messages: list[LlmMessage] = []
        final_response = ""
        tool_calls_made = 0
        iterations = 0

        try:
            # Collect all events
            async for event in self.run_stream(context):
                if event.type == AgentEventType.RUN_COMPLETED:
                    final_response = event.data.get("response", "")
                    tool_calls_made = event.data.get("tool_calls_made", 0)
                    iterations = event.data.get("iterations", 0)
                elif event.type == AgentEventType.RUN_SUSPENDED:
                    # Can't handle suspension in non-streaming mode
                    return AgentRunResult(
                        success=False,
                        response="",
                        messages=messages,
                        error=AgentError(
                            "Proactive agent suspended - use streaming mode with start_session()",
                            "suspension_not_supported",
                        ),
                    )

            return AgentRunResult(
                success=True,
                response=final_response,
                messages=messages,
                tool_calls_made=tool_calls_made,
                iterations=iterations,
                total_time_ms=(time.time() - start_time) * 1000,
            )

        except Exception as e:
            return AgentRunResult(
                success=False,
                response="",
                messages=messages,
                error=AgentError(str(e), "execution_error"),
                total_time_ms=(time.time() - start_time) * 1000,
            )

    async def run_stream(self, context: AgentRunContext) -> AsyncIterator[AgentEvent]:
        """Run the agent with streaming (basic mode).

        Note: For proactive agents, use start_session() instead.
        This method is provided for interface compatibility and behaves
        like a basic reactive agent.

        Args:
            context: Run context

        Yields:
            Agent events
        """
        # Create a minimal session context
        session_context = ProactiveSessionContext(
            session_id=str(uuid4()),
            session_type=SessionType.THOUGHT,
            config=SessionConfig(),
            conversation_id=str(uuid4()),
            initial_message=context.user_message,
        )

        async for event in self._proactive_loop(context, session_context):
            yield event
