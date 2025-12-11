"""Unit tests for client tools module."""

from application.agents.client_tools import (
    CLIENT_TOOL_NAMES,
    CLIENT_TOOLS,
    PRESENT_CHOICES_TOOL,
    PRESENT_CODE_EDITOR_TOOL,
    REQUEST_FREE_TEXT_TOOL,
    ClientToolName,
    WidgetType,
    extract_widget_payload,
    get_all_client_tools,
    get_client_tool,
    get_client_tool_manifest,
    get_widget_type_for_tool,
    is_client_tool,
    validate_response,
)


class TestClientToolDefinition:
    """Tests for ClientToolDefinition dataclass."""

    def test_present_choices_tool_exists(self) -> None:
        """present_choices tool should be defined."""
        assert PRESENT_CHOICES_TOOL is not None
        assert PRESENT_CHOICES_TOOL.name == "present_choices"
        assert PRESENT_CHOICES_TOOL.widget_type == WidgetType.MULTIPLE_CHOICE

    def test_request_free_text_tool_exists(self) -> None:
        """request_free_text tool should be defined."""
        assert REQUEST_FREE_TEXT_TOOL is not None
        assert REQUEST_FREE_TEXT_TOOL.name == "request_free_text"
        assert REQUEST_FREE_TEXT_TOOL.widget_type == WidgetType.FREE_TEXT

    def test_present_code_editor_tool_exists(self) -> None:
        """present_code_editor tool should be defined."""
        assert PRESENT_CODE_EDITOR_TOOL is not None
        assert PRESENT_CODE_EDITOR_TOOL.name == "present_code_editor"
        assert PRESENT_CODE_EDITOR_TOOL.widget_type == WidgetType.CODE_EDITOR

    def test_tool_to_llm_format(self) -> None:
        """Tools should convert to LLM-compatible format."""
        llm_format = PRESENT_CHOICES_TOOL.to_llm_format()

        assert llm_format["type"] == "function"
        assert "function" in llm_format
        assert llm_format["function"]["name"] == "present_choices"
        assert "description" in llm_format["function"]
        assert "parameters" in llm_format["function"]

    def test_tool_parameters_schema(self) -> None:
        """Tool parameters should have valid JSON Schema structure."""
        params = PRESENT_CHOICES_TOOL.parameters

        assert params["type"] == "object"
        assert "properties" in params
        assert "prompt" in params["properties"]
        assert "options" in params["properties"]
        assert "required" in params
        assert "prompt" in params["required"]


class TestClientToolRegistry:
    """Tests for client tool registry functions."""

    def test_client_tool_names_set(self) -> None:
        """CLIENT_TOOL_NAMES should contain all tool names."""
        assert "present_choices" in CLIENT_TOOL_NAMES
        assert "request_free_text" in CLIENT_TOOL_NAMES
        assert "present_code_editor" in CLIENT_TOOL_NAMES
        assert len(CLIENT_TOOL_NAMES) == 3

    def test_client_tools_dict(self) -> None:
        """CLIENT_TOOLS dict should map names to definitions."""
        assert len(CLIENT_TOOLS) == 3
        assert CLIENT_TOOLS["present_choices"] == PRESENT_CHOICES_TOOL
        assert CLIENT_TOOLS["request_free_text"] == REQUEST_FREE_TEXT_TOOL
        assert CLIENT_TOOLS["present_code_editor"] == PRESENT_CODE_EDITOR_TOOL

    def test_is_client_tool_true(self) -> None:
        """is_client_tool should return True for client tools."""
        assert is_client_tool("present_choices") is True
        assert is_client_tool("request_free_text") is True
        assert is_client_tool("present_code_editor") is True

    def test_is_client_tool_false(self) -> None:
        """is_client_tool should return False for non-client tools."""
        assert is_client_tool("execute_query") is False
        assert is_client_tool("get_weather") is False
        assert is_client_tool("") is False

    def test_get_client_tool(self) -> None:
        """get_client_tool should return tool definition."""
        tool = get_client_tool("present_choices")
        assert tool is not None
        assert tool.name == "present_choices"

    def test_get_client_tool_not_found(self) -> None:
        """get_client_tool should return None for unknown tools."""
        assert get_client_tool("unknown_tool") is None

    def test_get_widget_type_for_tool(self) -> None:
        """get_widget_type_for_tool should return correct widget type."""
        assert get_widget_type_for_tool("present_choices") == WidgetType.MULTIPLE_CHOICE
        assert get_widget_type_for_tool("request_free_text") == WidgetType.FREE_TEXT
        assert get_widget_type_for_tool("present_code_editor") == WidgetType.CODE_EDITOR

    def test_get_widget_type_for_unknown_tool(self) -> None:
        """get_widget_type_for_tool should return None for unknown tools."""
        assert get_widget_type_for_tool("unknown") is None

    def test_get_client_tool_manifest(self) -> None:
        """get_client_tool_manifest should return LLM-compatible list."""
        manifest = get_client_tool_manifest()

        assert isinstance(manifest, list)
        assert len(manifest) == 3

        for tool in manifest:
            assert tool["type"] == "function"
            assert "function" in tool
            assert "name" in tool["function"]

    def test_get_all_client_tools(self) -> None:
        """get_all_client_tools should return all tool definitions."""
        tools = get_all_client_tools()

        assert len(tools) == 3
        names = {t.name for t in tools}
        assert "present_choices" in names
        assert "request_free_text" in names
        assert "present_code_editor" in names


class TestResponseValidation:
    """Tests for response validation functions."""

    def test_validate_choice_response_valid(self) -> None:
        """Valid choice responses should pass validation."""
        result = validate_response("present_choices", {"selection": "Option A", "index": 0})

        assert result.is_valid is True
        assert result.normalized_value["selection"] == "Option A"
        assert result.normalized_value["index"] == 0

    def test_validate_choice_response_selection_only(self) -> None:
        """Choice response with only selection should be valid."""
        result = validate_response("present_choices", {"selection": "Option B"})

        assert result.is_valid is True
        assert result.normalized_value["selection"] == "Option B"
        assert result.normalized_value["index"] is None

    def test_validate_choice_response_index_only(self) -> None:
        """Choice response with only index should be valid."""
        result = validate_response("present_choices", {"index": 2})

        assert result.is_valid is True
        assert result.normalized_value["selection"] is None
        assert result.normalized_value["index"] == 2

    def test_validate_choice_response_invalid(self) -> None:
        """Choice response without selection or index should fail."""
        result = validate_response("present_choices", {"other": "value"})

        assert result.is_valid is False
        assert "selection" in result.error_message.lower() or "index" in result.error_message.lower()

    def test_validate_free_text_response_valid(self) -> None:
        """Valid free text responses should pass validation."""
        result = validate_response("request_free_text", {"text": "This is my answer."})

        assert result.is_valid is True
        assert result.normalized_value["text"] == "This is my answer."

    def test_validate_free_text_response_alternative_keys(self) -> None:
        """Free text response with alternative keys should be normalized."""
        # Try with 'value' instead of 'text'
        result = validate_response("request_free_text", {"value": "Alternative value"})

        assert result.is_valid is True
        assert result.normalized_value["text"] == "Alternative value"

    def test_validate_free_text_response_invalid(self) -> None:
        """Free text response without text should fail."""
        result = validate_response("request_free_text", {"other": "value"})

        assert result.is_valid is False
        assert "text" in result.error_message.lower()

    def test_validate_code_response_valid(self) -> None:
        """Valid code responses should pass validation."""
        result = validate_response("present_code_editor", {"code": "def hello():\n    print('Hello')"})

        assert result.is_valid is True
        assert "def hello()" in result.normalized_value["code"]

    def test_validate_code_response_alternative_keys(self) -> None:
        """Code response with alternative keys should be normalized."""
        result = validate_response("present_code_editor", {"content": "print('test')"})

        assert result.is_valid is True
        assert result.normalized_value["code"] == "print('test')"

    def test_validate_code_response_invalid(self) -> None:
        """Code response without code should fail."""
        result = validate_response("present_code_editor", {"other": "value"})

        assert result.is_valid is False
        assert "code" in result.error_message.lower()

    def test_validate_unknown_tool(self) -> None:
        """Validation of unknown tool should fail."""
        result = validate_response("unknown_tool", {"data": "value"})

        assert result.is_valid is False
        assert "unknown" in result.error_message.lower()


class TestExtractWidgetPayload:
    """Tests for extract_widget_payload function."""

    def test_extract_multiple_choice_payload(self) -> None:
        """Multiple choice widget payload should be extracted correctly."""
        payload = extract_widget_payload(
            "present_choices",
            {
                "prompt": "What is 2 + 2?",
                "options": ["3", "4", "5"],
                "context": "Math quiz",
            },
        )

        assert payload["widget_type"] == "multiple_choice"
        assert payload["prompt"] == "What is 2 + 2?"
        assert payload["options"] == ["3", "4", "5"]
        assert payload["context"] == "Math quiz"

    def test_extract_free_text_payload(self) -> None:
        """Free text widget payload should be extracted correctly."""
        payload = extract_widget_payload(
            "request_free_text",
            {
                "prompt": "Explain your reasoning",
                "placeholder": "Type here...",
                "min_length": 10,
                "max_length": 500,
            },
        )

        assert payload["widget_type"] == "free_text"
        assert payload["prompt"] == "Explain your reasoning"
        assert payload["placeholder"] == "Type here..."
        assert payload["min_length"] == 10
        assert payload["max_length"] == 500

    def test_extract_code_editor_payload(self) -> None:
        """Code editor widget payload should be extracted correctly."""
        payload = extract_widget_payload(
            "present_code_editor",
            {
                "prompt": "Write a function",
                "language": "python",
                "initial_code": "def solution():\n    pass",
            },
        )

        assert payload["widget_type"] == "code_editor"
        assert payload["prompt"] == "Write a function"
        assert payload["language"] == "python"
        assert payload["initial_code"] == "def solution():\n    pass"

    def test_extract_payload_default_values(self) -> None:
        """Payload extraction should provide default values."""
        payload = extract_widget_payload(
            "request_free_text",
            {"prompt": "Enter text"},
        )

        assert payload["min_length"] == 1
        assert payload["max_length"] == 2000
        assert payload["multiline"] is True

    def test_extract_unknown_tool_payload(self) -> None:
        """Unknown tool should return error payload."""
        payload = extract_widget_payload("unknown_tool", {"data": "value"})

        assert "error" in payload


class TestClientToolNameEnum:
    """Tests for ClientToolName enum."""

    def test_enum_values(self) -> None:
        """Enum should have correct values."""
        assert ClientToolName.PRESENT_CHOICES.value == "present_choices"
        assert ClientToolName.REQUEST_FREE_TEXT.value == "request_free_text"
        assert ClientToolName.PRESENT_CODE_EDITOR.value == "present_code_editor"


class TestWidgetTypeEnum:
    """Tests for WidgetType enum."""

    def test_enum_values(self) -> None:
        """Enum should have correct values."""
        assert WidgetType.MULTIPLE_CHOICE.value == "multiple_choice"
        assert WidgetType.FREE_TEXT.value == "free_text"
        assert WidgetType.CODE_EDITOR.value == "code_editor"
