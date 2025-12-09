"""LLM Provider abstraction for Agent Host.

This module defines the abstract interface for LLM providers, allowing
the agent to work with different LLM backends (Ollama, OpenAI, Anthropic, etc.)
without coupling to a specific implementation.

Design Principles:
- Interface-based design for swappable LLM backends
- Dataclasses for configuration and message structures
- Support for both streaming and non-streaming responses
- Tool/function calling support as first-class citizen
- Unified error handling across providers
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Provider Enumeration
# =============================================================================


class LlmProviderType(str, Enum):
    """Supported LLM provider types."""

    OLLAMA = "ollama"
    OPENAI = "openai"


# =============================================================================
# Unified Error Handling
# =============================================================================


class LlmProviderError(Exception):
    """Base error class for all LLM provider errors.

    This provides a unified error structure across all providers (Ollama, OpenAI, etc.)
    with user-friendly messages and error categorization.

    Attributes:
        message: Human-readable error message
        error_code: Categorized error code for programmatic handling
        provider: The provider that raised the error (ollama, openai, etc.)
        is_retryable: Whether the operation might succeed on retry
        details: Additional error context
    """

    def __init__(
        self,
        message: str,
        error_code: str,
        provider: str,
        is_retryable: bool = False,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.provider = provider
        self.is_retryable = is_retryable
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "message": self.message,
            "error_code": self.error_code,
            "provider": self.provider,
            "is_retryable": self.is_retryable,
            "details": self.details,
        }

    def __repr__(self) -> str:
        return f"LlmProviderError({self.provider}:{self.error_code}: {self.message})"


# =============================================================================
# Model Definition
# =============================================================================


@dataclass
class ModelDefinition:
    """Definition of an available LLM model.

    This provides a typed, structured representation of model options
    replacing the previous pipe-delimited string format.

    Attributes:
        provider: The provider type (ollama, openai)
        id: Model identifier (e.g., "llama3.2:3b", "gpt-4o")
        name: User-friendly display name
        description: Brief description of model capabilities
        is_default: Whether this is the default model for its provider
    """

    provider: LlmProviderType
    id: str
    name: str
    description: str = ""
    is_default: bool = False

    @property
    def qualified_id(self) -> str:
        """Get the fully qualified model ID with provider prefix.

        Returns:
            e.g., "ollama:llama3.2:3b" or "openai:gpt-4o"
        """
        return f"{self.provider.value}:{self.id}"

    @classmethod
    def from_qualified_id(cls, qualified_id: str, name: str = "", description: str = "") -> "ModelDefinition":
        """Create from a qualified ID string.

        The method handles both qualified IDs (with provider prefix) and
        unqualified IDs (model only). For Ollama models that contain colons
        (like "llama3.2:3b"), the method checks if the first part is a known
        provider before splitting.

        Args:
            qualified_id: Format "provider:model_id" (e.g., "openai:gpt-4o") or
                         just "model_id" (e.g., "llama3.2:3b" defaults to ollama)
            name: Display name (defaults to model_id)
            description: Model description

        Returns:
            ModelDefinition instance
        """
        provider = LlmProviderType.OLLAMA
        model_id = qualified_id

        if ":" in qualified_id:
            parts = qualified_id.split(":", 1)
            potential_provider = parts[0].lower()

            # Only treat as provider prefix if it's a known provider
            if potential_provider in [p.value for p in LlmProviderType]:
                try:
                    provider = LlmProviderType(potential_provider)
                    model_id = parts[1]
                except ValueError:
                    # Not a valid provider, keep full string as model_id
                    pass

        return cls(
            provider=provider,
            id=model_id,
            name=name or model_id,
            description=description,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "provider": self.provider.value,
            "id": self.id,
            "qualified_id": self.qualified_id,
            "name": self.name,
            "description": self.description,
            "is_default": self.is_default,
        }


class LlmMessageRole(str, Enum):
    """Role of a message in the LLM conversation."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class LlmToolCall:
    """A tool call requested by the LLM.

    Attributes:
        id: Unique identifier for this tool call (for matching with results)
        name: Name of the tool to call
        arguments: Arguments to pass to the tool (as dict)
    """

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LlmMessage:
    """A message in the LLM conversation.

    Attributes:
        role: Role of the message sender
        content: Text content of the message
        name: Optional name (used for tool results)
        tool_calls: Optional list of tool calls (for assistant messages)
        tool_call_id: Optional ID linking to a tool call (for tool result messages)
    """

    role: LlmMessageRole
    content: str
    name: Optional[str] = None
    tool_calls: Optional[list[LlmToolCall]] = None
    tool_call_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format for LLM API."""
        result: dict[str, Any] = {
            "role": self.role.value,
            "content": self.content,
        }
        if self.name:
            result["name"] = self.name
        if self.tool_calls:
            result["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": tc.arguments,
                    },
                }
                for tc in self.tool_calls
            ]
        if self.tool_call_id:
            result["tool_call_id"] = self.tool_call_id
        return result

    @classmethod
    def system(cls, content: str) -> "LlmMessage":
        """Create a system message."""
        return cls(role=LlmMessageRole.SYSTEM, content=content)

    @classmethod
    def user(cls, content: str) -> "LlmMessage":
        """Create a user message."""
        return cls(role=LlmMessageRole.USER, content=content)

    @classmethod
    def assistant(
        cls,
        content: str,
        tool_calls: Optional[list[LlmToolCall]] = None,
    ) -> "LlmMessage":
        """Create an assistant message."""
        return cls(role=LlmMessageRole.ASSISTANT, content=content, tool_calls=tool_calls)

    @classmethod
    def tool_result(
        cls,
        tool_call_id: str,
        tool_name: str,
        content: str,
    ) -> "LlmMessage":
        """Create a tool result message."""
        return cls(
            role=LlmMessageRole.TOOL,
            content=content,
            name=tool_name,
            tool_call_id=tool_call_id,
        )


@dataclass
class LlmResponse:
    """Response from an LLM.

    Attributes:
        content: Text content of the response
        tool_calls: Optional list of tool calls requested
        finish_reason: Why the response ended (stop, tool_calls, length, etc.)
        usage: Optional token usage statistics
    """

    content: str
    tool_calls: Optional[list[LlmToolCall]] = None
    finish_reason: str = "stop"
    usage: Optional[dict[str, int]] = None

    @property
    def has_tool_calls(self) -> bool:
        """Check if response contains tool calls."""
        return bool(self.tool_calls)


@dataclass
class LlmStreamChunk:
    """A chunk from a streaming LLM response.

    Attributes:
        content: Text content delta
        tool_calls: Partial tool call information (accumulated)
        done: Whether this is the final chunk
        finish_reason: Why the response ended (only on final chunk)
    """

    content: str = ""
    tool_calls: Optional[list[LlmToolCall]] = None
    done: bool = False
    finish_reason: Optional[str] = None


@dataclass
class LlmToolDefinition:
    """Definition of a tool that can be called by the LLM.

    This is a provider-agnostic representation that each LLM provider
    converts to its specific format.

    Attributes:
        name: Unique name of the tool
        description: Human-readable description of what the tool does
        parameters: JSON Schema defining the tool's parameters
    """

    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)

    def to_openai_format(self) -> dict[str, Any]:
        """Convert to OpenAI function calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def to_ollama_format(self) -> dict[str, Any]:
        """Convert to Ollama function calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


@dataclass
class LlmConfig:
    """Configuration for an LLM provider.

    Attributes:
        model: Model identifier (e.g., "llama3.2:3b", "gpt-4", "claude-3-opus")
        temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)
        top_p: Top-p (nucleus) sampling parameter
        max_tokens: Maximum tokens to generate (None = model default)
        timeout: Request timeout in seconds
        base_url: Base URL for the API (if applicable)
        api_key: API key (if applicable)
        extra: Provider-specific extra configuration
    """

    model: str
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: Optional[int] = None
    timeout: float = 120.0
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    extra: dict[str, Any] = field(default_factory=dict)


class LlmProvider(ABC):
    """Abstract base class for LLM providers.

    This interface defines the contract that all LLM provider implementations
    must follow. It supports both streaming and non-streaming chat completions,
    as well as tool/function calling.

    Implementations:
    - OllamaLlmProvider: For local Ollama deployments (development)
    - OpenAiLlmProvider: For OpenAI API (production option)
    - (Future) AnthropicLlmProvider, AzureOpenAiLlmProvider, etc.

    Usage:
        provider = OllamaLlmProvider(config)
        messages = [LlmMessage.system("You are helpful.")]
        response = await provider.chat(messages, tools=my_tools)
    """

    def __init__(self, config: LlmConfig) -> None:
        """Initialize the LLM provider.

        Args:
            config: Provider configuration
        """
        self._config = config
        self._model_override: Optional[str] = None

    @property
    @abstractmethod
    def provider_type(self) -> LlmProviderType:
        """Get the provider type identifier."""
        pass

    @property
    def config(self) -> LlmConfig:
        """Get the provider configuration."""
        return self._config

    @property
    def model(self) -> str:
        """Get the model identifier."""
        return self._config.model

    @property
    def current_model(self) -> str:
        """Get the current model (with override if set)."""
        return self._model_override or self._config.model

    def set_model_override(self, model: Optional[str]) -> None:
        """Set a temporary model override for subsequent calls.

        Args:
            model: Model name to use, or None to clear override
        """
        self._model_override = model
        if model:
            logger.info(f"Model override set to: {model}")
        else:
            logger.debug("Model override cleared")

    @abstractmethod
    async def chat(
        self,
        messages: list[LlmMessage],
        tools: Optional[list[LlmToolDefinition]] = None,
    ) -> LlmResponse:
        """Send a chat completion request.

        Args:
            messages: Conversation messages
            tools: Optional list of available tools

        Returns:
            Complete response from the LLM
        """
        pass

    @abstractmethod
    def chat_stream(
        self,
        messages: list[LlmMessage],
        tools: Optional[list[LlmToolDefinition]] = None,
    ) -> AsyncIterator[LlmStreamChunk]:
        """Send a streaming chat completion request.

        This method is an async generator - implementations should use
        `async def` with `yield` statements.

        Args:
            messages: Conversation messages
            tools: Optional list of available tools

        Yields:
            Streaming chunks from the LLM
        """
        # This is typed as returning AsyncIterator but implementations
        # should be async generators (async def with yield)
        raise NotImplementedError

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the LLM provider is available.

        Returns:
            True if healthy, False otherwise
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close any resources held by the provider."""
        pass

    async def __aenter__(self) -> "LlmProvider":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
