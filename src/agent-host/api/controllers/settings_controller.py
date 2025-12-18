"""Settings controller for admin settings management."""

import logging
from datetime import datetime
from typing import Any

from classy_fastapi.decorators import delete, get, put
from fastapi import Depends, HTTPException, status
from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from neuroglia.mvc import ControllerBase
from pydantic import BaseModel, Field

from api.dependencies import require_admin
from application.settings import app_settings
from infrastructure.app_settings_service import get_settings_service
from integration.models.app_settings_dto import AgentSettingsDto, AppSettingsDto, LlmSettingsDto, UiSettingsDto

logger = logging.getLogger(__name__)


# =============================================================================
# Request/Response Models
# =============================================================================


class OllamaModelInfo(BaseModel):
    """Information about an available Ollama model."""

    name: str
    model: str
    size: int | None = None
    digest: str | None = None
    modified_at: str | None = None
    details: dict[str, Any] | None = None


class LlmSettingsRequest(BaseModel):
    """LLM settings update request."""

    # Default provider
    default_llm_provider: str | None = None

    # Ollama settings
    ollama_enabled: bool | None = None
    ollama_url: str | None = None
    ollama_model: str | None = None
    ollama_timeout: float | None = None
    ollama_stream: bool | None = None
    ollama_temperature: float | None = Field(None, ge=0.0, le=2.0)
    ollama_top_p: float | None = Field(None, ge=0.0, le=1.0)
    ollama_num_ctx: int | None = Field(None, ge=512)

    # OpenAI settings
    openai_enabled: bool | None = None
    openai_api_endpoint: str | None = None
    openai_api_version: str | None = None
    openai_model: str | None = None
    openai_timeout: float | None = None
    openai_temperature: float | None = Field(None, ge=0.0, le=2.0)
    openai_top_p: float | None = Field(None, ge=0.0, le=1.0)
    openai_max_tokens: int | None = Field(None, ge=256)

    # OpenAI auth
    openai_auth_type: str | None = None
    openai_api_key: str | None = None
    openai_oauth_endpoint: str | None = None
    openai_oauth_client_id: str | None = None
    openai_oauth_client_secret: str | None = None
    openai_oauth_token_ttl: int | None = None

    # OpenAI custom headers
    openai_app_key: str | None = None
    openai_client_id_header: str | None = None

    # Model selection
    allow_model_selection: bool | None = None
    available_models: str | None = None


class AgentSettingsRequest(BaseModel):
    """Agent settings update request."""

    agent_name: str | None = None
    max_iterations: int | None = Field(None, ge=1, le=50)
    max_tool_calls_per_iteration: int | None = Field(None, ge=1, le=20)
    stop_on_error: bool | None = None
    retry_on_error: bool | None = None
    max_retries: int | None = Field(None, ge=0, le=10)
    timeout_seconds: float | None = Field(None, ge=30.0, le=600.0)
    system_prompt: str | None = None


class UiSettingsRequest(BaseModel):
    """UI settings update request."""

    welcome_message: str | None = None
    rate_limit_requests_per_minute: int | None = Field(None, ge=1, le=100)
    rate_limit_concurrent_requests: int | None = Field(None, ge=1, le=10)
    app_tag: str | None = None
    app_repo_url: str | None = None


class AppSettingsRequest(BaseModel):
    """Full application settings update request."""

    llm: LlmSettingsRequest | None = None
    agent: AgentSettingsRequest | None = None
    ui: UiSettingsRequest | None = None


class LlmSettingsResponse(BaseModel):
    """LLM settings response."""

    # Default provider
    default_llm_provider: str

    # Ollama settings
    ollama_enabled: bool
    ollama_url: str
    ollama_model: str
    ollama_timeout: float
    ollama_stream: bool
    ollama_temperature: float
    ollama_top_p: float
    ollama_num_ctx: int

    # OpenAI settings
    openai_enabled: bool
    openai_api_endpoint: str
    openai_api_version: str
    openai_model: str
    openai_timeout: float
    openai_temperature: float
    openai_top_p: float
    openai_max_tokens: int

    # OpenAI auth
    openai_auth_type: str
    openai_api_key: str
    openai_oauth_endpoint: str
    openai_oauth_client_id: str
    openai_oauth_client_secret: str
    openai_oauth_token_ttl: int

    # OpenAI custom headers
    openai_app_key: str
    openai_client_id_header: str

    # Model selection
    allow_model_selection: bool
    available_models: str


class AgentSettingsResponse(BaseModel):
    """Agent settings response."""

    agent_name: str
    max_iterations: int
    max_tool_calls_per_iteration: int
    stop_on_error: bool
    retry_on_error: bool
    max_retries: int
    timeout_seconds: float
    system_prompt: str


class UiSettingsResponse(BaseModel):
    """UI settings response."""

    welcome_message: str
    rate_limit_requests_per_minute: int
    rate_limit_concurrent_requests: int
    app_tag: str
    app_repo_url: str


class AppSettingsResponse(BaseModel):
    """Full application settings response."""

    llm: LlmSettingsResponse
    agent: AgentSettingsResponse
    ui: UiSettingsResponse
    updated_at: datetime | None = None
    updated_by: str | None = None
    is_default: bool = False  # True if using defaults (no stored settings)


# =============================================================================
# Helper Functions
# =============================================================================


def get_default_settings() -> AppSettingsDto:
    """Get default settings from application settings (env vars)."""
    return AppSettingsDto(
        llm=LlmSettingsDto(
            # Default provider
            default_llm_provider=app_settings.default_llm_provider,
            # Ollama settings
            ollama_enabled=app_settings.ollama_enabled,
            ollama_url=app_settings.ollama_url,
            ollama_model=app_settings.ollama_model,
            ollama_timeout=app_settings.ollama_timeout,
            ollama_stream=app_settings.ollama_stream,
            ollama_temperature=app_settings.ollama_temperature,
            ollama_top_p=app_settings.ollama_top_p,
            ollama_num_ctx=app_settings.ollama_num_ctx,
            # OpenAI settings
            openai_enabled=app_settings.openai_enabled,
            openai_api_endpoint=app_settings.openai_api_endpoint,
            openai_api_version=app_settings.openai_api_version,
            openai_model=app_settings.openai_model,
            openai_timeout=app_settings.openai_timeout,
            openai_temperature=app_settings.openai_temperature,
            openai_top_p=app_settings.openai_top_p,
            openai_max_tokens=app_settings.openai_max_tokens,
            # OpenAI auth
            openai_auth_type=app_settings.openai_auth_type,
            openai_api_key=app_settings.openai_api_key,
            openai_oauth_endpoint=app_settings.openai_oauth_endpoint,
            openai_oauth_client_id=app_settings.openai_oauth_client_id,
            openai_oauth_client_secret=app_settings.openai_oauth_client_secret,
            openai_oauth_token_ttl=app_settings.openai_oauth_token_ttl,
            # OpenAI custom headers
            openai_app_key=app_settings.openai_app_key,
            openai_client_id_header=app_settings.openai_client_id_header,
            # Model selection
            allow_model_selection=app_settings.allow_model_selection,
            available_models=app_settings.available_models,
        ),
        agent=AgentSettingsDto(
            agent_name=app_settings.agent_name,
            max_iterations=app_settings.agent_max_iterations,
            max_tool_calls_per_iteration=app_settings.agent_max_tool_calls_per_iteration,
            stop_on_error=app_settings.agent_stop_on_error,
            retry_on_error=app_settings.agent_retry_on_error,
            max_retries=app_settings.agent_max_retries,
            timeout_seconds=app_settings.agent_timeout_seconds,
            system_prompt=app_settings.system_prompt,
        ),
        ui=UiSettingsDto(
            welcome_message=app_settings.welcome_message,
            rate_limit_requests_per_minute=app_settings.rate_limit_requests_per_minute,
            rate_limit_concurrent_requests=app_settings.rate_limit_concurrent_requests,
            app_tag=app_settings.app_tag,
            app_repo_url=app_settings.app_repo_url,
        ),
    )


def dto_to_response(dto: AppSettingsDto, is_default: bool = False) -> AppSettingsResponse:
    """Convert AppSettingsDto to AppSettingsResponse."""
    return AppSettingsResponse(
        llm=LlmSettingsResponse(
            # Default provider
            default_llm_provider=dto.llm.default_llm_provider,
            # Ollama settings
            ollama_enabled=dto.llm.ollama_enabled,
            ollama_url=dto.llm.ollama_url,
            ollama_model=dto.llm.ollama_model,
            ollama_timeout=dto.llm.ollama_timeout,
            ollama_stream=dto.llm.ollama_stream,
            ollama_temperature=dto.llm.ollama_temperature,
            ollama_top_p=dto.llm.ollama_top_p,
            ollama_num_ctx=dto.llm.ollama_num_ctx,
            # OpenAI settings
            openai_enabled=dto.llm.openai_enabled,
            openai_api_endpoint=dto.llm.openai_api_endpoint,
            openai_api_version=dto.llm.openai_api_version,
            openai_model=dto.llm.openai_model,
            openai_timeout=dto.llm.openai_timeout,
            openai_temperature=dto.llm.openai_temperature,
            openai_top_p=dto.llm.openai_top_p,
            openai_max_tokens=dto.llm.openai_max_tokens,
            # OpenAI auth
            openai_auth_type=dto.llm.openai_auth_type,
            openai_api_key=dto.llm.openai_api_key,
            openai_oauth_endpoint=dto.llm.openai_oauth_endpoint,
            openai_oauth_client_id=dto.llm.openai_oauth_client_id,
            openai_oauth_client_secret=dto.llm.openai_oauth_client_secret,
            openai_oauth_token_ttl=dto.llm.openai_oauth_token_ttl,
            # OpenAI custom headers
            openai_app_key=dto.llm.openai_app_key,
            openai_client_id_header=dto.llm.openai_client_id_header,
            # Model selection
            allow_model_selection=dto.llm.allow_model_selection,
            available_models=dto.llm.available_models,
        ),
        agent=AgentSettingsResponse(
            agent_name=dto.agent.agent_name,
            max_iterations=dto.agent.max_iterations,
            max_tool_calls_per_iteration=dto.agent.max_tool_calls_per_iteration,
            stop_on_error=dto.agent.stop_on_error,
            retry_on_error=dto.agent.retry_on_error,
            max_retries=dto.agent.max_retries,
            timeout_seconds=dto.agent.timeout_seconds,
            system_prompt=dto.agent.system_prompt,
        ),
        ui=UiSettingsResponse(
            welcome_message=dto.ui.welcome_message,
            rate_limit_requests_per_minute=dto.ui.rate_limit_requests_per_minute,
            rate_limit_concurrent_requests=dto.ui.rate_limit_concurrent_requests,
            app_tag=dto.ui.app_tag,
            app_repo_url=dto.ui.app_repo_url,
        ),
        updated_at=dto.updated_at,
        updated_by=dto.updated_by,
        is_default=is_default,
    )


# =============================================================================
# Controller
# =============================================================================


class SettingsController(ControllerBase):
    """Controller for admin settings management.

    All endpoints require admin role.
    Settings are stored in MongoDB and override default application settings.
    """

    def __init__(self, service_provider: ServiceProviderBase, mapper: Mapper, mediator: Mediator):
        super().__init__(service_provider, mapper, mediator)

    @get("/")
    async def get_settings(self, user: dict = Depends(require_admin)) -> AppSettingsResponse:
        """
        Get current application settings.

        Returns stored settings from MongoDB, or defaults if no settings are stored.
        Requires admin role.
        """
        service = get_settings_service()
        stored_settings = await service.get_settings_async()

        if stored_settings:
            return dto_to_response(stored_settings, is_default=False)
        else:
            # Return defaults
            return dto_to_response(get_default_settings(), is_default=True)

    @put("/")
    async def update_settings(self, request: AppSettingsRequest, user: dict = Depends(require_admin)) -> AppSettingsResponse:
        """
        Update application settings.

        Merges provided settings with existing settings and saves to MongoDB.
        Requires admin role.
        """
        service = get_settings_service()

        # Get current settings or defaults
        current = await service.get_settings_async()
        if not current:
            current = get_default_settings()

        # Merge LLM settings
        if request.llm:
            # Default provider
            if request.llm.default_llm_provider is not None:
                current.llm.default_llm_provider = request.llm.default_llm_provider

            # Ollama settings
            if request.llm.ollama_enabled is not None:
                current.llm.ollama_enabled = request.llm.ollama_enabled
            if request.llm.ollama_url is not None:
                current.llm.ollama_url = request.llm.ollama_url
            if request.llm.ollama_model is not None:
                current.llm.ollama_model = request.llm.ollama_model
            if request.llm.ollama_timeout is not None:
                current.llm.ollama_timeout = request.llm.ollama_timeout
            if request.llm.ollama_stream is not None:
                current.llm.ollama_stream = request.llm.ollama_stream
            if request.llm.ollama_temperature is not None:
                current.llm.ollama_temperature = request.llm.ollama_temperature
            if request.llm.ollama_top_p is not None:
                current.llm.ollama_top_p = request.llm.ollama_top_p
            if request.llm.ollama_num_ctx is not None:
                current.llm.ollama_num_ctx = request.llm.ollama_num_ctx

            # OpenAI settings
            if request.llm.openai_enabled is not None:
                current.llm.openai_enabled = request.llm.openai_enabled
            if request.llm.openai_api_endpoint is not None:
                current.llm.openai_api_endpoint = request.llm.openai_api_endpoint
            if request.llm.openai_api_version is not None:
                current.llm.openai_api_version = request.llm.openai_api_version
            if request.llm.openai_model is not None:
                current.llm.openai_model = request.llm.openai_model
            if request.llm.openai_timeout is not None:
                current.llm.openai_timeout = request.llm.openai_timeout
            if request.llm.openai_temperature is not None:
                current.llm.openai_temperature = request.llm.openai_temperature
            if request.llm.openai_top_p is not None:
                current.llm.openai_top_p = request.llm.openai_top_p
            if request.llm.openai_max_tokens is not None:
                current.llm.openai_max_tokens = request.llm.openai_max_tokens

            # OpenAI auth
            if request.llm.openai_auth_type is not None:
                current.llm.openai_auth_type = request.llm.openai_auth_type
            if request.llm.openai_api_key is not None:
                current.llm.openai_api_key = request.llm.openai_api_key
            if request.llm.openai_oauth_endpoint is not None:
                current.llm.openai_oauth_endpoint = request.llm.openai_oauth_endpoint
            if request.llm.openai_oauth_client_id is not None:
                current.llm.openai_oauth_client_id = request.llm.openai_oauth_client_id
            if request.llm.openai_oauth_client_secret is not None:
                current.llm.openai_oauth_client_secret = request.llm.openai_oauth_client_secret
            if request.llm.openai_oauth_token_ttl is not None:
                current.llm.openai_oauth_token_ttl = request.llm.openai_oauth_token_ttl

            # OpenAI custom headers
            if request.llm.openai_app_key is not None:
                current.llm.openai_app_key = request.llm.openai_app_key
            if request.llm.openai_client_id_header is not None:
                current.llm.openai_client_id_header = request.llm.openai_client_id_header

            # Model selection
            if request.llm.allow_model_selection is not None:
                current.llm.allow_model_selection = request.llm.allow_model_selection
            if request.llm.available_models is not None:
                current.llm.available_models = request.llm.available_models

        # Merge Agent settings
        if request.agent:
            if request.agent.agent_name is not None:
                current.agent.agent_name = request.agent.agent_name
            if request.agent.max_iterations is not None:
                current.agent.max_iterations = request.agent.max_iterations
            if request.agent.max_tool_calls_per_iteration is not None:
                current.agent.max_tool_calls_per_iteration = request.agent.max_tool_calls_per_iteration
            if request.agent.stop_on_error is not None:
                current.agent.stop_on_error = request.agent.stop_on_error
            if request.agent.retry_on_error is not None:
                current.agent.retry_on_error = request.agent.retry_on_error
            if request.agent.max_retries is not None:
                current.agent.max_retries = request.agent.max_retries
            if request.agent.timeout_seconds is not None:
                current.agent.timeout_seconds = request.agent.timeout_seconds
            if request.agent.system_prompt is not None:
                current.agent.system_prompt = request.agent.system_prompt

        # Merge UI settings
        if request.ui:
            if request.ui.welcome_message is not None:
                current.ui.welcome_message = request.ui.welcome_message
            if request.ui.rate_limit_requests_per_minute is not None:
                current.ui.rate_limit_requests_per_minute = request.ui.rate_limit_requests_per_minute
            if request.ui.rate_limit_concurrent_requests is not None:
                current.ui.rate_limit_concurrent_requests = request.ui.rate_limit_concurrent_requests
            if request.ui.app_tag is not None:
                current.ui.app_tag = request.ui.app_tag
            if request.ui.app_repo_url is not None:
                current.ui.app_repo_url = request.ui.app_repo_url

        # Save to MongoDB
        username = user.get("preferred_username") or user.get("name") or user.get("sub", "unknown")
        saved = await service.save_settings_async(current, updated_by=username)

        # Reconfigure LLM providers with new settings (applies at runtime)
        await self._reconfigure_providers(saved)

        logger.info(f"Settings updated by {username}")
        return dto_to_response(saved, is_default=False)

    async def _reconfigure_providers(self, settings: AppSettingsDto) -> None:
        """Reconfigure LLM providers with updated settings.

        This applies settings changes at runtime without requiring a restart.

        Args:
            settings: The updated settings DTO
        """
        from infrastructure import get_provider_factory

        factory = get_provider_factory()
        if not factory:
            logger.warning("LlmProviderFactory not available, skipping provider reconfiguration")
            return

        # Reconfigure Ollama provider
        from application.agents import LlmProviderType
        from infrastructure.adapters.ollama_llm_provider import OllamaLlmProvider

        ollama = factory.get_provider(LlmProviderType.OLLAMA)
        if ollama and isinstance(ollama, OllamaLlmProvider):
            try:
                await ollama.reconfigure_from_settings(settings.llm)
            except Exception as e:
                logger.error(f"Failed to reconfigure Ollama provider: {e}")

        # Reconfigure OpenAI provider
        from infrastructure.adapters.openai_llm_provider import OpenAiLlmProvider

        openai = factory.get_provider(LlmProviderType.OPENAI)
        if openai and isinstance(openai, OpenAiLlmProvider):
            try:
                await openai.reconfigure_from_settings(settings.llm)
            except Exception as e:
                logger.error(f"Failed to reconfigure OpenAI provider: {e}")

        # Update default provider in factory
        try:
            new_default = LlmProviderType(settings.llm.default_llm_provider)
            factory.default_provider_type = new_default
            logger.info(f"Updated default LLM provider to: {new_default.value}")
        except ValueError:
            logger.warning(f"Unknown default_llm_provider: {settings.llm.default_llm_provider}")

    @delete("/")
    async def reset_settings(self, user: dict = Depends(require_admin)) -> AppSettingsResponse:
        """
        Reset settings to defaults.

        Deletes stored settings from MongoDB, reverting to environment variable defaults.
        Requires admin role.
        """
        service = get_settings_service()
        await service.delete_settings_async()

        # Get and apply default settings to providers
        default_settings = get_default_settings()
        await self._reconfigure_providers(default_settings)

        username = user.get("preferred_username") or user.get("name") or user.get("sub", "unknown")
        logger.info(f"Settings reset to defaults by {username}")

        return dto_to_response(default_settings, is_default=True)

    @get("/ollama/models")
    async def get_ollama_models(self, user: dict = Depends(require_admin)) -> list[OllamaModelInfo]:
        """
        Get available Ollama models.

        Fetches the list of models available in the configured Ollama instance.
        Requires admin role.
        """
        import httpx

        service = get_settings_service()
        stored_settings = await service.get_settings_async()
        ollama_url = stored_settings.llm.ollama_url if stored_settings else app_settings.ollama_url

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{ollama_url}/api/tags")
                response.raise_for_status()
                data = response.json()

                models = []
                for model_data in data.get("models", []):
                    models.append(
                        OllamaModelInfo(
                            name=model_data.get("name", ""),
                            model=model_data.get("model", ""),
                            size=model_data.get("size"),
                            digest=model_data.get("digest"),
                            modified_at=model_data.get("modified_at"),
                            details=model_data.get("details"),
                        )
                    )
                return models

        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Ollama at {ollama_url}: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Failed to connect to Ollama at {ollama_url}",
            )
        except Exception as e:
            logger.error(f"Error fetching Ollama models: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch Ollama models",
            )
