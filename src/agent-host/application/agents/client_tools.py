"""Client Tool Registry for Proactive Agent.

This module defines the client-side tools that trigger UI widgets instead of
server-side execution. Client tools are intercepted by the agent and cause
the agent loop to suspend, waiting for user response via the UI.

Client Tools:
- present_choices: Multiple choice widget
- request_free_text: Free text input widget
- present_code_editor: Code editor widget (Monaco)

Design Principles:
- Tool definitions match OpenAI function calling format
- Response validation is lenient (accept & normalize)
- Each tool maps to exactly one UI widget type
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ClientToolName(str, Enum):
    """Names of available client-side tools."""

    PRESENT_CHOICES = "present_choices"
    REQUEST_FREE_TEXT = "request_free_text"
    PRESENT_CODE_EDITOR = "present_code_editor"


class WidgetType(str, Enum):
    """UI widget types corresponding to client tools."""

    MULTIPLE_CHOICE = "multiple_choice"
    FREE_TEXT = "free_text"
    CODE_EDITOR = "code_editor"


# Mapping from tool name to widget type
TOOL_TO_WIDGET: dict[ClientToolName, WidgetType] = {
    ClientToolName.PRESENT_CHOICES: WidgetType.MULTIPLE_CHOICE,
    ClientToolName.REQUEST_FREE_TEXT: WidgetType.FREE_TEXT,
    ClientToolName.PRESENT_CODE_EDITOR: WidgetType.CODE_EDITOR,
}


@dataclass(frozen=True)
class ClientToolDefinition:
    """Definition of a client-side tool.

    Follows the OpenAI function calling format for compatibility
    with various LLM providers.

    Attributes:
        name: Unique tool name
        description: Human-readable description for the LLM
        parameters: JSON Schema for tool parameters
        widget_type: Corresponding UI widget type
        response_schema: JSON Schema for expected response format
    """

    name: str
    description: str
    parameters: dict[str, Any]
    widget_type: WidgetType
    response_schema: dict[str, Any] = field(default_factory=dict)

    def to_llm_format(self) -> dict[str, Any]:
        """Convert to LLM tool calling format (OpenAI compatible).

        Returns:
            Tool definition in OpenAI function format
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


@dataclass
class ResponseValidationResult:
    """Result of validating a client response.

    Attributes:
        is_valid: Whether the response is valid
        normalized_value: The normalized/cleaned response value
        error_message: Human-readable error (if invalid)
        validation_details: Additional validation info
    """

    is_valid: bool
    normalized_value: Any = None
    error_message: str | None = None
    validation_details: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Client Tool Definitions
# =============================================================================

PRESENT_CHOICES_TOOL = ClientToolDefinition(
    name=ClientToolName.PRESENT_CHOICES.value,
    description="""Present a multiple choice question to the user with 2-6 options.
The user will select exactly one option. Use this when you need the user to
choose between discrete alternatives. Each option should be clear and distinct.""",
    parameters={
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "The question or prompt to display to the user",
            },
            "options": {
                "type": "array",
                "description": "List of 2-6 choices for the user to select from",
                "items": {"type": "string"},
                "minItems": 2,
                "maxItems": 6,
            },
            "context": {
                "type": "string",
                "description": "Optional additional context or explanation",
            },
        },
        "required": ["prompt", "options"],
    },
    widget_type=WidgetType.MULTIPLE_CHOICE,
    response_schema={
        "type": "object",
        "properties": {
            "selection": {"type": "string", "description": "The selected option text"},
            "index": {"type": "integer", "description": "Zero-based index of selection"},
        },
        "required": ["selection", "index"],
    },
)

REQUEST_FREE_TEXT_TOOL = ClientToolDefinition(
    name=ClientToolName.REQUEST_FREE_TEXT.value,
    description="""Request free-form text input from the user. Use this when you need
the user to provide a written response, explanation, or any text that doesn't fit
predefined options. You can optionally specify min/max length constraints.""",
    parameters={
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "The prompt or question asking for user input",
            },
            "placeholder": {
                "type": "string",
                "description": "Optional placeholder text for the input field",
            },
            "min_length": {
                "type": "integer",
                "description": "Minimum character length (default: 1)",
                "default": 1,
            },
            "max_length": {
                "type": "integer",
                "description": "Maximum character length (default: 2000)",
                "default": 2000,
            },
            "multiline": {
                "type": "boolean",
                "description": "Whether to show a multiline textarea (default: true)",
                "default": True,
            },
        },
        "required": ["prompt"],
    },
    widget_type=WidgetType.FREE_TEXT,
    response_schema={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "The user's text input"},
        },
        "required": ["text"],
    },
)

PRESENT_CODE_EDITOR_TOOL = ClientToolDefinition(
    name=ClientToolName.PRESENT_CODE_EDITOR.value,
    description="""Present a code editor to the user for writing or editing code.
Use this when you need the user to provide code, solve a programming challenge,
or modify existing code. Supports syntax highlighting for multiple languages.""",
    parameters={
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Instructions or the coding challenge description",
            },
            "language": {
                "type": "string",
                "description": "Programming language for syntax highlighting",
                "enum": ["python", "javascript", "typescript", "java", "cpp", "c", "go", "rust", "sql", "json", "yaml", "markdown", "text"],
                "default": "python",
            },
            "initial_code": {
                "type": "string",
                "description": "Optional starter code to pre-populate the editor",
            },
            "read_only_lines": {
                "type": "array",
                "description": "Optional line numbers (1-indexed) that should be read-only",
                "items": {"type": "integer"},
            },
        },
        "required": ["prompt"],
    },
    widget_type=WidgetType.CODE_EDITOR,
    response_schema={
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "The user's code submission"},
        },
        "required": ["code"],
    },
)


# =============================================================================
# Client Tool Registry
# =============================================================================

# All client tools in a registry
CLIENT_TOOLS: dict[str, ClientToolDefinition] = {
    PRESENT_CHOICES_TOOL.name: PRESENT_CHOICES_TOOL,
    REQUEST_FREE_TEXT_TOOL.name: REQUEST_FREE_TEXT_TOOL,
    PRESENT_CODE_EDITOR_TOOL.name: PRESENT_CODE_EDITOR_TOOL,
}

# Set of client tool names for quick lookup
CLIENT_TOOL_NAMES: set[str] = set(CLIENT_TOOLS.keys())


# =============================================================================
# Helper Functions
# =============================================================================


def is_client_tool(tool_name: str) -> bool:
    """Check if a tool name is a client-side tool.

    Args:
        tool_name: Name of the tool to check

    Returns:
        True if tool is a client-side tool, False otherwise
    """
    return tool_name in CLIENT_TOOL_NAMES


def get_client_tool(tool_name: str) -> ClientToolDefinition | None:
    """Get a client tool definition by name.

    Args:
        tool_name: Name of the tool to retrieve

    Returns:
        Tool definition or None if not found
    """
    return CLIENT_TOOLS.get(tool_name)


def get_widget_type_for_tool(tool_name: str) -> WidgetType | None:
    """Get the widget type for a client tool.

    Args:
        tool_name: Name of the client tool

    Returns:
        Widget type or None if tool not found
    """
    tool = get_client_tool(tool_name)
    return tool.widget_type if tool else None


def get_client_tool_manifest() -> list[dict[str, Any]]:
    """Get all client tool definitions in LLM-compatible format.

    This returns the tool definitions that should be provided to the LLM
    when running a proactive session.

    Returns:
        List of tool definitions in OpenAI function calling format
    """
    return [tool.to_llm_format() for tool in CLIENT_TOOLS.values()]


def get_all_client_tools() -> list[ClientToolDefinition]:
    """Get all client tool definitions.

    Returns:
        List of all client tool definitions
    """
    return list(CLIENT_TOOLS.values())


# =============================================================================
# Response Validation
# =============================================================================


def validate_response(tool_name: str, response_data: dict[str, Any]) -> ResponseValidationResult:
    """Validate and normalize a client response.

    This function is intentionally lenient - it tries to accept and normalize
    responses even if they don't perfectly match the expected schema. This
    provides a better user experience.

    Args:
        tool_name: Name of the tool the response is for
        response_data: Raw response data from the client

    Returns:
        Validation result with normalized value or error
    """
    tool = get_client_tool(tool_name)
    if not tool:
        return ResponseValidationResult(
            is_valid=False,
            error_message=f"Unknown tool: {tool_name}",
        )

    if tool_name == ClientToolName.PRESENT_CHOICES.value:
        return _validate_choice_response(response_data)
    elif tool_name == ClientToolName.REQUEST_FREE_TEXT.value:
        return _validate_free_text_response(response_data)
    elif tool_name == ClientToolName.PRESENT_CODE_EDITOR.value:
        return _validate_code_response(response_data)
    else:
        # Unknown tool type - be lenient
        return ResponseValidationResult(
            is_valid=True,
            normalized_value=response_data,
            validation_details={"note": "Unknown tool type, accepted as-is"},
        )


def _validate_choice_response(response_data: dict[str, Any]) -> ResponseValidationResult:
    """Validate a multiple choice response.

    Expected format: {"selection": "...", "index": N}
    Also accepts: {"selection": "..."} or {"index": N}
    """
    selection = response_data.get("selection")
    index = response_data.get("index")

    # Need at least one of selection or index
    if selection is None and index is None:
        return ResponseValidationResult(
            is_valid=False,
            error_message="Choice response must include 'selection' or 'index'",
        )

    # Normalize index to int if present
    if index is not None:
        try:
            index = int(index)
        except (TypeError, ValueError):
            return ResponseValidationResult(
                is_valid=False,
                error_message=f"Invalid index value: {index}",
            )

    return ResponseValidationResult(
        is_valid=True,
        normalized_value={
            "selection": str(selection) if selection is not None else None,
            "index": index,
        },
    )


def _validate_free_text_response(response_data: dict[str, Any]) -> ResponseValidationResult:
    """Validate a free text response.

    Expected format: {"text": "..."}
    """
    text = response_data.get("text")

    if text is None:
        # Try to find text in other common keys
        text = response_data.get("value") or response_data.get("input") or response_data.get("content")

    if text is None:
        return ResponseValidationResult(
            is_valid=False,
            error_message="Free text response must include 'text'",
        )

    # Accept any string, even empty (validation of min/max happens elsewhere)
    return ResponseValidationResult(
        is_valid=True,
        normalized_value={"text": str(text)},
    )


def _validate_code_response(response_data: dict[str, Any]) -> ResponseValidationResult:
    """Validate a code editor response.

    Expected format: {"code": "..."}
    """
    code = response_data.get("code")

    if code is None:
        # Try to find code in other common keys
        code = response_data.get("content") or response_data.get("text") or response_data.get("source")

    if code is None:
        return ResponseValidationResult(
            is_valid=False,
            error_message="Code response must include 'code'",
        )

    return ResponseValidationResult(
        is_valid=True,
        normalized_value={"code": str(code)},
    )


# =============================================================================
# Tool Call Argument Extraction
# =============================================================================


def extract_widget_payload(tool_name: str, tool_arguments: dict[str, Any]) -> dict[str, Any]:
    """Extract and format the widget payload from tool call arguments.

    Transforms the tool call arguments into a payload suitable for the
    client_action SSE event.

    Args:
        tool_name: Name of the client tool
        tool_arguments: Arguments from the LLM's tool call

    Returns:
        Formatted payload for the widget
    """
    tool = get_client_tool(tool_name)
    if not tool:
        return {"error": f"Unknown tool: {tool_name}"}

    widget_type = tool.widget_type.value

    if tool_name == ClientToolName.PRESENT_CHOICES.value:
        return {
            "widget_type": widget_type,
            "prompt": tool_arguments.get("prompt", ""),
            "options": tool_arguments.get("options", []),
            "context": tool_arguments.get("context"),
        }
    elif tool_name == ClientToolName.REQUEST_FREE_TEXT.value:
        return {
            "widget_type": widget_type,
            "prompt": tool_arguments.get("prompt", ""),
            "placeholder": tool_arguments.get("placeholder"),
            "min_length": tool_arguments.get("min_length", 1),
            "max_length": tool_arguments.get("max_length", 2000),
            "multiline": tool_arguments.get("multiline", True),
        }
    elif tool_name == ClientToolName.PRESENT_CODE_EDITOR.value:
        return {
            "widget_type": widget_type,
            "prompt": tool_arguments.get("prompt", ""),
            "language": tool_arguments.get("language", "python"),
            "initial_code": tool_arguments.get("initial_code"),
            "read_only_lines": tool_arguments.get("read_only_lines"),
        }
    else:
        # Fallback - return arguments as-is
        return {
            "widget_type": widget_type,
            **tool_arguments,
        }
