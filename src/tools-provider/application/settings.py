"""Application settings configuration."""

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
    app_name: str = "Tools Provider"
    app_version: str = "1.0.0"
    app_url: str = "http://localhost:8040"  # External URL for callbacks
    app_host: str = "127.0.0.1"  # Uvicorn bind address (override in production as needed)
    app_port: int = 8080  # Uvicorn port

    # Observability Configuration
    service_name: str = "tools-provider"
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
    session_timeout_hours: int = 8  # Legacy: kept for backward compatibility
    # Session idle timeout is fetched from Keycloak (ssoSessionIdleTimeout)
    # This setting defines how many minutes before idle timeout to show warning modal
    session_expiration_warning_minutes: int = 2  # Show warning N minutes before Keycloak idle timeout
    # Session cookie name - MUST be unique per application to avoid cross-app cookie collisions
    # When multiple apps share the same domain (e.g., localhost), each app needs a unique cookie name
    session_cookie_name: str = "tools_session"

    # Redis Configuration
    # Database 0: Sessions (security-critical, long-lived)
    # Database 1: Cache (performance cache, safe to flush)
    # Database 3: Agent memory (built-in tools persistent storage)
    redis_url: str = "redis://redis:6379/0"  # Sessions database
    redis_cache_url: str = "redis://redis:6379/1"  # Cache database (tools, manifests, tokens)
    redis_memory_url: str = "redis://redis:6379/3"  # Agent memory database (built-in tools)
    redis_enabled: bool = True  # Use Redis for sessions by default (even in dev)
    redis_key_prefix: str = "session:"
    redis_memory_key_prefix: str = "agent:memory:"  # Prefix for agent memory keys

    # CORS Configuration
    enable_cors: bool = True
    cors_origins: list[str] = ["http://localhost:8040", "http://localhost:3000"]

    # Agent Host Configuration
    agent_host_url: str = "http://localhost:8050"  # External URL for agent-host link

    # Keycloak OAuth2/OIDC Configuration
    keycloak_url: str = "http://localhost:8041"  # External URL (browser accessible)
    keycloak_url_internal: str = "http://keycloak:8080"  # Internal Docker network URL
    keycloak_realm: str = "tools-provider"

    # Backend confidential client for secure token exchange
    keycloak_client_id: str = "tools-provider-public"
    keycloak_client_secret: str = "tools-provider-backend-secret-change-in-production"

    # Legacy JWT (deprecated - will be removed)
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # Token Claim Validation (optional hardened checks)
    verify_issuer: bool = False  # Set True to enforce 'iss' claim
    expected_issuer: str = ""  # e.g. "http://localhost:8021/realms/tools-provider"
    verify_audience: bool = False  # Set True to enforce 'aud' claim
    expected_audience: list[str] = []  # e.g. ["tools-provider-backend"]
    refresh_auto_leeway_seconds: int = 60  # Auto-refresh if exp is within this window

    # Token Exchange Configuration (RFC 8693)
    # Uses a dedicated confidential client for token exchange operations
    token_exchange_client_id: str = "tools-provider-token-exchange"
    token_exchange_client_secret: str = "token-exchange-secret-change-in-production"  # pragma: allowlist secret
    token_exchange_cache_ttl_buffer: int = 60  # Seconds before expiry to consider token stale
    token_exchange_timeout: float = 10.0  # HTTP timeout for token exchange requests

    # Service Account Configuration (OAuth2 Client Credentials)
    # Used for Level 2 auth mode (client_credentials grant) when using Tools Provider's own identity
    # Leave empty to disable this feature (Variant A disabled)
    service_account_token_url: str = ""  # OAuth2 token endpoint (default: Keycloak realm token endpoint)
    service_account_client_id: str = "tools-provider-service"  # Service account client ID
    service_account_client_secret: str = ""  # Service account client secret (set in production)  # pragma: allowlist secret
    service_account_cache_buffer_seconds: int = 60  # Refresh token this many seconds before expiry

    # Circuit Breaker Configuration
    circuit_breaker_failure_threshold: int = 5  # Failures before circuit opens
    circuit_breaker_recovery_timeout: float = 30.0  # Seconds before retry

    # Tool Execution Configuration
    tool_execution_timeout: float = 30.0  # Default HTTP timeout for tool execution
    tool_execution_max_poll_attempts: int = 60  # Max polling attempts for async tools
    tool_execution_validate_schema: bool = True  # Global schema validation toggle

    # Persistence Configuration
    consumer_group: str | None = "tools-provider-consumer-group"
    database_name: str = "tools_provider"
    connection_strings: dict[str, str] = {"mongo": "mongodb://root:pass@mongodb:27017/?authSource=admin"}  # pragma: allowlist secret

    # Cloud Events Configuration
    cloud_event_sink: str | None = None
    cloud_event_source: str | None = None
    cloud_event_type_prefix: str = "io.system.tools-provider"
    cloud_event_retry_attempts: int = 5
    cloud_event_retry_delay: float = 1.0

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra environment variables


app_settings = Settings()


def configure_logging(log_level: str = "INFO") -> None:
    """
    Configure application-wide logging.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Set third-party loggers to WARNING to reduce noise
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
