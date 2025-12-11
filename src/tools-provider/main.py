"""Main application entry point with SubApp mounting."""

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from neuroglia.data.infrastructure.event_sourcing.abstractions import DeleteMode
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_ingestor import CloudEventIngestor
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_middleware import CloudEventMiddleware
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import CloudEventPublisher
from neuroglia.hosting.configuration.data_access_layer import DataAccessLayer
from neuroglia.hosting.web import SubAppConfig, WebApplicationBuilder
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from neuroglia.observability import Observability
from neuroglia.serialization.json import JsonSerializer

from api.services import DualAuthService
from api.services.openapi_config import configure_api_openapi, configure_mounted_apps_openapi_prefix
from application.services import ToolExecutor, configure_logging
from application.settings import app_settings
from domain.repositories import AccessPolicyDtoRepository, LabelDtoRepository, SourceDtoRepository, SourceToolDtoRepository, TaskDtoRepository, ToolGroupDtoRepository
from infrastructure import CircuitBreakerEventPublisher, KeycloakTokenExchanger, RedisCacheService
from integration.repositories import (
    MotorAccessPolicyDtoRepository,
    MotorLabelDtoRepository,
    MotorSourceDtoRepository,
    MotorSourceToolDtoRepository,
    MotorTaskDtoRepository,
    MotorToolGroupDtoRepository,
)

configure_logging(log_level=app_settings.log_level)
log = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Creates separate apps for:
    - API backend (/api prefix) - REST API for task management
    - UI frontend (/ prefix) - Web interface

    Returns:
        Configured FastAPI application with multiple mounted apps
    """
    log.debug("🚀 Creating Starter App application...")

    builder = WebApplicationBuilder(app_settings=app_settings)

    # Configure core services
    Mediator.configure(
        builder,
        [
            "application.commands",
            "application.queries",
            "application.events.domain",
            "application.events.integration",
        ],
    )
    Mapper.configure(
        builder,
        [
            "application.commands",
            "application.queries",
            "application.mapping",
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
    CloudEventIngestor.configure(builder, ["application.events.integration"])
    Observability.configure(builder)

    # Configure repositories for aggregates and read models
    DataAccessLayer.WriteModel(
        database_name=app_settings.database_name,
        consumer_group=app_settings.consumer_group,
        delete_mode=DeleteMode.HARD,
    ).configure(builder, ["domain.entities"])
    DataAccessLayer.ReadModel(
        database_name=app_settings.database_name,
        repository_type="motor",
        repository_mappings={
            TaskDtoRepository: MotorTaskDtoRepository,
            SourceDtoRepository: MotorSourceDtoRepository,
            SourceToolDtoRepository: MotorSourceToolDtoRepository,
            ToolGroupDtoRepository: MotorToolGroupDtoRepository,
            AccessPolicyDtoRepository: MotorAccessPolicyDtoRepository,
            LabelDtoRepository: MotorLabelDtoRepository,
        },
    ).configure(builder, ["integration.models", "application.events.domain"])

    # Configure authentication services (session store + auth service)
    DualAuthService.configure(builder)

    # Configure Tool Execution services (order matters - dependencies resolved from DI)
    RedisCacheService.configure(builder)  # Cache service (database 1, isolated from sessions)
    CircuitBreakerEventPublisher.configure(builder)  # Event publisher for circuit breaker state changes
    KeycloakTokenExchanger.configure(builder)  # Token exchange (depends on RedisCacheService, CircuitBreakerEventPublisher)
    ToolExecutor.configure(builder)  # Tool execution (depends on KeycloakTokenExchanger)

    # Add SubApp for API with controllers
    builder.add_sub_app(
        SubAppConfig(
            path="/api",
            name="api",
            title=f"{app_settings.app_name} API",
            description="Task management REST API with OAuth2/JWT authentication",
            version=app_settings.app_version,
            controllers=["api.controllers"],
            custom_setup=lambda app, service_provider: configure_api_openapi(app, app_settings),
            docs_url="/docs",
        )
    )

    # UI sub-app: Web interface serving static files built by Parcel
    # Get absolute path to static directory (same level as main.py)
    static_dir = Path(__file__).parent / "static"

    # Add SubApp for UI at root path
    builder.add_sub_app(
        SubAppConfig(
            path="/",
            name="ui",
            title=app_settings.app_name,
            controllers=["ui.controllers"],
            static_files={"/static": str(static_dir)},
            docs_url=None,  # Disable docs for UI
        )
    )

    # Build the application
    app = builder.build_app_with_lifespan(
        title="Starter App",
        description="Task management application with multi-app architecture",
        version="1.0.0",
        debug=True,
    )

    # Configure OpenAPI path prefixes for all mounted sub-apps
    configure_mounted_apps_openapi_prefix(app)

    # Configure middlewares
    DualAuthService.configure_middleware(app)
    app.add_middleware(CloudEventMiddleware, service_provider=app.state.services)

    if app_settings.enable_cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=app_settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Register shutdown handler for SSE connections
    # Note: Redis lifecycle is handled by RedisCacheService as a HostedService
    @app.on_event("shutdown")
    async def shutdown_sse_connections() -> None:
        """Gracefully close admin SSE connections on shutdown."""
        from api.controllers.admin_sse_controller import admin_sse_manager

        log.info("🛑 Shutting down SSE connections...")
        await admin_sse_manager.shutdown()
        log.info("✅ SSE connections closed")
        return

    log.info("✅ Application created successfully!")
    log.info("📊 Access points:")
    log.info("   - UI: http://localhost:8020/")
    log.info("   - API Docs: http://localhost:8020/api/docs")
    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:create_app",
        factory=True,
        host=app_settings.app_host,
        port=app_settings.app_port,
        reload=app_settings.debug,
        timeout_graceful_shutdown=5,  # Force-close SSE connections after 5s on reload/shutdown
    )
