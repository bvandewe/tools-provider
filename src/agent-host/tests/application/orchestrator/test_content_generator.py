"""Unit tests for ContentGenerator.

Tests cover:
- Basic content generation with instructions
- Content generation with source_id only
- Missing instructions and source_id handling
- LLM generation errors
- Prompt building with Jinja variables
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from application.orchestrator.context import ConversationContext
from application.orchestrator.template.content_generator import ContentGenerator
from application.orchestrator.template.jinja_renderer import JinjaRenderer


@pytest.fixture
def mock_llm_provider():
    """Create a mock LLM provider."""
    provider = MagicMock()
    response = MagicMock()
    response.content = "Generated content from LLM"
    provider.chat = AsyncMock(return_value=response)
    return provider


@pytest.fixture
def mock_llm_factory(mock_llm_provider):
    """Create a mock LlmProviderFactory."""
    factory = MagicMock()
    factory.get_provider_for_model = MagicMock(return_value=mock_llm_provider)
    return factory


@pytest.fixture
def jinja_renderer():
    """Create a JinjaRenderer instance."""
    return JinjaRenderer()


@pytest.fixture
def generator(mock_llm_factory, jinja_renderer):
    """Create a ContentGenerator with mocked dependencies."""
    return ContentGenerator(mock_llm_factory, jinja_renderer)


@pytest.fixture
def sample_context():
    """Create a sample ConversationContext."""
    return ConversationContext(
        connection_id="conn-123",
        conversation_id="conv-456",
        user_id="user-789",
        model="openai:gpt-4o",
    )


@pytest.fixture
def sample_content():
    """Create a sample ItemContentDto-like object."""
    content = MagicMock()
    content.id = "content-1"
    content.widget_type = "message"
    content.is_templated = True
    content.source_id = None
    content.stem = None
    return content


@pytest.fixture
def sample_item():
    """Create a sample ConversationItemDto-like object."""
    item = MagicMock()
    item.id = "item-1"
    item.instructions = "Generate a greeting for the user."
    return item


class TestContentGeneratorBasicGeneration:
    """Test basic content generation scenarios."""

    @pytest.mark.asyncio
    async def test_generate_with_instructions(self, generator, sample_context, sample_content, sample_item, mock_llm_provider):
        """Test content generation with item instructions."""
        result = await generator.generate(sample_context, sample_content, sample_item)

        assert result == "Generated content from LLM"
        mock_llm_provider.chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_with_source_id_only(self, generator, sample_context, sample_content, mock_llm_provider):
        """Test content generation with source_id but no instructions."""
        sample_content.source_id = "skill-template-1"
        item = MagicMock()
        item.instructions = None

        result = await generator.generate(sample_context, sample_content, item)

        assert result == "Generated content from LLM"
        mock_llm_provider.chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_without_item(self, generator, sample_context, sample_content, mock_llm_provider):
        """Test generation fails gracefully without item or source_id."""
        # No item means no instructions
        result = await generator.generate(sample_context, sample_content, None)

        assert result is None
        mock_llm_provider.chat.assert_not_called()


class TestContentGeneratorNoInstructions:
    """Test handling of missing instructions."""

    @pytest.mark.asyncio
    async def test_no_instructions_or_source_id_returns_none(self, generator, sample_context, sample_content):
        """Test that missing instructions and source_id returns None."""
        sample_content.source_id = None
        item = MagicMock()
        item.instructions = None

        result = await generator.generate(sample_context, sample_content, item)

        assert result is None

    @pytest.mark.asyncio
    async def test_empty_instructions_returns_none(self, generator, sample_context, sample_content):
        """Test that empty instructions returns None."""
        sample_content.source_id = None
        item = MagicMock()
        item.instructions = ""

        result = await generator.generate(sample_context, sample_content, item)

        # Empty string is falsy, so should return None
        assert result is None


class TestContentGeneratorPromptBuilding:
    """Test prompt building logic."""

    @pytest.mark.asyncio
    async def test_prompt_includes_widget_type(self, generator, sample_context, sample_content, sample_item, mock_llm_provider):
        """Test that non-message widget types are included in prompt."""
        sample_content.widget_type = "multiple_choice"

        await generator.generate(sample_context, sample_content, sample_item)

        # Check that the prompt was built with widget type
        call_args = mock_llm_provider.chat.call_args
        messages = call_args[0][0]
        user_message_content = messages[1].content
        assert "multiple_choice" in user_message_content

    @pytest.mark.asyncio
    async def test_prompt_excludes_widget_type_for_message(self, generator, sample_context, sample_content, sample_item, mock_llm_provider):
        """Test that message widget type is not included in prompt."""
        sample_content.widget_type = "message"

        await generator.generate(sample_context, sample_content, sample_item)

        # Check that the prompt was built without widget type instruction
        call_args = mock_llm_provider.chat.call_args
        messages = call_args[0][0]
        user_message_content = messages[1].content
        assert "Generate content suitable for a message widget" not in user_message_content

    @pytest.mark.asyncio
    async def test_prompt_renders_jinja_variables(self, generator, sample_context, sample_content, mock_llm_provider):
        """Test that Jinja variables in instructions are rendered."""
        item = MagicMock()
        item.instructions = "Hello {{ user_id }}, generate content."

        await generator.generate(sample_context, sample_content, item)

        call_args = mock_llm_provider.chat.call_args
        messages = call_args[0][0]
        user_message_content = messages[1].content
        assert "Hello user-789, generate content." in user_message_content


class TestContentGeneratorModelSelection:
    """Test model selection from context."""

    @pytest.mark.asyncio
    async def test_uses_context_model(self, generator, sample_context, sample_content, sample_item, mock_llm_factory):
        """Test that the model from context is used."""
        sample_context.model = "openai:gpt-4-turbo"

        await generator.generate(sample_context, sample_content, sample_item)

        mock_llm_factory.get_provider_for_model.assert_called_once_with("openai:gpt-4-turbo")

    @pytest.mark.asyncio
    async def test_uses_default_model_when_none(self, generator, sample_content, sample_item, mock_llm_factory):
        """Test that default model is used when context has no model."""
        context = ConversationContext(
            connection_id="conn-1",
            conversation_id="conv-1",
            user_id="user-1",
        )
        context.model = None

        await generator.generate(context, sample_content, sample_item)

        mock_llm_factory.get_provider_for_model.assert_called_once_with("openai:gpt-4o-mini")


class TestContentGeneratorErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    async def test_llm_exception_returns_none(self, generator, sample_context, sample_content, sample_item, mock_llm_provider):
        """Test that LLM exceptions are caught and return None."""
        mock_llm_provider.chat.side_effect = Exception("LLM error")

        result = await generator.generate(sample_context, sample_content, sample_item)

        assert result is None

    @pytest.mark.asyncio
    async def test_llm_returns_none_response(self, generator, sample_context, sample_content, sample_item, mock_llm_provider):
        """Test handling when LLM returns None response."""
        mock_llm_provider.chat.return_value = None

        result = await generator.generate(sample_context, sample_content, sample_item)

        assert result is None

    @pytest.mark.asyncio
    async def test_llm_returns_empty_content(self, generator, sample_context, sample_content, sample_item, mock_llm_provider):
        """Test handling when LLM returns empty content."""
        response = MagicMock()
        response.content = ""
        mock_llm_provider.chat.return_value = response

        result = await generator.generate(sample_context, sample_content, sample_item)

        # Empty string is still returned (not None)
        assert result == ""


class TestContentGeneratorBuildPrompt:
    """Test the _build_prompt method."""

    def test_build_prompt_with_instructions_only(self, generator, sample_context):
        """Test building prompt with only instructions."""
        content = MagicMock()
        content.widget_type = "message"

        prompt = generator._build_prompt(
            sample_context,
            content,
            instructions="Test instructions",
            source_id=None,
        )

        assert prompt == "Test instructions"

    def test_build_prompt_with_source_id_only(self, generator, sample_context):
        """Test building prompt with only source_id."""
        content = MagicMock()
        content.widget_type = "message"

        prompt = generator._build_prompt(
            sample_context,
            content,
            instructions=None,
            source_id="template-1",
        )

        assert "Content type: template-1" in prompt

    def test_build_prompt_with_both(self, generator, sample_context):
        """Test building prompt with both instructions and source_id."""
        content = MagicMock()
        content.widget_type = "short_answer"

        prompt = generator._build_prompt(
            sample_context,
            content,
            instructions="Custom instructions",
            source_id="skill-1",
        )

        assert "Custom instructions" in prompt
        assert "Content type: skill-1" in prompt
        assert "short_answer" in prompt

    def test_build_prompt_returns_none_when_empty(self, generator, sample_context):
        """Test building prompt returns None when nothing to build."""
        content = MagicMock()
        content.widget_type = "message"

        prompt = generator._build_prompt(
            sample_context,
            content,
            instructions=None,
            source_id=None,
        )

        assert prompt is None
