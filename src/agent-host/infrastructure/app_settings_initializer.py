"""Application Settings Service.

This module provides a hosted service that manages application settings in MongoDB.
It ensures default settings exist on startup, initializing them from environment
configuration if needed.

Implements HostedService for proper lifecycle management:
- start_async(): Called on application startup to ensure settings exist
- stop_async(): Called on application shutdown (no-op for this service)

This ensures that:
1. The settings service always has a document to return
2. Environment variables are used as the initial values
3. Subsequent changes via the UI will override these defaults
"""

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from neuroglia.hosting.abstractions import HostedService

from application.settings import app_settings
from infrastructure.app_settings_service import get_settings_service
from integration.models.app_settings_dto import AgentSettingsDto, AppSettingsDto, LlmSettingsDto, UiSettingsDto

if TYPE_CHECKING:
    from neuroglia.hosting.web import WebApplicationBuilder

logger = logging.getLogger(__name__)


class AppSettingsInitializer(HostedService):
    """Hosted service that initializes app settings in MongoDB on startup.

    Implements HostedService for automatic lifecycle management:
    - start_async(): Called on application startup to ensure settings exist
    - stop_async(): Called on application shutdown (cleanup if needed)

    This service checks if settings exist in MongoDB and creates default
    settings from environment configuration if they don't exist.
    """

    def __init__(self) -> None:
        """Initialize the settings initializer."""
        self._initialized = False

    # =========================================================================
    # HostedService Lifecycle Methods
    # =========================================================================

    async def start_async(self) -> None:
        """Start the service by ensuring settings exist in MongoDB.

        Called automatically by the Neuroglia host during application startup.
        Creates default settings from environment configuration if none exist.
        """
        try:
            await self._initialize_settings()
            self._initialized = True
            logger.info("✅ AppSettingsInitializer started")
        except Exception as e:
            logger.error(f"❌ AppSettingsInitializer failed: {e}")
            # Don't raise - the app can still function with env defaults
            # The settings service will return None and callers handle it

    async def stop_async(self) -> None:
        """Stop the service.

        Called automatically by the Neuroglia host during application shutdown.
        No cleanup needed for this service.
        """
        logger.info("✅ AppSettingsInitializer stopped")

    # =========================================================================
    # Settings Initialization
    # =========================================================================

    async def _initialize_settings(self) -> AppSettingsDto | None:
        """Initialize application settings in MongoDB if they don't exist.

        Returns:
            The existing or newly created AppSettingsDto, or None on error
        """
        settings_service = get_settings_service()

        # Check if settings already exist
        existing = await settings_service.get_settings_async(use_cache=False)
        if existing is not None:
            logger.info("✅ App settings already exist in MongoDB")
            return existing

        # Create default settings from environment variables
        logger.info("📝 Creating default app settings from environment configuration...")

        default_settings = AppSettingsDto(
            id="app_settings",
            llm=LlmSettingsDto(
                # Ollama settings from env
                ollama_enabled=app_settings.ollama_enabled,
                ollama_url=app_settings.ollama_url,
                ollama_model=app_settings.ollama_model,
                ollama_timeout=app_settings.ollama_timeout,
                ollama_stream=app_settings.ollama_stream,
                ollama_temperature=app_settings.ollama_temperature,
                ollama_top_p=app_settings.ollama_top_p,
                ollama_num_ctx=app_settings.ollama_num_ctx,
                # OpenAI settings from env
                openai_enabled=app_settings.openai_enabled,
                openai_api_endpoint=app_settings.openai_api_endpoint,
                openai_api_version=app_settings.openai_api_version,
                openai_model=app_settings.openai_model,
                openai_timeout=app_settings.openai_timeout,
                openai_temperature=app_settings.openai_temperature,
                openai_top_p=app_settings.openai_top_p,
                openai_max_tokens=app_settings.openai_max_tokens,
                openai_auth_type=app_settings.openai_auth_type,
                openai_api_key=app_settings.openai_api_key,
                openai_oauth_endpoint=app_settings.openai_oauth_endpoint,
                openai_oauth_client_id=app_settings.openai_oauth_client_id,
                openai_oauth_client_secret=app_settings.openai_oauth_client_secret,
                openai_oauth_token_ttl=app_settings.openai_oauth_token_ttl,
                openai_app_key=app_settings.openai_app_key,
                openai_client_id_header=app_settings.openai_client_id_header,
                # Default provider
                default_llm_provider="ollama" if app_settings.ollama_enabled else "openai",
                allow_model_selection=True,
                available_models="",  # Will be populated by model discovery
            ),
            agent=AgentSettingsDto(
                agent_name="assistant",
                max_iterations=10,
                max_tool_calls_per_iteration=5,
                stop_on_error=False,
                retry_on_error=True,
                max_retries=2,
                timeout_seconds=300.0,
                system_prompt="",  # Use session-type-specific prompts
            ),
            ui=UiSettingsDto(
                welcome_message="Your AI assistant with access to powerful tools.",
                rate_limit_requests_per_minute=app_settings.rate_limit_requests_per_minute,
                rate_limit_concurrent_requests=app_settings.rate_limit_concurrent_requests,
                app_tag=app_settings.app_tag,
                app_repo_url=app_settings.app_repo_url,
            ),
            updated_at=datetime.now(UTC),
            updated_by="system_initializer",
        )

        # Save to MongoDB
        saved_settings = await settings_service.save_settings_async(default_settings, "system_initializer")
        logger.info("✅ Default app settings created in MongoDB")

        return saved_settings

    # =========================================================================
    # Configuration
    # =========================================================================

    @staticmethod
    def configure(builder: "WebApplicationBuilder") -> "WebApplicationBuilder":
        """Configure and register the app settings initializer service.

        This method follows the Neuroglia pattern for service configuration,
        registering AppSettingsInitializer as a HostedService for automatic
        lifecycle management.

        The HostedService registration ensures start_async() is called during
        application startup.

        Args:
            builder: WebApplicationBuilder instance for service registration

        Returns:
            The builder instance for fluent chaining
        """
        logger.info("🔧 Configuring AppSettingsInitializer...")

        initializer = AppSettingsInitializer()

        # Register as HostedService for lifecycle management (start_async/stop_async)
        builder.services.add_singleton(HostedService, singleton=initializer)

        # Also register as singleton for DI if needed
        builder.services.add_singleton(AppSettingsInitializer, singleton=initializer)

        logger.info("✅ AppSettingsInitializer configured")
        return builder
