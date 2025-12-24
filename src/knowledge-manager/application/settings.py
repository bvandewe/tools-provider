"""Application settings configuration for Knowledge Manager.

Following the same pattern as tools-provider with full observability support.
"""

import logging
import sys

from neuroglia.hosting.abstractions import ApplicationSettings


class Settings(ApplicationSettings):
    """Application settings with Keycloak OAuth2/OIDC configuration and observability."""

    # Debugging Configuration
    debug: bool = True
    environment: str = "development"  # development, production
    log_level: str = "INFO"

    # Application Configuration
    app_name: str = "Knowledge Manager"
    app_version: str = "0.1.0"
    app_url: str = "http://localhost:8060"  # External URL for callbacks
    app_host: str = "127.0.0.1"  # Uvicorn bind address
    app_port: int = 8060  # Uvicorn port

    # Database Configuration
    database_name: str = "knowledge_manager"
    consumer_group: str = "knowledge-manager-consumer-group"

    # Connection Strings - override from ApplicationSettings base class
    # Set via CONNECTION_STRINGS env var as JSON (no prefix):
    # {"mongo": "mongodb://..."}
    # Docker: uses mongodb:27017 (internal network)
    connection_strings: dict[str, str] = {"mongo": "mongodb://root:password123@mongodb:27017/?authSource=admin"}  # pragma: allowlist secret

    def get_connection_strings(self) -> dict[str, str]:
        """Get connection strings with 'mongodb' key for backward compatibility.

        The framework uses 'mongo' key, but some code may expect 'mongodb'.

        Returns:
            Connection strings dict with both 'mongo' and 'mongodb' keys
        """
        result = dict(self.connection_strings)
        # Ensure both keys exist for compatibility
        if "mongo" in result and "mongodb" not in result:
            result["mongodb"] = result["mongo"]
        return result

    # Observability Configuration
    service_name: str = "knowledge-manager"
    service_version: str = app_version
    deployment_environment: str = "development"

    observability_enabled: bool = True
    observability_metrics_enabled: bool = True
    observability_tracing_enabled: bool = True
    observability_logging_enabled: bool = True
    observability_health_endpoint: bool = True
    observability_metrics_endpoint: bool = True
    observability_ready_endpoint: bool = True
    observability_health_path: str = "/health"
    observability_metrics_path: str = "/metrics"
    observability_ready_path: str = "/ready"
    observability_health_checks: list[str] = []

    otel_enabled: bool = True
    otel_endpoint: str = "http://otel-collector:4317"
    otel_protocol: str = "grpc"
    otel_timeout: int = 10
    otel_console_export: bool = False
    otel_batch_max_queue_size: int = 2048
    otel_batch_schedule_delay_ms: int = 5000
    otel_batch_max_export_size: int = 512
    otel_metrics_interval_ms: int = 60000
    otel_metrics_timeout_ms: int = 30000
    otel_instrument_fastapi: bool = True
    otel_instrument_httpx: bool = True
    otel_instrument_logging: bool = True
    otel_instrument_system_metrics: bool = True
    otel_resource_attributes: dict = {}

    # Session Configuration
    session_secret_key: str = "change-me-in-production-use-secrets-token-urlsafe"
    session_timeout_hours: int = 8
    session_expiration_warning_minutes: int = 2
    session_cookie_name: str = "knowledge_session"  # Unique per application

    # Redis Configuration
    # Database 0: Sessions (security-critical, long-lived)
    # Database 1: Cache (performance cache, safe to flush)
    redis_url: str = "redis://redis:6379/0"
    redis_cache_url: str = "redis://redis:6379/1"
    redis_enabled: bool = True
    redis_key_prefix: str = "km_session:"

    # CORS Configuration
    enable_cors: bool = True
    cors_origins: list[str] = ["http://localhost:8060", "http://localhost:3000"]

    # Keycloak OAuth2/OIDC Configuration
    keycloak_url: str = "http://localhost:8041"  # External URL (browser accessible)
    keycloak_url_internal: str = "http://keycloak:8080"  # Internal Docker network URL
    keycloak_realm: str = "tools-provider"  # Shared realm with tools-provider

    # Public client for browser-based OAuth2 (PKCE enabled in Keycloak)
    keycloak_client_id: str = "knowledge-manager"
    keycloak_client_secret: str = ""  # Public client - no secret needed

    # JWT Configuration
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # Token Claim Validation
    verify_issuer: bool = False
    expected_issuer: str = ""
    verify_audience: bool = True  # Set True to enforce 'aud' claim
    expected_audience: list[str] = ["knowledge-manager"]  # Expected audience(s)
    refresh_auto_leeway_seconds: int = 60

    # ==========================================================================
    # Neo4j Configuration (Graph Database - Phase 2)
    # ==========================================================================
    neo4j_uri: str = "bolt://neo4j:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "neo4j-password-change-in-production"
    neo4j_database: str = "neo4j"
    neo4j_max_connection_pool_size: int = 50
    neo4j_connection_timeout: float = 30.0

    # ==========================================================================
    # Qdrant Configuration (Vector Database - Phase 3)
    # ==========================================================================
    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    qdrant_grpc_port: int = 6334
    qdrant_api_key: str | None = None
    qdrant_collection_name: str = "knowledge_terms"
    qdrant_vector_size: int = 384  # Sentence-transformers default

    # ==========================================================================
    # Embedding Configuration (Phase 3)
    # ==========================================================================
    embedding_model: str = "all-MiniLM-L6-v2"  # Sentence-transformers model
    embedding_batch_size: int = 32
    embedding_cache_enabled: bool = True

    # ==========================================================================
    # Agent-Host Integration
    # ==========================================================================
    agent_host_url: str = "http://localhost:8050"

    # ==========================================================================
    # Tools-Provider Integration
    # ==========================================================================
    tools_provider_url: str = "http://localhost:8040"

    # ==========================================================================
    # CloudEvent Publishing
    # ==========================================================================
    cloud_event_sink: str = "http://event-player:8080/events/pub"
    cloud_event_source: str = "https://knowledge-manager.system.io"
    cloud_event_type_prefix: str = "io.system.knowledge-manager"


# Create singleton instance
app_settings = Settings()


def configure_logging(log_level: str = "INFO") -> None:
    """Configure application logging.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Configure root logger
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )

    # Reduce noise from verbose libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    logging.getLogger("motor").setLevel(logging.WARNING)
    logging.getLogger("neo4j").setLevel(logging.WARNING)
    logging.getLogger("qdrant_client").setLevel(logging.WARNING)
