"""Unit tests for ModelHandler.

Tests cover:
- Model change validation
- Model change in context
- Available models listing
- Model validation
"""

from unittest.mock import MagicMock

import pytest

from application.orchestrator.context import ConversationContext
from application.orchestrator.handlers.model_handler import ModelHandler


@pytest.fixture
def mock_llm_factory():
    """Create a mock LlmProviderFactory."""
    factory = MagicMock()
    factory.get_provider_for_model = MagicMock()
    factory.get_all_providers = MagicMock(return_value={})
    return factory


@pytest.fixture
def sample_context():
    """Create a sample ConversationContext."""
    return ConversationContext(
        connection_id="test-conn-123",
        conversation_id="conv-456",
        user_id="user-789",
        model="openai:gpt-4o",
        allow_model_selection=True,
    )


@pytest.fixture
def handler(mock_llm_factory):
    """Create a ModelHandler with mocked dependencies."""
    return ModelHandler(mock_llm_factory)


class TestModelHandlerChange:
    """Test model change handling."""

    def test_change_model_success(self, handler, sample_context, mock_llm_factory):
        """Test successful model change."""
        mock_llm_factory.get_provider_for_model.return_value = MagicMock()

        handler.handle_model_change(sample_context, "anthropic:claude-3-opus")

        assert sample_context.model == "anthropic:claude-3-opus"

    def test_change_model_validates_availability(self, handler, sample_context, mock_llm_factory):
        """Test that model availability is validated."""
        mock_llm_factory.get_provider_for_model.side_effect = Exception("Model not found")

        with pytest.raises(ValueError, match="not available"):
            handler.handle_model_change(sample_context, "invalid:model")

        # Model should not change
        assert sample_context.model == "openai:gpt-4o"

    def test_change_model_rejects_when_disabled(self, handler, mock_llm_factory):
        """Test that model change is rejected when not allowed."""
        context = ConversationContext(
            connection_id="conn-1",
            conversation_id="conv-1",
            user_id="user-1",
            allow_model_selection=False,
        )

        with pytest.raises(ValueError, match="not allowed"):
            handler.handle_model_change(context, "openai:gpt-4")


class TestModelHandlerValidation:
    """Test model validation."""

    def test_validate_valid_model(self, handler, mock_llm_factory):
        """Test validation of valid model."""
        mock_llm_factory.get_provider_for_model.return_value = MagicMock()

        result = handler.validate_model_id("openai:gpt-4o")

        assert result is True

    def test_validate_invalid_model(self, handler, mock_llm_factory):
        """Test validation of invalid model."""
        mock_llm_factory.get_provider_for_model.side_effect = Exception("Not found")

        result = handler.validate_model_id("invalid:model")

        assert result is False


class TestModelHandlerAvailableModels:
    """Test available models listing."""

    def test_get_available_models_empty(self, handler, mock_llm_factory):
        """Test getting available models when none configured."""
        mock_llm_factory.get_all_providers.return_value = {}

        models = handler.get_available_models()

        assert models == []

    def test_get_available_models_with_providers(self, handler, mock_llm_factory):
        """Test getting available models from providers."""
        # Create mock providers with models
        mock_model_1 = MagicMock()
        mock_model_1.id = "gpt-4o"
        mock_model_1.name = "GPT-4 Opus"

        mock_model_2 = MagicMock()
        mock_model_2.id = "gpt-3.5-turbo"
        mock_model_2.name = "GPT-3.5 Turbo"

        mock_provider = MagicMock()
        mock_provider.available_models = [mock_model_1, mock_model_2]

        mock_llm_factory.get_all_providers.return_value = {"openai": mock_provider}

        models = handler.get_available_models()

        assert len(models) == 2
        assert models[0]["id"] == "openai:gpt-4o"
        assert models[0]["name"] == "GPT-4 Opus"
        assert models[0]["provider"] == "openai"
        assert models[1]["id"] == "openai:gpt-3.5-turbo"

    def test_get_available_models_multiple_providers(self, handler, mock_llm_factory):
        """Test getting models from multiple providers."""
        # OpenAI provider
        mock_openai_model = MagicMock()
        mock_openai_model.id = "gpt-4o"
        mock_openai_model.name = "GPT-4 Opus"

        mock_openai = MagicMock()
        mock_openai.available_models = [mock_openai_model]

        # Anthropic provider
        mock_anthropic_model = MagicMock()
        mock_anthropic_model.id = "claude-3-opus"
        mock_anthropic_model.name = "Claude 3 Opus"

        mock_anthropic = MagicMock()
        mock_anthropic.available_models = [mock_anthropic_model]

        mock_llm_factory.get_all_providers.return_value = {
            "openai": mock_openai,
            "anthropic": mock_anthropic,
        }

        models = handler.get_available_models()

        assert len(models) == 2
        providers = {m["provider"] for m in models}
        assert providers == {"openai", "anthropic"}
