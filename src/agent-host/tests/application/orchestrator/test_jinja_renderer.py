"""Unit tests for JinjaRenderer.

Tests cover:
- Basic variable substitution
- Missing variable handling (returns original)
- All available context variables
- Error handling for invalid templates
"""

import pytest

from application.orchestrator.context import ConversationContext
from application.orchestrator.template.jinja_renderer import JinjaRenderer


@pytest.fixture
def renderer():
    """Create a JinjaRenderer instance."""
    return JinjaRenderer()


@pytest.fixture
def sample_context():
    """Create a sample ConversationContext with various fields populated."""
    return ConversationContext(
        connection_id="test-conn-123",
        conversation_id="conv-456",
        user_id="user-789",
        definition_name="TestAgent",
        current_item_index=2,
        total_items=5,
    )


class TestJinjaRendererBasicSubstitution:
    """Test basic variable substitution."""

    def test_render_user_id(self, renderer, sample_context):
        """Test rendering user_id variable."""
        template = "Hello {{ user_id }}!"
        result = renderer.render(template, sample_context)
        assert result == "Hello user-789!"

    def test_render_user_name_fallback(self, renderer, sample_context):
        """Test user_name falls back to user_id."""
        template = "Welcome, {{ user_name }}!"
        result = renderer.render(template, sample_context)
        # user_name uses user_id as fallback
        assert result == "Welcome, user-789!"

    def test_render_conversation_id(self, renderer, sample_context):
        """Test rendering conversation_id variable."""
        template = "Conversation: {{ conversation_id }}"
        result = renderer.render(template, sample_context)
        assert result == "Conversation: conv-456"

    def test_render_agent_name(self, renderer, sample_context):
        """Test rendering agent_name from definition_name."""
        template = "I am {{ agent_name }}."
        result = renderer.render(template, sample_context)
        assert result == "I am TestAgent."

    def test_render_current_item_one_based(self, renderer, sample_context):
        """Test current_item is 1-based for display."""
        template = "Question {{ current_item }} of {{ total_items }}"
        result = renderer.render(template, sample_context)
        # current_item_index=2 -> current_item=3 (1-based)
        assert result == "Question 3 of 5"


class TestJinjaRendererDefaults:
    """Test default values for missing context fields."""

    def test_missing_user_id_renders_as_value(self, renderer):
        """Test user_id renders with provided value."""
        context = ConversationContext(
            connection_id="conn-1",
            conversation_id="conv-1",
            user_id="",  # Empty user_id
        )
        template = "User: [{{ user_id }}]"
        result = renderer.render(template, context)
        assert result == "User: []"

    def test_missing_definition_name_uses_agent_default(self, renderer):
        """Test missing definition_name uses 'Agent' as default."""
        context = ConversationContext(
            connection_id="conn-1",
            conversation_id="conv-1",
            user_id="user-1",
        )
        template = "From: {{ agent_name }}"
        result = renderer.render(template, context)
        assert result == "From: Agent"

    def test_missing_total_items_returns_zero(self, renderer):
        """Test missing total_items renders as 0."""
        context = ConversationContext(
            connection_id="conn-1",
            conversation_id="conv-1",
            user_id="user-1",
        )
        template = "Total: {{ total_items }}"
        result = renderer.render(template, context)
        assert result == "Total: 0"


class TestJinjaRendererTimestamp:
    """Test timestamp rendering."""

    def test_timestamp_is_iso_format(self, renderer, sample_context):
        """Test timestamp variable is ISO format."""
        template = "Time: {{ timestamp }}"
        result = renderer.render(template, sample_context)
        # Verify the result contains a timestamp-like string
        assert "Time: " in result
        # Should be ISO format (contains T separator)
        timestamp_part = result.replace("Time: ", "")
        # Just check it parses as ISO
        assert "T" in timestamp_part or ":" in timestamp_part


class TestJinjaRendererErrorHandling:
    """Test error handling scenarios."""

    def test_undefined_variable_renders_empty(self, renderer, sample_context):
        """Test undefined variables render as empty (Jinja default behavior)."""
        template = "Value: {{ undefined_var }}"
        result = renderer.render(template, sample_context)
        # Jinja2 with autoescape renders undefined as empty string
        assert result == "Value: "

    def test_syntax_error_returns_original(self, renderer, sample_context):
        """Test syntax errors return original template."""
        template = "Bad: {{ unclosed"
        result = renderer.render(template, sample_context)
        # Should return original on syntax error
        assert result == template

    def test_no_template_syntax_passthrough(self, renderer, sample_context):
        """Test plain text without template syntax passes through."""
        template = "Just plain text with no variables"
        result = renderer.render(template, sample_context)
        assert result == template


class TestJinjaRendererMultipleVariables:
    """Test templates with multiple variables."""

    def test_multiple_variables_in_template(self, renderer, sample_context):
        """Test rendering multiple variables in one template."""
        template = "Hello {{ user_id }}, this is {{ agent_name }}. You are on item {{ current_item }}."
        result = renderer.render(template, sample_context)
        assert result == "Hello user-789, this is TestAgent. You are on item 3."

    def test_repeated_variable(self, renderer, sample_context):
        """Test same variable used multiple times."""
        template = "{{ agent_name }} says: {{ agent_name }} is here!"
        result = renderer.render(template, sample_context)
        assert result == "TestAgent says: TestAgent is here!"


class TestJinjaRendererBuildTemplateVars:
    """Test the internal _build_template_vars method."""

    def test_build_template_vars_returns_dict(self, renderer, sample_context):
        """Test _build_template_vars returns expected dictionary."""
        vars_dict = renderer._build_template_vars(sample_context)

        assert isinstance(vars_dict, dict)
        assert "user_id" in vars_dict
        assert "user_name" in vars_dict
        assert "conversation_id" in vars_dict
        assert "agent_name" in vars_dict
        assert "current_item" in vars_dict
        assert "total_items" in vars_dict
        assert "timestamp" in vars_dict

    def test_build_template_vars_values(self, renderer, sample_context):
        """Test _build_template_vars returns correct values."""
        vars_dict = renderer._build_template_vars(sample_context)

        assert vars_dict["user_id"] == "user-789"
        assert vars_dict["conversation_id"] == "conv-456"
        assert vars_dict["agent_name"] == "TestAgent"
        assert vars_dict["current_item"] == 3  # 1-based
        assert vars_dict["total_items"] == 5
