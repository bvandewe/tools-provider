"""Agent abstractions for Agent Host.

This package contains:
- Agent base class and configuration
- LLM provider abstractions
- ReAct agent implementation
- Client tools for UI widgets
"""

from application.agents.agent_config import AgentConfig
from application.agents.base_agent import Agent, AgentError, AgentEvent, AgentEventType, AgentRunContext, AgentRunResult, ToolExecutionRequest, ToolExecutionResult, ToolExecutor
from application.agents.client_tools import (
    CLIENT_TOOL_NAMES,
    ClientToolDefinition,
    ClientToolName,
    ResponseValidationResult,
    WidgetType,
    extract_widget_payload,
    get_all_client_tools,
    get_client_tool,
    get_client_tool_manifest,
    get_widget_type_for_tool,
    is_client_tool,
    validate_response,
)
from application.agents.llm_provider import (
    LlmConfig,
    LlmMessage,
    LlmMessageRole,
    LlmProvider,
    LlmProviderError,
    LlmProviderType,
    LlmResponse,
    LlmStreamChunk,
    LlmToolCall,
    LlmToolDefinition,
    ModelDefinition,
)
from application.agents.react_agent import ReActAgent

__all__ = [
    # Agent
    "Agent",
    "AgentConfig",
    "AgentError",
    "AgentEvent",
    "AgentEventType",
    "AgentRunContext",
    "AgentRunResult",
    "ReActAgent",
    "ToolExecutionRequest",
    "ToolExecutionResult",
    "ToolExecutor",
    # Client Tools
    "ClientToolDefinition",
    "ClientToolName",
    "WidgetType",
    "ResponseValidationResult",
    "CLIENT_TOOL_NAMES",
    "is_client_tool",
    "get_client_tool",
    "get_widget_type_for_tool",
    "get_client_tool_manifest",
    "get_all_client_tools",
    "validate_response",
    "extract_widget_payload",
    # LLM Provider
    "LlmProvider",
    "LlmProviderError",
    "LlmProviderType",
    "LlmConfig",
    "LlmMessage",
    "LlmMessageRole",
    "LlmResponse",
    "LlmStreamChunk",
    "LlmToolCall",
    "LlmToolDefinition",
    "ModelDefinition",
]
