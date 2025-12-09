"""Agent configuration for Agent Host.

This module defines the configuration dataclass for agents, including
LLM settings, tool configuration, and behavioral parameters.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentConfig:
    """Configuration for an Agent.

    This configuration controls the agent's behavior, including which LLM to use,
    what system prompt to apply, and how to handle tool calling.

    Attributes:
        name: Human-readable name for the agent
        system_prompt: The system prompt that defines the agent's persona and instructions
        max_iterations: Maximum number of LLM calls in a single run (prevents infinite loops)
        max_tool_calls_per_iteration: Maximum tool calls per LLM response
        tool_choice: How to handle tool calling ("auto", "none", "required")
        include_tool_results_in_response: Whether to include tool results in final response
        stream_responses: Whether to stream LLM responses
        stop_on_error: Whether to stop execution on tool errors
        retry_on_error: Whether to retry failed tool calls
        max_retries: Maximum retries for failed tool calls
        timeout_seconds: Overall timeout for agent run
        metadata: Additional metadata for the agent
    """

    # Identity
    name: str = "assistant"

    # System prompt - defines the agent's behavior
    system_prompt: str = """You are a helpful AI assistant with access to various tools.
When the user asks you to perform an action, analyze if any available tools can help.
If a tool is needed, call it using the function calling format.
Always explain what you're doing and present tool results in a user-friendly way.
Be concise but informative in your responses."""

    # Iteration limits (safety bounds)
    max_iterations: int = 10
    max_tool_calls_per_iteration: int = 5

    # Tool calling behavior
    tool_choice: str = "auto"  # "auto", "none", "required"
    include_tool_results_in_response: bool = True

    # Tool filtering (optional)
    tool_whitelist: list[str] | None = None  # Only allow these tools (None = allow all)
    tool_blacklist: list[str] | None = None  # Exclude these tools (None = exclude none)

    # Response handling
    stream_responses: bool = True

    # Error handling
    stop_on_error: bool = False
    retry_on_error: bool = True
    max_retries: int = 2

    # Timeouts
    timeout_seconds: float = 300.0  # 5 minutes overall timeout

    # Extensibility
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_system_prompt(self, system_prompt: str) -> "AgentConfig":
        """Create a copy with a different system prompt.

        Args:
            system_prompt: New system prompt

        Returns:
            New AgentConfig instance
        """
        return AgentConfig(
            name=self.name,
            system_prompt=system_prompt,
            max_iterations=self.max_iterations,
            max_tool_calls_per_iteration=self.max_tool_calls_per_iteration,
            tool_choice=self.tool_choice,
            include_tool_results_in_response=self.include_tool_results_in_response,
            tool_whitelist=self.tool_whitelist,
            tool_blacklist=self.tool_blacklist,
            stream_responses=self.stream_responses,
            stop_on_error=self.stop_on_error,
            retry_on_error=self.retry_on_error,
            max_retries=self.max_retries,
            timeout_seconds=self.timeout_seconds,
            metadata=self.metadata.copy(),
        )

    def with_max_iterations(self, max_iterations: int) -> "AgentConfig":
        """Create a copy with different max iterations.

        Args:
            max_iterations: New max iterations

        Returns:
            New AgentConfig instance
        """
        return AgentConfig(
            name=self.name,
            system_prompt=self.system_prompt,
            max_iterations=max_iterations,
            max_tool_calls_per_iteration=self.max_tool_calls_per_iteration,
            tool_choice=self.tool_choice,
            include_tool_results_in_response=self.include_tool_results_in_response,
            tool_whitelist=self.tool_whitelist,
            tool_blacklist=self.tool_blacklist,
            stream_responses=self.stream_responses,
            stop_on_error=self.stop_on_error,
            retry_on_error=self.retry_on_error,
            max_retries=self.max_retries,
            timeout_seconds=self.timeout_seconds,
            metadata=self.metadata.copy(),
        )

    @classmethod
    def default(cls) -> "AgentConfig":
        """Create a default agent configuration."""
        return cls()

    @classmethod
    def minimal(cls) -> "AgentConfig":
        """Create a minimal agent configuration (no tools, single iteration)."""
        return cls(
            name="minimal",
            system_prompt="You are a helpful assistant.",
            max_iterations=1,
            tool_choice="none",
            stream_responses=False,
        )
