"""Settings controller for admin settings management."""

import logging
from datetime import datetime
from typing import Any, Optional

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
    size: Optional[int] = None
    digest: Optional[str] = None
    modified_at: Optional[str] = None
    details: Optional[dict[str, Any]] = None


class LlmSettingsRequest(BaseModel):
    """LLM settings update request."""

    ollama_url: Optional[str] = None
    ollama_model: Optional[str] = None
    ollama_timeout: Optional[float] = None
    ollama_stream: Optional[bool] = None
    ollama_temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    ollama_top_p: Optional[float] = Field(None, ge=0.0, le=1.0)
    ollama_num_ctx: Optional[int] = Field(None, ge=512)
    allow_model_selection: Optional[bool] = None
    available_models: Optional[str] = None


class AgentSettingsRequest(BaseModel):
    """Agent settings update request."""

    agent_name: Optional[str] = None
    max_iterations: Optional[int] = Field(None, ge=1, le=50)
    max_tool_calls_per_iteration: Optional[int] = Field(None, ge=1, le=20)
    stop_on_error: Optional[bool] = None
    retry_on_error: Optional[bool] = None
    max_retries: Optional[int] = Field(None, ge=0, le=10)
    timeout_seconds: Optional[float] = Field(None, ge=30.0, le=600.0)
    system_prompt: Optional[str] = None


class UiSettingsRequest(BaseModel):
    """UI settings update request."""

    welcome_message: Optional[str] = None
    rate_limit_requests_per_minute: Optional[int] = Field(None, ge=1, le=100)
    rate_limit_concurrent_requests: Optional[int] = Field(None, ge=1, le=10)
    app_tag: Optional[str] = None
    app_repo_url: Optional[str] = None


class AppSettingsRequest(BaseModel):
    """Full application settings update request."""

    llm: Optional[LlmSettingsRequest] = None
    agent: Optional[AgentSettingsRequest] = None
    ui: Optional[UiSettingsRequest] = None


class LlmSettingsResponse(BaseModel):
    """LLM settings response."""

    ollama_url: str
    ollama_model: str
    ollama_timeout: float
    ollama_stream: bool
    ollama_temperature: float
    ollama_top_p: float
    ollama_num_ctx: int
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
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    is_default: bool = False  # True if using defaults (no stored settings)


# =============================================================================
# Helper Functions
# =============================================================================


def get_default_settings() -> AppSettingsDto:
    """Get default settings from application settings (env vars)."""
    return AppSettingsDto(
        llm=LlmSettingsDto(
            ollama_url=app_settings.ollama_url,
            ollama_model=app_settings.ollama_model,
            ollama_timeout=app_settings.ollama_timeout,
            ollama_stream=app_settings.ollama_stream,
            ollama_temperature=app_settings.ollama_temperature,
            ollama_top_p=app_settings.ollama_top_p,
            ollama_num_ctx=app_settings.ollama_num_ctx,
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
            ollama_url=dto.llm.ollama_url,
            ollama_model=dto.llm.ollama_model,
            ollama_timeout=dto.llm.ollama_timeout,
            ollama_stream=dto.llm.ollama_stream,
            ollama_temperature=dto.llm.ollama_temperature,
            ollama_top_p=dto.llm.ollama_top_p,
            ollama_num_ctx=dto.llm.ollama_num_ctx,
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

        logger.info(f"Settings updated by {username}")
        return dto_to_response(saved, is_default=False)

    @delete("/")
    async def reset_settings(self, user: dict = Depends(require_admin)) -> AppSettingsResponse:
        """
        Reset settings to defaults.

        Deletes stored settings from MongoDB, reverting to environment variable defaults.
        Requires admin role.
        """
        service = get_settings_service()
        await service.delete_settings_async()

        username = user.get("preferred_username") or user.get("name") or user.get("sub", "unknown")
        logger.info(f"Settings reset to defaults by {username}")

        return dto_to_response(get_default_settings(), is_default=True)

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
