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

    id: str  # Ollama model identifier (e.g., "qwen2.5:7b")
    name: str  # User-friendly display name (e.g., "Qwen 2.5 (Fast)")
    description: str  # Brief description of model capabilities


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
    default_model: str
    available_models: list[ModelOption]


def parse_available_models(models_str: str) -> list[ModelOption]:
    """Parse the available_models setting into ModelOption objects.

    Format: "model_id|Display Name,model_id2|Display Name 2"
    or "model_id|Display Name|Description,..."

    The model_id can contain colons (e.g., qwen2.5:7b), so we use pipe (|)
    as the delimiter between model_id, display name, and description.

    Args:
        models_str: Comma-separated model definitions

    Returns:
        List of ModelOption objects
    """
    models = []
    for entry in models_str.split(","):
        entry = entry.strip()
        if not entry:
            continue

        parts = entry.split("|")
        model_id = parts[0].strip()

        if len(parts) >= 2:
            display_name = parts[1].strip()
        else:
            # Use model_id as display name if not provided
            display_name = model_id.replace(":", " ").replace("-", " ").title()

        if len(parts) >= 3:
            description = parts[2].strip()
        else:
            # Generate description based on model characteristics
            description = _generate_model_description(model_id, display_name)

        models.append(ModelOption(id=model_id, name=display_name, description=description))

    return models


def _generate_model_description(model_id: str, display_name: str) -> str:
    """Generate a user-friendly description for a model.

    Args:
        model_id: The Ollama model identifier
        display_name: The user-friendly name

    Returns:
        A brief description of the model
    """
    model_lower = model_id.lower()

    # Known model descriptions
    descriptions = {
        "qwen2.5": "Fast and efficient. Great for quick tool operations.",
        "llama3.2": "Compact model with good reasoning. Ideal for general tasks.",
        "llama3.1": "More capable model. Better for complex tool chains.",
        "mistral": "Well-balanced performance. Good for diverse tasks.",
        "codellama": "Specialized for code-related tasks.",
        "deepseek": "Strong reasoning capabilities.",
        "phi": "Microsoft's efficient small model.",
        "gemma": "Google's open model family.",
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
            return AppConfigResponse(
                app_name=app_settings.app_name,  # App name always from env
                welcome_message=stored_settings.ui.welcome_message or app_settings.welcome_message,
                rate_limit_requests_per_minute=stored_settings.ui.rate_limit_requests_per_minute,
                rate_limit_concurrent_requests=stored_settings.ui.rate_limit_concurrent_requests,
                app_tag=stored_settings.ui.app_tag or app_settings.app_tag,
                app_repo_url=stored_settings.ui.app_repo_url or app_settings.app_repo_url,
                tools_provider_url=app_settings.tools_provider_external_url,
                allow_model_selection=stored_settings.llm.allow_model_selection,
                default_model=stored_settings.llm.ollama_model or app_settings.ollama_model,
                available_models=available_models,
            )
        else:
            # Use defaults from env vars
            available_models = parse_available_models(app_settings.available_models)
            return AppConfigResponse(
                app_name=app_settings.app_name,
                welcome_message=app_settings.welcome_message,
                rate_limit_requests_per_minute=app_settings.rate_limit_requests_per_minute,
                rate_limit_concurrent_requests=app_settings.rate_limit_concurrent_requests,
                app_tag=app_settings.app_tag,
                app_repo_url=app_settings.app_repo_url,
                tools_provider_url=app_settings.tools_provider_external_url,
                allow_model_selection=app_settings.allow_model_selection,
                default_model=app_settings.ollama_model,
                available_models=available_models,
            )
