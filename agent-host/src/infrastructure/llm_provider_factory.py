"""LLM Provider Factory for runtime provider selection.

This module provides a factory pattern for selecting the appropriate LLM provider
at runtime based on model specification. It supports multiple providers (Ollama, OpenAI)
and handles model routing via qualified model IDs (e.g., "openai:gpt-4o", "ollama:llama3.2:3b").

Design Pattern:
- Factory Pattern: Creates appropriate provider based on model prefix
- Strategy Pattern: Each provider implements the same interface
- Singleton Registry: Providers are registered once and reused

Usage:
    factory = LlmProviderFactory(settings)
    factory.register_provider(LlmProviderType.OLLAMA, ollama_provider)
    factory.register_provider(LlmProviderType.OPENAI, openai_provider)

    # Get provider for a specific model
    provider = factory.get_provider_for_model("openai:gpt-4o")

    # Or use the default provider
    provider = factory.get_default_provider()
"""

import json
import logging
from typing import TYPE_CHECKING, Optional

from application.agents.llm_provider import LlmProvider, LlmProviderError, LlmProviderType, ModelDefinition

if TYPE_CHECKING:
    from neuroglia.hosting.abstractions import ApplicationBuilderBase

logger = logging.getLogger(__name__)


class LlmProviderFactory:
    """Factory for creating and selecting LLM providers.

    This factory manages registered providers and handles runtime selection
    based on model specification. It supports:

    - Multiple provider registration (Ollama, OpenAI, etc.)
    - Model-based provider routing via qualified IDs
    - Default provider selection
    - Model definition parsing from settings

    Thread Safety:
    - Provider registration should happen during startup
    - Runtime selection is read-only and thread-safe

    Example:
        # During startup
        factory = LlmProviderFactory(settings)
        factory.register_provider(LlmProviderType.OLLAMA, ollama_provider)
        factory.register_provider(LlmProviderType.OPENAI, openai_provider)

        # At runtime
        provider = factory.get_provider_for_model("openai:gpt-4o")
        response = await provider.chat(messages)
    """

    def __init__(self, default_provider: LlmProviderType = LlmProviderType.OLLAMA) -> None:
        """Initialize the factory.

        Args:
            default_provider: Default provider type when model doesn't specify
        """
        self._providers: dict[LlmProviderType, LlmProvider] = {}
        self._default_provider_type = default_provider
        self._available_models: list[ModelDefinition] = []

    @property
    def default_provider_type(self) -> LlmProviderType:
        """Get the default provider type."""
        return self._default_provider_type

    @default_provider_type.setter
    def default_provider_type(self, value: LlmProviderType) -> None:
        """Set the default provider type."""
        self._default_provider_type = value

    @property
    def available_providers(self) -> list[LlmProviderType]:
        """Get list of registered provider types."""
        return list(self._providers.keys())

    @property
    def available_models(self) -> list[ModelDefinition]:
        """Get list of available models."""
        return self._available_models

    def register_provider(self, provider_type: LlmProviderType, provider: LlmProvider) -> None:
        """Register a provider instance.

        Args:
            provider_type: The provider type identifier
            provider: The provider instance
        """
        self._providers[provider_type] = provider
        logger.info(f"Registered LLM provider: {provider_type.value}")

    def unregister_provider(self, provider_type: LlmProviderType) -> None:
        """Unregister a provider.

        Args:
            provider_type: The provider type to unregister
        """
        if provider_type in self._providers:
            del self._providers[provider_type]
            logger.info(f"Unregistered LLM provider: {provider_type.value}")

    def get_provider(self, provider_type: LlmProviderType) -> Optional[LlmProvider]:
        """Get a provider by type.

        Args:
            provider_type: The provider type

        Returns:
            Provider instance or None if not registered
        """
        return self._providers.get(provider_type)

    def get_default_provider(self) -> LlmProvider:
        """Get the default provider.

        Returns:
            Default provider instance

        Raises:
            LlmProviderError: If no providers are registered
        """
        provider = self._providers.get(self._default_provider_type)
        if provider:
            return provider

        # Fallback to first available provider
        if self._providers:
            fallback_type = next(iter(self._providers.keys()))
            logger.warning(f"Default provider {self._default_provider_type.value} not available, using {fallback_type.value}")
            return self._providers[fallback_type]

        raise LlmProviderError(
            message="No LLM providers are available",
            error_code="no_providers_available",
            provider="factory",
            is_retryable=False,
        )

    def get_provider_for_model(self, model_id: str) -> LlmProvider:
        """Get the appropriate provider for a model ID.

        The model ID can be:
        - Qualified: "openai:gpt-4o" or "ollama:llama3.2:3b"
        - Unqualified: "gpt-4o" or "llama3.2:3b" (uses default provider)

        Args:
            model_id: The model identifier (qualified or unqualified)

        Returns:
            Appropriate provider for the model

        Raises:
            LlmProviderError: If provider not available
        """
        # Parse provider from qualified ID
        provider_type = self._default_provider_type
        actual_model_id = model_id

        if ":" in model_id:
            parts = model_id.split(":", 1)
            potential_provider = parts[0].lower()

            # Check if first part is a known provider
            try:
                provider_type = LlmProviderType(potential_provider)
                actual_model_id = parts[1]
            except ValueError:
                # Not a provider prefix, treat entire string as model ID
                # (e.g., "llama3.2:3b" where "llama3.2" is not a provider)
                pass

        provider = self._providers.get(provider_type)
        if not provider:
            raise LlmProviderError(
                message=f"Provider '{provider_type.value}' is not available",
                error_code="provider_not_available",
                provider="factory",
                is_retryable=False,
                details={"requested_provider": provider_type.value, "available": [p.value for p in self._providers.keys()]},
            )

        # Set model override on the provider
        provider.set_model_override(actual_model_id)

        return provider

    def parse_model_id(self, qualified_id: str) -> tuple[LlmProviderType, str]:
        """Parse a qualified model ID into provider and model components.

        Args:
            qualified_id: Model ID like "openai:gpt-4o" or "llama3.2:3b"

        Returns:
            Tuple of (provider_type, model_id)
        """
        if ":" in qualified_id:
            parts = qualified_id.split(":", 1)
            potential_provider = parts[0].lower()

            try:
                provider_type = LlmProviderType(potential_provider)
                return (provider_type, parts[1])
            except ValueError:
                pass

        return (self._default_provider_type, qualified_id)

    def load_models_from_settings(self, available_models_json: str) -> None:
        """Load available models from settings JSON string.

        Args:
            available_models_json: JSON array of model definitions
        """
        try:
            models_data = json.loads(available_models_json)
            self._available_models = []

            for model_data in models_data:
                try:
                    provider_str = model_data.get("provider", "ollama").lower()
                    provider = LlmProviderType(provider_str)

                    model = ModelDefinition(
                        provider=provider,
                        id=model_data["id"],
                        name=model_data.get("name", model_data["id"]),
                        description=model_data.get("description", ""),
                        is_default=model_data.get("is_default", False),
                    )
                    self._available_models.append(model)

                except (KeyError, ValueError) as e:
                    logger.warning(f"Failed to parse model definition: {model_data}, error: {e}")

            logger.info(f"Loaded {len(self._available_models)} model definitions")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse available_models JSON: {e}")
            self._available_models = []

    def get_models_for_provider(self, provider_type: LlmProviderType) -> list[ModelDefinition]:
        """Get available models for a specific provider.

        Args:
            provider_type: The provider type

        Returns:
            List of models for that provider
        """
        return [m for m in self._available_models if m.provider == provider_type]

    def get_default_model(self, provider_type: Optional[LlmProviderType] = None) -> Optional[ModelDefinition]:
        """Get the default model for a provider.

        Args:
            provider_type: Provider type (uses default if None)

        Returns:
            Default model or None
        """
        pt = provider_type or self._default_provider_type
        models = self.get_models_for_provider(pt)

        # Look for explicitly marked default
        for m in models:
            if m.is_default:
                return m

        # Fall back to first model
        return models[0] if models else None

    def is_provider_available(self, provider_type: LlmProviderType) -> bool:
        """Check if a provider is registered and available.

        Args:
            provider_type: The provider type

        Returns:
            True if provider is available
        """
        return provider_type in self._providers

    @staticmethod
    def configure(builder: "ApplicationBuilderBase") -> "LlmProviderFactory":
        """Configure LlmProviderFactory in the service collection.

        This should be called after individual providers are configured.

        Args:
            builder: The application builder

        Returns:
            Configured factory instance
        """
        from application.settings import Settings, app_settings

        # Get settings
        settings: Optional[Settings] = None
        for desc in builder.services:
            if desc.service_type is Settings and desc.singleton:
                settings = desc.singleton
                break

        if settings is None:
            settings = app_settings

        # Determine default provider
        try:
            default_provider = LlmProviderType(settings.default_llm_provider)
        except ValueError:
            logger.warning(f"Unknown default_llm_provider '{settings.default_llm_provider}', using ollama")
            default_provider = LlmProviderType.OLLAMA

        factory = LlmProviderFactory(default_provider=default_provider)

        # Load model definitions
        factory.load_models_from_settings(settings.available_models)

        # Register available providers
        from infrastructure.adapters.ollama_llm_provider import OllamaLlmProvider
        from infrastructure.adapters.openai_llm_provider import OpenAiLlmProvider

        # Check for Ollama provider
        ollama_provider: Optional[OllamaLlmProvider] = None
        for desc in builder.services:
            if desc.service_type is OllamaLlmProvider and desc.singleton:
                ollama_provider = desc.singleton
                break

        if ollama_provider:
            factory.register_provider(LlmProviderType.OLLAMA, ollama_provider)

        # Check for OpenAI provider
        openai_provider: Optional[OpenAiLlmProvider] = None
        for desc in builder.services:
            if desc.service_type is OpenAiLlmProvider and desc.singleton:
                openai_provider = desc.singleton
                break

        if openai_provider:
            factory.register_provider(LlmProviderType.OPENAI, openai_provider)

        # Register factory
        builder.services.add_singleton(LlmProviderFactory, singleton=factory)

        # Also register the default provider as the abstract LlmProvider interface
        # This maintains backward compatibility with code expecting a single provider
        try:
            default = factory.get_default_provider()
            builder.services.add_singleton(LlmProvider, singleton=default)
            logger.info(f"Registered default LlmProvider: {default.provider_type.value}")
        except LlmProviderError:
            logger.warning("No providers available to register as default LlmProvider")

        logger.info(f"✅ Configured LlmProviderFactory: providers={[p.value for p in factory.available_providers]}, default={default_provider.value}")
        return factory


# Singleton instance (for access outside DI context)
_provider_factory: Optional[LlmProviderFactory] = None


def get_provider_factory() -> Optional[LlmProviderFactory]:
    """Get the singleton factory instance.

    Returns:
        Factory instance or None if not initialized
    """
    return _provider_factory


def set_provider_factory(factory: LlmProviderFactory) -> None:
    """Set the singleton factory instance.

    Args:
        factory: Factory instance
    """
    global _provider_factory
    _provider_factory = factory
