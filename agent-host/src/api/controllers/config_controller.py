"""Configuration controller for frontend app settings."""

import logging

from classy_fastapi.decorators import get
from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from neuroglia.mvc import ControllerBase
from pydantic import BaseModel

from application.settings import app_settings
from infrastructure.app_settings_service import get_settings_service

logger = logging.getLogger(__name__)


class ModelOption(BaseModel):
    """A selectable LLM model option."""

    id: str  # Qualified model identifier (e.g., "openai:gpt-4o" or "ollama:qwen2.5:7b")
    name: str  # User-friendly display name (e.g., "GPT-4o" or "Qwen 2.5 (Fast)")
    description: str  # Brief description of model capabilities
    provider: str  # Provider identifier (e.g., "openai" or "ollama")


class AppConfigResponse(BaseModel):
    """Response containing frontend application configuration."""

    app_name: str
    welcome_message: str
    rate_limit_requests_per_minute: int
    rate_limit_concurrent_requests: int
    app_tag: str
    app_repo_url: str
    tools_provider_url: str  # External URL for admin tools link
    # Model selection
    allow_model_selection: bool
    default_model: str  # Qualified model ID (e.g., "openai:gpt-4o")
    default_provider: str  # Default provider (e.g., "openai" or "ollama")
    available_models: list[ModelOption]


def parse_available_models(models_str: str) -> list[ModelOption]:
    """Parse the available_models JSON setting into ModelOption objects.

    Expected format: JSON array of model definitions
    '[{"provider":"openai","id":"gpt-4o","name":"GPT-4o","description":"..."}]'

    Each model object should have:
    - provider: "openai" or "ollama"
    - id: model identifier (e.g., "gpt-4o", "llama3.2:3b")
    - name: display name
    - description: (optional) model description

    Args:
        models_str: JSON array of model definitions

    Returns:
        List of ModelOption objects
    """
    import json

    models_str = models_str.strip()
    if not models_str:
        return []

    # Strip surrounding quotes (common issue with env vars passed through Docker)
    if (models_str.startswith("'") and models_str.endswith("'")) or (models_str.startswith('"') and models_str.endswith('"')):
        models_str = models_str[1:-1]

    try:
        models_data = json.loads(models_str)
        if not isinstance(models_data, list):
            logger.warning(f"available_models must be a JSON array, got: {type(models_data)}")
            return []

        models = []
        for item in models_data:
            provider = item.get("provider", "ollama")
            model_id = item.get("id", "")
            name = item.get("name", model_id)
            description = item.get("description", "")

            if not model_id:
                continue

            # Build qualified ID (provider:model_id)
            qualified_id = f"{provider}:{model_id}"

            # Generate description if not provided
            if not description:
                description = _generate_model_description(qualified_id, name, provider)

            models.append(
                ModelOption(
                    id=qualified_id,
                    name=name,
                    description=description,
                    provider=provider,
                )
            )
        return models
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse available_models JSON: {e}")
        return []


def _generate_model_description(model_id: str, display_name: str, provider: str) -> str:
    """Generate a user-friendly description for a model.

    Args:
        model_id: The qualified model identifier
        display_name: The user-friendly name
        provider: The provider identifier

    Returns:
        A brief description of the model
    """
    model_lower = model_id.lower()

    # OpenAI/Circuit model descriptions
    if provider == "openai":
        openai_descriptions = {
            # GPT models
            "gpt-5.1-chat": "Best for general use and conversation.",
            "gpt-5.1": "Best for logic, multi-step tasks, and coding.",
            "gpt-4o": "Fast, capable model for general tasks.",
            "gpt-4o-mini": "Fast and efficient. Great for routine tasks.",
            "gpt-4-turbo": "Previous generation with vision. Good balance.",
            "gpt-4": "Stable, reliable model for complex tasks.",
            "gpt-3.5-turbo": "Fast and cost-effective for simple tasks.",
            # Claude models (via Circuit)
            "claude-opus-4": "Enterprise-scale dialogue, analysis, and content.",
            "claude-opus": "Enterprise-scale dialogue, analysis, and content.",
            "claude-sonnet-4.5": "Complex reasoning, creative writing, problem-solving.",
            "claude-sonnet-4": "Coding and content generation.",
            "claude-sonnet": "Balanced Claude model for general tasks.",
            "claude-haiku-4.5": "Fast responses, concise answers, real-time reasoning.",
            "claude-haiku": "Fast and efficient Claude model.",
            # Gemini models (via Circuit)
            "gemini-2.5-pro": "Best for coding and complex prompts.",
            "gemini-2.5": "Google's advanced reasoning model.",
            "gemini-pro": "Google's capable model for diverse tasks.",
            # Reasoning models
            "o1-preview": "Advanced reasoning model for complex problems.",
            "o1-mini": "Efficient reasoning model.",
        }
        for key, desc in openai_descriptions.items():
            if key in model_lower:
                return desc
        return "Cloud model with advanced capabilities."

    # Ollama model descriptions (local models)
    descriptions = {
        "qwen2.5": "Fast and efficient. Great for quick tool operations.",
        "llama3.2": "Compact model with good reasoning. Ideal for general tasks.",
        "llama3.1": "More capable model. Better for complex tool chains.",
        "mistral": "Well-balanced performance. Good for diverse tasks.",
        "codellama": "Specialized for code-related tasks.",
        "deepseek": "Strong reasoning capabilities.",
        "phi": "Microsoft's efficient small model.",
        "gemma": "Google's open model family.",
        "gpt-oss": "Powerful open-source GPT variant.",
    }

    for key, desc in descriptions.items():
        if key in model_lower:
            return desc

    return "AI assistant with tool capabilities."


class ConfigController(ControllerBase):
    """Controller for application configuration endpoints.

    Provides configuration data to the frontend without requiring authentication.
    This allows the UI to fetch dynamic settings on initialization.
    """

    def __init__(self, service_provider: ServiceProviderBase, mapper: Mapper, mediator: Mediator):
        super().__init__(service_provider, mapper, mediator)

    @get("/")
    async def get_config(self) -> AppConfigResponse:
        """
        Get application configuration for the frontend.

        Returns configuration values that the UI needs to initialize,
        including the welcome message, rate limit settings, and available models.

        This endpoint does not require authentication so it can be
        called before the user logs in.

        Settings are loaded from MongoDB if stored, otherwise defaults from env vars.
        """
        # Try to load stored settings from MongoDB
        service = get_settings_service()
        stored_settings = await service.get_settings_async()

        if stored_settings:
            # Use stored settings
            available_models = parse_available_models(stored_settings.llm.available_models or app_settings.available_models)

            # Determine default provider and model
            default_provider = stored_settings.llm.default_llm_provider or app_settings.default_llm_provider
            if default_provider == "openai":
                default_model_name = stored_settings.llm.openai_model or app_settings.openai_model
            else:
                default_model_name = stored_settings.llm.ollama_model or app_settings.ollama_model
            default_model = f"{default_provider}:{default_model_name}"

            return AppConfigResponse(
                app_name=app_settings.app_name,  # App name always from env
                welcome_message=stored_settings.ui.welcome_message or app_settings.welcome_message,
                rate_limit_requests_per_minute=stored_settings.ui.rate_limit_requests_per_minute,
                rate_limit_concurrent_requests=stored_settings.ui.rate_limit_concurrent_requests,
                app_tag=stored_settings.ui.app_tag or app_settings.app_tag,
                app_repo_url=stored_settings.ui.app_repo_url or app_settings.app_repo_url,
                tools_provider_url=app_settings.tools_provider_external_url,
                allow_model_selection=stored_settings.llm.allow_model_selection,
                default_model=default_model,
                default_provider=default_provider,
                available_models=available_models,
            )
        else:
            # Use defaults from env vars
            available_models = parse_available_models(app_settings.available_models)
            default_provider = app_settings.default_llm_provider
            if default_provider == "openai":
                default_model = f"openai:{app_settings.openai_model}"
            else:
                default_model = f"ollama:{app_settings.ollama_model}"

            return AppConfigResponse(
                app_name=app_settings.app_name,
                welcome_message=app_settings.welcome_message,
                rate_limit_requests_per_minute=app_settings.rate_limit_requests_per_minute,
                rate_limit_concurrent_requests=app_settings.rate_limit_concurrent_requests,
                app_tag=app_settings.app_tag,
                app_repo_url=app_settings.app_repo_url,
                tools_provider_url=app_settings.tools_provider_external_url,
                allow_model_selection=app_settings.allow_model_selection,
                default_model=default_model,
                default_provider=default_provider,
                available_models=available_models,
            )
