"""Application settings configuration for Agent Host."""

import logging
import sys
from typing import Optional

from neuroglia.hosting.abstractions import ApplicationSettings


class Settings(ApplicationSettings):
    """Agent Host settings with Keycloak OAuth2/OIDC configuration."""

    # Debugging Configuration
    debug: bool = True
    environment: str = "development"  # development, production
    log_level: str = "INFO"

    # Application Configuration
    app_name: str = "Agent Host"
    app_version: str = "1.0.0"
    app_url: str = "http://localhost:8050"  # External URL for callbacks
    app_host: str = "127.0.0.1"  # Uvicorn bind address
    app_port: int = 8050  # Uvicorn port

    # Database Configuration (for Neuroglia DataAccessLayer)
    database_name: str = "agent_host"

    # Connection Strings - override from ApplicationSettings base class
    # Set via CONNECTION_STRINGS env var as JSON (no prefix):
    # {"mongo": "mongodb://..."}
    connection_strings: dict[str, str] = {"mongo": "mongodb://root:password123@mongodb:27017/?authSource=admin"}  # pragma: allowlist secret

    # Observability Configuration
    service_name: str = "agent-host"
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

    # CloudEvent Configuration
    # DomainEvents are published as CloudEvents via DomainEventCloudEventBehavior
    # event-player service aggregates and fans out events
    cloud_event_sink: Optional[str] = None
    cloud_event_source: Optional[str] = None
    cloud_event_type_prefix: str = "io.agent-host"
    cloud_event_retry_attempts: int = 5
    cloud_event_retry_delay: float = 1.0

    otel_enabled: bool = False  # Optional - enable for tracing
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
    session_secret_key: str = "agent-host-session-secret-change-in-production"  # pragma: allowlist secret
    session_timeout_hours: int = 8  # Legacy: kept for backward compatibility
    # Session idle timeout is fetched from Keycloak (ssoSessionIdleTimeout)
    # This setting defines how many minutes before idle timeout to show warning modal
    session_expiration_warning_minutes: int = 2  # Show warning N minutes before Keycloak idle timeout
    # Session cookie name - MUST be unique per application to avoid cross-app cookie collisions
    # When multiple apps share the same domain (e.g., localhost), each app needs a unique cookie name
    session_cookie_name: str = "agent_session"

    # Redis Configuration (Database 2 - separate from Tools Provider)
    redis_url: str = "redis://redis:6379/2"
    redis_enabled: bool = True
    redis_key_prefix: str = "agent-host:session:"

    # CORS Configuration
    enable_cors: bool = True
    cors_origins: list[str] = ["http://localhost:8050", "http://localhost:3000"]

    # Keycloak OAuth2/OIDC Configuration
    keycloak_url: str = "http://localhost:8041"  # External URL (browser accessible)
    keycloak_url_internal: str = "http://keycloak:8080"  # Internal Docker network URL
    keycloak_realm: str = "tools-provider"

    # Public client for OAuth2 Authorization Code flow
    keycloak_client_id: str = "agent-host"

    # Token Claim Validation
    verify_issuer: bool = False
    expected_issuer: str = ""
    verify_audience: bool = False
    expected_audience: list[str] = []
    refresh_auto_leeway_seconds: int = 60

    # Tools Provider Configuration
    tools_provider_url: str = "http://app:8080"  # Internal Docker network URL
    tools_provider_external_url: str = "http://localhost:8040"  # External/browser-accessible URL
    tools_provider_timeout: float = 30.0  # HTTP timeout for Tools Provider calls

    # Ollama LLM Configuration
    # Default to localhost for local development (user has Ollama installed locally)
    # Override with AGENT_HOST_OLLAMA_URL=http://ollama:11434 in Docker environment
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    ollama_timeout: float = 120.0  # LLM can take time to respond
    ollama_stream: bool = True  # Enable streaming responses
    ollama_temperature: float = 0.7
    ollama_top_p: float = 0.9
    ollama_num_ctx: int = 8192  # Context window size

    # ==========================================================================
    # Model Selection Configuration
    # ==========================================================================
    # Available models for user selection (comma-separated Ollama model names)
    # Format: model_id|Display Name|Description (use pipe delimiter since model_id can contain colons)
    # Models should support tool/function calling for best experience
    available_models: str = (
        "qwen2.5:7b|Qwen 2.5 (Fast)|Fast and efficient for quick tasks,llama3.2:3b|Llama 3.2 (Compact)|Compact model with good reasoning,mistral:7b-instruct|Mistral (Balanced)|Well-balanced performance,llama3.1:8b|Llama 3.1 (Capable)|More capable for complex tasks,gpt-oss:20b|GPT-OSS 20B (Powerful)|Powerful model for advanced reasoning"
    )

    # Allow users to select model (if False, uses default ollama_model)
    allow_model_selection: bool = True

    # Conversation Configuration
    conversation_history_max_messages: int = 50  # Max messages to retain in context
    conversation_session_ttl_seconds: int = 3600  # 1 hour session TTL

    # ==========================================================================
    # Agent Configuration
    # ==========================================================================

    # Agent Identity
    agent_name: str = "assistant"

    # Agent Behavior
    agent_max_iterations: int = 10  # Max LLM calls per user message (prevents infinite loops)
    agent_max_tool_calls_per_iteration: int = 5  # Max tools per LLM response
    agent_stop_on_error: bool = False  # Stop execution on tool errors
    agent_retry_on_error: bool = True  # Retry failed tool calls
    agent_max_retries: int = 2  # Max retries for failed tool calls
    agent_timeout_seconds: float = 300.0  # Overall timeout for agent run (5 minutes)

    # System Prompt - defines the agent's persona and instructions
    system_prompt: str = """You are a helpful AI assistant with access to various tools that can interact with external services.

## TOOL USAGE GUIDELINES

1. **Always use tools when appropriate**: When the user asks about data (pets, menu items, etc.), ALWAYS call the relevant tool to fetch real data. Never make up information.

2. **Provide valid arguments**: When calling tools, always provide valid values for required parameters:
   - For `status` fields with enum values like ['available', 'pending', 'sold'], choose the most appropriate value (default to 'available' if listing all)
   - For `category` fields, use reasonable defaults like 'pizza' for menu items
   - Never send empty strings for required enum parameters

3. **Handle tool results**: After receiving tool results:
   - If successful, present the data in a clear, user-friendly format
   - If the result is empty or null, explain that no data was found
   - If the tool fails, explain the error and suggest alternatives

4. **Be proactive**: If a query is ambiguous about parameters, make reasonable assumptions rather than asking clarifying questions. For example, "list all pets" should call findPetsByStatus with status='available'.

5. **Multiple tool calls**: If needed, call multiple tools to gather comprehensive information.

## RESPONSE FORMAT

- Be concise but informative
- Format data as readable lists or tables when presenting multiple items
- Include relevant details like prices, descriptions, and availability"""

    # ==========================================================================
    # UI Configuration
    # ==========================================================================

    # Welcome message displayed below the title on the chat page
    welcome_message: str = "Your AI assistant with access to powerful tools."

    # Rate limiting to prevent abuse
    rate_limit_requests_per_minute: int = 20  # Max requests per user per minute
    rate_limit_concurrent_requests: int = 1  # Max concurrent streaming requests per user

    # Application metadata for sidebar footer
    app_tag: str = "v1.0.0"  # Version tag displayed in sidebar footer
    app_repo_url: str = ""  # GitHub repository URL (empty = hide link)

    class Config:
        env_file = ".env"
        env_prefix = "AGENT_HOST_"  # All env vars prefixed with AGENT_HOST_
        case_sensitive = False
        extra = "ignore"


app_settings = Settings()


def configure_logging(log_level: str = "INFO") -> None:
    """
    Configure application-wide logging.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Reduce noise from third-party loggers
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    logging.getLogger("motor").setLevel(logging.WARNING)
