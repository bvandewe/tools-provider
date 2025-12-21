"""Model handler for LLM model selection.

This handler manages LLM model changes during a conversation,
allowing users to switch between different models.
"""

import logging
from typing import TYPE_CHECKING

from application.orchestrator.context import ConversationContext

if TYPE_CHECKING:
    from infrastructure.llm_provider_factory import LlmProviderFactory

log = logging.getLogger(__name__)


class ModelHandler:
    """Handles LLM model selection and changes.

    Responsibilities:
    - Validating model availability
    - Updating conversation context with new model
    - Coordinating with LLM provider factory

    This handler enables dynamic model switching during conversations,
    allowing users to choose the best model for their needs.
    """

    def __init__(
        self,
        llm_provider_factory: "LlmProviderFactory",
    ):
        """Initialize the model handler.

        Args:
            llm_provider_factory: Factory for selecting LLM provider based on model
        """
        self._llm_provider_factory = llm_provider_factory

    def handle_model_change(
        self,
        context: ConversationContext,
        model_id: str,
    ) -> None:
        """Handle model change request from client.

        Updates the conversation context's model so subsequent agent runs use
        the newly selected model.

        Args:
            context: The conversation context
            model_id: Qualified model ID (e.g., "openai:gpt-4o", "ollama:llama3.2:3b")

        Raises:
            ValueError: If the model is not available or model selection is disabled
        """
        # Check if model selection is allowed for this conversation
        if not context.allow_model_selection:
            raise ValueError("Model selection is not allowed for this conversation")

        # Validate the model is available via the factory
        try:
            # This will raise if the provider/model is not available
            self._llm_provider_factory.get_provider_for_model(model_id)
        except Exception as e:
            log.error(f"Model {model_id} is not available: {e}")
            raise ValueError(f"Model '{model_id}' is not available") from e

        # Update the context
        old_model = context.model
        context.model = model_id
        log.info(f"🔄 Model changed for conversation {context.conversation_id[:8]}...: {old_model} → {model_id}")

    def get_available_models(self) -> list[dict[str, str]]:
        """Get list of available models.

        Returns:
            List of model dictionaries with id, name, and provider info
        """
        models = []

        # Get all providers from factory
        for provider_id, provider in self._llm_provider_factory.get_all_providers().items():
            for model in provider.available_models:
                models.append(
                    {
                        "id": f"{provider_id}:{model.id}",
                        "name": model.name,
                        "provider": provider_id,
                        "description": model.description if hasattr(model, "description") else None,
                    }
                )

        return models

    def validate_model_id(self, model_id: str) -> bool:
        """Check if a model ID is valid and available.

        Args:
            model_id: Qualified model ID to validate

        Returns:
            True if model is available, False otherwise
        """
        try:
            self._llm_provider_factory.get_provider_for_model(model_id)
            return True
        except Exception:
            return False
