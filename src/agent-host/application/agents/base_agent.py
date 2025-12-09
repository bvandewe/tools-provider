"""Base Agent abstraction for Agent Host.

This module defines the abstract Agent interface and associated types
for building agentic AI systems with tool calling capabilities.

Design Principles:
- Interface-based design for different agent implementations
- Event-driven communication for streaming and observability
- Clean separation between agent logic and infrastructure
- Support for both streaming and non-streaming execution
"""

import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from application.agents.agent_config import AgentConfig
from application.agents.llm_provider import LlmMessage, LlmProvider, LlmToolDefinition

logger = logging.getLogger(__name__)


class AgentEventType(str, Enum):
    """Types of events emitted by an agent during execution."""

    # Lifecycle events
    RUN_STARTED = "run_started"
    RUN_COMPLETED = "run_completed"
    RUN_FAILED = "run_failed"

    # Iteration events
    ITERATION_STARTED = "iteration_started"
    ITERATION_COMPLETED = "iteration_completed"

    # LLM events
    LLM_REQUEST_STARTED = "llm_request_started"
    LLM_RESPONSE_CHUNK = "llm_response_chunk"
    LLM_RESPONSE_COMPLETED = "llm_response_completed"

    # Tool events
    TOOL_CALLS_DETECTED = "tool_calls_detected"
    TOOL_EXECUTION_STARTED = "tool_execution_started"
    TOOL_EXECUTION_COMPLETED = "tool_execution_completed"
    TOOL_EXECUTION_FAILED = "tool_execution_failed"

    # Message events
    MESSAGE_ADDED = "message_added"


@dataclass
class AgentEvent:
    """An event emitted by an agent during execution.

    Events provide a stream of information about what the agent is doing,
    enabling real-time UI updates and observability.

    Attributes:
        type: Type of the event
        data: Event-specific data payload
        timestamp: When the event occurred
        iteration: Current iteration number (if applicable)
        message_id: Related message ID (if applicable)
    """

    type: AgentEventType
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    iteration: int | None = None
    message_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "event": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "iteration": self.iteration,
            "message_id": self.message_id,
        }


@dataclass
class ToolExecutionRequest:
    """A request to execute a tool.

    Attributes:
        call_id: Unique identifier for this tool call
        tool_name: Name of the tool to execute
        arguments: Arguments to pass to the tool
    """

    call_id: str
    tool_name: str
    arguments: dict[str, Any]


@dataclass
class ToolExecutionResult:
    """Result of a tool execution.

    Attributes:
        call_id: ID of the tool call this result is for
        tool_name: Name of the executed tool
        success: Whether execution succeeded
        result: Result data (on success)
        error: Error message (on failure)
        execution_time_ms: Execution time in milliseconds
    """

    call_id: str
    tool_name: str
    success: bool
    result: Any | None = None
    error: str | None = None
    execution_time_ms: float = 0.0

    def to_llm_message(self) -> LlmMessage:
        """Convert to an LLM message for the conversation."""
        if self.success:
            import json

            content = json.dumps(self.result) if not isinstance(self.result, str) else self.result
        else:
            content = f"Error: {self.error}"

        return LlmMessage.tool_result(
            tool_call_id=self.call_id,
            tool_name=self.tool_name,
            content=content,
        )


class AgentError(Exception):
    """Error during agent execution.

    Attributes:
        message: Human-readable error message
        error_code: Categorized error code
        is_retryable: Whether the operation might succeed on retry
        details: Additional error details
    """

    def __init__(
        self,
        message: str,
        error_code: str = "agent_error",
        is_retryable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.is_retryable = is_retryable
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "message": self.message,
            "error_code": self.error_code,
            "is_retryable": self.is_retryable,
            "details": self.details,
        }


# Type alias for tool executor function
ToolExecutor = Callable[[ToolExecutionRequest], "AsyncIterator[ToolExecutionResult]"]


@dataclass
class AgentRunContext:
    """Context for an agent run.

    Contains all the information needed for an agent to process a user request,
    including conversation history, available tools, and execution parameters.

    Attributes:
        user_message: The user's input message
        conversation_history: Previous messages in the conversation
        tools: Available tool definitions
        tool_executor: Function to execute tool calls
        access_token: User's access token (for tool execution auth)
        metadata: Additional context metadata
    """

    user_message: str
    conversation_history: list[LlmMessage] = field(default_factory=list)
    tools: list[LlmToolDefinition] = field(default_factory=list)
    tool_executor: Callable[[ToolExecutionRequest], "AsyncIterator[ToolExecutionResult]"] | None = None
    access_token: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentRunResult:
    """Result of an agent run.

    Attributes:
        success: Whether the run completed successfully
        response: The agent's final response text
        messages: All messages generated during the run
        tool_calls_made: Number of tool calls executed
        iterations: Number of LLM iterations
        total_time_ms: Total execution time in milliseconds
        error: Error details (if failed)
    """

    success: bool
    response: str
    messages: list[LlmMessage] = field(default_factory=list)
    tool_calls_made: int = 0
    iterations: int = 0
    total_time_ms: float = 0.0
    error: AgentError | None = None


class Agent(ABC):
    """Abstract base class for AI agents.

    An Agent orchestrates the interaction between a user, an LLM, and tools
    to accomplish tasks. Different implementations can use different strategies
    (ReAct, function calling, chain-of-thought, etc.).

    Key Responsibilities:
    - Managing conversation context
    - Calling the LLM with appropriate prompts
    - Detecting and executing tool calls
    - Handling errors and retries
    - Emitting events for observability

    Implementations:
    - ReActAgent: ReAct-style reasoning with tool use
    - (Future) PlanningAgent: Plan-then-execute approach
    - (Future) RouterAgent: Routes to specialized sub-agents

    Usage:
        agent = ReActAgent(llm_provider, config)
        async for event in agent.run_stream(context):
            handle_event(event)
    """

    def __init__(
        self,
        llm_provider: LlmProvider,
        config: AgentConfig | None = None,
    ) -> None:
        """Initialize the agent.

        Args:
            llm_provider: The LLM provider to use for inference
            config: Agent configuration (uses defaults if None)
        """
        self._llm = llm_provider
        self._config = config or AgentConfig.default()

    @property
    def config(self) -> AgentConfig:
        """Get the agent configuration."""
        return self._config

    @property
    def llm(self) -> LlmProvider:
        """Get the LLM provider."""
        return self._llm

    @abstractmethod
    async def run(self, context: AgentRunContext) -> AgentRunResult:
        """Run the agent on a user request.

        This is the non-streaming version that returns the final result.

        Args:
            context: The run context including user message, history, and tools

        Returns:
            The result of the agent run
        """
        pass

    @abstractmethod
    def run_stream(self, context: AgentRunContext) -> AsyncIterator[AgentEvent]:
        """Run the agent on a user request with streaming events.

        This method is an async generator - implementations should use
        `async def` with `yield` statements.

        Args:
            context: The run context including user message, history, and tools

        Yields:
            Events as the agent executes
        """
        # This is typed as returning AsyncIterator but implementations
        # should be async generators (async def with yield)
        raise NotImplementedError

    def _build_system_message(self) -> LlmMessage:
        """Build the system message from configuration.

        Returns:
            The system message for the LLM
        """
        return LlmMessage.system(self._config.system_prompt)

    def _build_messages(
        self,
        context: AgentRunContext,
        include_system: bool = True,
    ) -> list[LlmMessage]:
        """Build the message list for LLM call.

        Args:
            context: The run context
            include_system: Whether to include the system message

        Returns:
            List of messages for the LLM
        """
        messages = []

        if include_system:
            messages.append(self._build_system_message())

        # Add conversation history
        messages.extend(context.conversation_history)

        # Add user message
        messages.append(LlmMessage.user(context.user_message))

        return messages
