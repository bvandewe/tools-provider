"""Agent Host main application entry point with Neuroglia framework."""

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from neuroglia.data.infrastructure.mongo import MotorRepository
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_ingestor import CloudEventIngestor
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_middleware import CloudEventMiddleware
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import CloudEventPublisher
from neuroglia.hosting.web import SubAppConfig, WebApplicationBuilder
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from neuroglia.observability import Observability
from neuroglia.serialization.json import JsonSerializer

from api.services.auth_service import AuthService
from application.agents import ReActAgent
from application.services.chat_service import ChatService
from application.services.tool_provider_client import ToolProviderClient
from application.settings import app_settings, configure_logging
from domain.entities.conversation import Conversation
from domain.repositories import ConversationRepository
from infrastructure.adapters.ollama_llm_provider import OllamaLlmProvider
from infrastructure.session_store import RedisSessionStore
from integration.repositories import MotorConversationRepository

configure_logging(log_level=app_settings.log_level)
log = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the Agent Host application.
    Creates separate apps for:
    - API backend (/api prefix) - REST API for chat and conversations
    - UI frontend (/ prefix) - Web interface

    Returns:
        Configured FastAPI application with Neuroglia framework
    """
    log.debug("🚀 Creating Agent Host application...")

    builder = WebApplicationBuilder(app_settings=app_settings)

    # Configure core Neuroglia services
    Mediator.configure(
        builder,
        [
            "application.commands",
            "application.queries",
        ],
    )
    Mapper.configure(
        builder,
        [
            "application.commands",
            "application.queries",
            "integration.models",
        ],
    )
    JsonSerializer.configure(
        builder,
        [
            "domain.entities",
            "domain.models",
            "integration.models",
        ],
    )
    CloudEventPublisher.configure(builder)
    CloudEventIngestor.configure(builder, [])
    Observability.configure(builder)

    # Configure Conversation repositories
    MotorRepository.configure(
        builder,
        entity_type=Conversation,
        key_type=str,
        database_name="agent_host",
        collection_name="conversations",
        domain_repository_type=ConversationRepository,
        implementation_type=MotorConversationRepository,
    )

    # Configure infrastructure services
    _configure_infrastructure_services(builder)

    # Add SubApp for API with controllers
    builder.add_sub_app(
        SubAppConfig(
            path="/api",
            name="api",
            title=f"{app_settings.app_name} API",
            description="Chat API with OAuth2/JWT authentication",
            version=app_settings.app_version,
            controllers=["api.controllers"],
            docs_url="/docs",
        )
    )

    # UI sub-app: Web interface serving static files
    static_dir = Path(__file__).parent.parent / "static"

    builder.add_sub_app(
        SubAppConfig(
            path="/",
            name="ui",
            title=app_settings.app_name,
            controllers=["ui.controllers"],
            static_files={"/static": str(static_dir)},
            docs_url=None,
        )
    )

    # Build the application
    app = builder.build_app_with_lifespan(
        title="Agent Host",
        description="Chat interface for MCP Tools Provider with LLM integration",
        version=app_settings.app_version,
        debug=app_settings.debug,
    )

    # Configure middlewares
    AuthService.configure_middleware(app)
    app.add_middleware(CloudEventMiddleware, service_provider=app.state.services)

    if app_settings.enable_cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=app_settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    log.info("✅ Agent Host application created successfully!")
    log.info("📊 Access points:")
    log.info(f"   - UI: http://localhost:{app_settings.app_port}/")
    log.info(f"   - API Docs: http://localhost:{app_settings.app_port}/api/docs")
    return app


def _configure_infrastructure_services(builder: WebApplicationBuilder) -> None:
    """Configure infrastructure services in the DI container.

    Args:
        builder: The WebApplicationBuilder
    """
    log.info("🔧 Configuring infrastructure services...")

    # Redis Session Store
    session_store = RedisSessionStore(
        redis_url=app_settings.redis_url,
        session_timeout_seconds=app_settings.session_timeout_hours * 3600,
        key_prefix=app_settings.redis_key_prefix,
    )
    builder.services.add_singleton(RedisSessionStore, singleton=session_store)

    # Rate Limiter
    from infrastructure.rate_limiter import RateLimiter, set_rate_limiter

    rate_limiter = RateLimiter(
        session_store=session_store,
        requests_per_minute=app_settings.rate_limit_requests_per_minute,
        max_concurrent=app_settings.rate_limit_concurrent_requests,
    )
    set_rate_limiter(rate_limiter)
    builder.services.add_singleton(RateLimiter, singleton=rate_limiter)

    # Auth Service
    auth_service = AuthService(
        session_store=session_store,
        settings=app_settings,
    )
    builder.services.add_singleton(AuthService, singleton=auth_service)

    # Tool Provider Client
    tool_provider_client = ToolProviderClient(
        base_url=app_settings.tools_provider_url,
        timeout=app_settings.tools_provider_timeout,
    )
    builder.services.add_singleton(ToolProviderClient, singleton=tool_provider_client)

    # ==========================================================================
    # LLM Provider Configuration (multi-provider support)
    # ==========================================================================
    # Configure available LLM providers based on settings
    # The LlmProviderFactory handles runtime provider selection

    # 1. Configure Ollama (if enabled)
    if app_settings.ollama_enabled:
        OllamaLlmProvider.configure(builder)

    # 2. Configure OpenAI (if enabled)
    if app_settings.openai_enabled:
        from infrastructure.adapters.openai_llm_provider import OpenAiLlmProvider
        from infrastructure.openai_token_cache import OpenAiTokenCache, set_openai_token_cache

        # Initialize token cache for OAuth2 mode
        token_cache = None
        if app_settings.openai_auth_type == "oauth2":
            token_cache = OpenAiTokenCache(
                redis_url=app_settings.redis_url,
                default_ttl_seconds=app_settings.openai_oauth_token_ttl,
            )
            set_openai_token_cache(token_cache)
            builder.services.add_singleton(OpenAiTokenCache, singleton=token_cache)

        OpenAiLlmProvider.configure(builder, token_cache=token_cache)

    # 3. Configure LLM Provider Factory (manages provider selection)
    from infrastructure.llm_provider_factory import LlmProviderFactory, set_provider_factory

    factory = LlmProviderFactory.configure(builder)
    set_provider_factory(factory)

    # ==========================================================================
    # Agent Configuration
    # ==========================================================================
    # ReActAgent is the default implementation using ReAct pattern
    # (Reasoning + Acting in a loop with tool calling)
    ReActAgent.configure(builder)

    # ==========================================================================
    # ChatService (scoped - created per request with repository)
    # ==========================================================================
    ChatService.configure(builder)

    log.info("✅ Infrastructure services configured")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:create_app",
        factory=True,
        host=app_settings.app_host,
        port=app_settings.app_port,
        reload=app_settings.debug,
    )
