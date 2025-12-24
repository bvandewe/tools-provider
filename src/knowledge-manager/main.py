"""Knowledge Manager - Main Application Entry Point.

A comprehensive knowledge management system for AI agents and applications,
built on the Neuroglia framework with CQRS and Clean Architecture.

Follows the same patterns as agent-host and tools-provider.
"""

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

from api.services.auth_service import DualAuthService
from api.services.openapi_config import configure_mounted_apps_openapi_prefix, setup_openapi
from application.settings import app_settings, configure_logging

# Domain entities (aggregates)
from domain.entities import KnowledgeNamespace

# Domain repository interfaces
from domain.repositories import KnowledgeNamespaceRepository

# Infrastructure
from infrastructure.session_store import RedisSessionStore

# Integration layer - Motor repository implementations
from integration.repositories import MotorKnowledgeNamespaceRepository

configure_logging(log_level=app_settings.log_level)
log = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the Knowledge Manager application.

    Creates separate apps for:
    - API backend (/api prefix) - REST API for knowledge management
    - UI frontend (/ prefix) - Web interface

    Returns:
        Configured FastAPI application with Neuroglia framework
    """
    log.debug("🚀 Creating Knowledge Manager application...")

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

    # ==========================================================================
    # Repository Configuration (MongoDB-only via MotorRepository)
    # ==========================================================================
    # All aggregates are persisted directly to MongoDB.
    # Domain events are still emitted via CloudEventPublisher for external consumers.
    # Query handlers read directly from aggregates and map to response models.
    #
    MotorRepository.configure(
        builder,
        entity_type=KnowledgeNamespace,
        key_type=str,
        database_name=app_settings.database_name,
        collection_name="namespaces",
        domain_repository_type=KnowledgeNamespaceRepository,
        implementation_type=MotorKnowledgeNamespaceRepository,
    )

    # Configure infrastructure services
    _configure_infrastructure_services(builder)

    # Add SubApp for API with controllers
    def api_sub_app_setup(app: FastAPI, settings) -> None:
        """Configure API sub-app with OpenAPI and auth dependencies."""
        # app.state.services is set by neuroglia before custom_setup is called
        app.state.auth_service = app.state.services.get_required_service(DualAuthService)
        # Configure OpenAPI
        setup_openapi(app, app_settings)

    builder.add_sub_app(
        SubAppConfig(
            path="/api",
            name="api",
            title=f"{app_settings.app_name} API",
            description="Knowledge Management API with OAuth2/JWT authentication",
            version=app_settings.app_version,
            controllers=["api.controllers"],
            custom_setup=api_sub_app_setup,
            docs_url="/docs",
        )
    )

    # UI sub-app: Web interface serving static files (same level as main.py)
    static_dir = Path(__file__).parent / "static"

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
        title="Knowledge Manager",
        description="Knowledge management system for AI agents",
        version=app_settings.app_version,
        debug=app_settings.debug,
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

    # Add health check endpoints
    _configure_health_endpoints(app)

    log.info("✅ Knowledge Manager application created successfully!")
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
        session_ttl=app_settings.session_timeout_hours * 3600,
        prefix=app_settings.redis_key_prefix,
    )
    builder.services.add_singleton(RedisSessionStore, singleton=session_store)

    # Auth Service
    auth_service = DualAuthService(
        session_store=session_store,
        settings=app_settings,
    )
    builder.services.add_singleton(DualAuthService, singleton=auth_service)

    log.info("✅ Infrastructure services configured")


def _configure_health_endpoints(app: FastAPI) -> None:
    """Add health check endpoints to the app.

    Args:
        app: FastAPI application
    """

    @app.get("/health", tags=["Health"])
    async def health_check():
        """Basic health check."""
        return {"status": "healthy", "service": "knowledge-manager"}

    @app.get("/health/ready", tags=["Health"])
    async def readiness_check():
        """Readiness check including dependencies."""
        checks = {"service": "ready"}

        # Check Redis
        try:
            session_store = app.state.services.get_required_service(RedisSessionStore)
            healthy = await session_store.health_check()
            checks["redis"] = "ready" if healthy else "not_ready"
        except Exception:
            checks["redis"] = "not_ready"

        all_ready = all(v == "ready" for v in checks.values())
        return {"status": "ready" if all_ready else "degraded", "checks": checks}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:create_app",
        factory=True,
        host=app_settings.app_host,
        port=app_settings.app_port,
        reload=app_settings.debug,
    )
