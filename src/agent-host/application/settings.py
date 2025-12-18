"""Application settings configuration for Agent Host."""

import logging
import sys

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
    consumer_group: str = "agent-host-consumer-group"  # EventStoreDB consumer group (when using event sourcing)

    # Connection Strings - override from ApplicationSettings base class
    # Set via CONNECTION_STRINGS env var as JSON (no prefix):
    # {"mongo": "mongodb://..."}
    # Docker: uses mongodb:27017 (internal network)
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
    cloud_event_sink: str | None = None
    cloud_event_source: str | None = None
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
    tools_provider_url: str = "http://tools-provider:8080"  # Internal Docker network URL
    tools_provider_external_url: str = "http://localhost:8040"  # External/browser-accessible URL
    tools_provider_timeout: float = 30.0  # HTTP timeout for Tools Provider calls

    # ==========================================================================
    # Ollama LLM Configuration
    # ==========================================================================
    # Default to localhost for local development (user has Ollama installed locally)
    # Override with AGENT_HOST_OLLAMA_URL=http://ollama:11434 in Docker environment
    ollama_enabled: bool = True  # Enable Ollama provider
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    ollama_timeout: float = 120.0  # LLM can take time to respond
    ollama_stream: bool = True  # Enable streaming responses
    ollama_temperature: float = 0.7
    ollama_top_p: float = 0.9
    ollama_num_ctx: int = 8192  # Context window size

    # ==========================================================================
    # OpenAI LLM Configuration
    # ==========================================================================
    # Supports both standard OpenAI API and Azure-style endpoints (e.g., Cisco Circuit)
    # Authentication: Either API Key OR OAuth2 client credentials (not both)
    openai_enabled: bool = False  # Enable OpenAI provider
    openai_api_endpoint: str = ""  # e.g., "https://api.openai.com/v1" or "https://chat-ai.cisco.com"
    openai_api_version: str = "2024-05-01-preview"  # API version (for Azure-style endpoints)
    openai_model: str = "gpt-4o"  # Default model
    openai_timeout: float = 120.0  # Request timeout
    openai_temperature: float = 0.7
    openai_top_p: float = 0.9
    openai_max_tokens: int = 4096  # Max tokens to generate

    # OpenAI Authentication - API Key mode (mutually exclusive with OAuth2)
    openai_auth_type: str = "api_key"  # "api_key" or "oauth2"
    openai_api_key: str = ""  # Direct API key (for standard OpenAI)

    # OpenAI Authentication - OAuth2 mode (for Cisco Circuit / Azure-style endpoints)
    openai_oauth_endpoint: str = ""  # Token endpoint (e.g., "https://id.cisco.com/oauth2/default/v1/token")
    openai_oauth_client_id: str = ""  # OAuth2 client ID
    openai_oauth_client_secret: str = ""  # OAuth2 client secret
    openai_oauth_token_ttl: int = 3600  # Token TTL in seconds (discovered or configured)

    # OpenAI Custom Headers (for Circuit-style endpoints)
    openai_app_key: str = ""  # Circuit app key (sent in model_kwargs)
    openai_client_id_header: str = ""  # Client ID header value (defaults to oauth_client_id if empty)

    # Stop sequences (for ChatML-format models like Azure/Circuit)
    # JSON array of strings, e.g., '["<|im_end|>"]'
    openai_stop_sequences: str = ""  # Empty means no custom stop sequences

    # ==========================================================================
    # Model Selection Configuration
    # ==========================================================================
    # Available models as JSON list of model definitions
    # Format: [{"provider": "ollama|openai", "id": "model-id", "name": "Display Name", "description": "..."}]
    # Environment variable: AGENT_HOST_AVAILABLE_MODELS='[{"provider":"ollama","id":"llama3.2:3b",...}]'
    available_models: str = (
        "["
        '{"provider":"openai","id":"gpt-4o","name":"GPT-4o","description":"Fast, capable model for general tasks","is_default":true},'
        '{"provider":"openai","id":"gpt-5.1","name":"GPT-5.1","description":"Best for logic, multi-step tasks, and coding"},'
        '{"provider":"openai","id":"claude-opus-4","name":"Claude Opus 4","description":"Enterprise-scale dialogue and analysis"},'
        '{"provider":"openai","id":"gemini-2.5-pro","name":"Gemini 2.5 Pro","description":"Best for coding and complex prompts"},'
        '{"provider":"ollama","id":"qwen2.5:7b","name":"Qwen 2.5 (Local)","description":"Fast local model with good tool support"},'
        '{"provider":"ollama","id":"llama3.2:3b","name":"Llama 3.2 (Local)","description":"Compact local model for quick tasks"}'
        "]"
    )

    # Allow users to select model (if False, uses default model for the provider)
    allow_model_selection: bool = True

    # Default provider to use when no model is explicitly selected
    default_llm_provider: str = "ollama"  # "ollama" or "openai"

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

## YOUR BUILT-IN CAPABILITIES

You have access to powerful built-in tools. Use them proactively to provide accurate, up-to-date, and helpful responses.

### 🕐 Time & Date
- **get_current_datetime**: Get the current date/time in any timezone. ALWAYS use this for date-related queries.

### 🌐 Web & Information
- **web_search**: Search the web via DuckDuckGo for current news, facts, or information.
- **wikipedia_query**: Look up factual, encyclopedic information on any topic.
- **fetch_url**: Download web pages, APIs, or files. Automatically saves binary files (Excel, PDF, images).

### 🐍 Code Execution
- **execute_python**: Run Python code in a secure sandbox. Use for calculations, data processing, parsing, and algorithms. Standard library only (math, json, datetime, re, collections, itertools).

### 🧠 Memory (Persistent)
- **memory_store**: Save key-value pairs that persist across conversations (user preferences, learned facts, context).
- **memory_retrieve**: Recall previously stored information or list all stored keys.

### 📁 File Management
- **file_writer**: Create files in the workspace (reports, code, data exports). Supports text and binary.
- **file_reader**: Read files from the workspace.
- **spreadsheet_read**: Read and analyze Excel (.xlsx) files with statistics and pagination.
- **spreadsheet_write**: Create or modify Excel spreadsheets.

### 🔧 Utilities
- **calculate**: Evaluate math expressions safely (arithmetic, sqrt, sin, cos, log, etc.).
- **generate_uuid**: Generate unique identifiers.
- **encode_decode**: Base64, URL, HTML, hex encoding/decoding.
- **regex_extract**: Extract data from text using regular expressions.
- **json_transform**: Query and transform JSON data with JSONPath expressions.
- **text_stats**: Analyze text (word count, reading time, common words).

### 🙋 Human Interaction
- **ask_human**: Pause and request clarification or input when needed.

## CRITICAL: DATE AND TIME AWARENESS

**ALWAYS use get_current_datetime FIRST** when the user's request involves:
- Relative time references: "last month", "last 3 months", "yesterday", "this week", "past year"
- Date ranges: "between X and Y", "from ... to ...", "since ..."
- Current time queries: "today", "now", "current"

Never assume or guess the current date - always verify it with the tool first.

## TOOL USAGE GUIDELINES

1. **Use tools proactively**: When users ask about facts, data, or current information:
   - Use **web_search** for current events, news, or real-time information
   - Use **wikipedia_query** for factual, encyclopedic knowledge
   - Use **fetch_url** to download and analyze web content or APIs

2. **Remember user context**: Use **memory_store** to save important preferences, facts, or context. Use **memory_retrieve** to recall them in future conversations.

3. **Code for complex tasks**: Use **execute_python** for:
   - Complex calculations or data transformations
   - Parsing or analyzing structured data
   - Generating formatted output

4. **Create deliverables**: Use **file_writer** and **spreadsheet_write** to create downloadable reports, data exports, or code files. When you create a file:
   - The tool returns a `download_url` - share this with the user
   - ⚠️ **Important**: File URLs are temporary (24 hours) - inform users not to rely on them for permanent storage

5. **Provide valid arguments**: For enum parameters, choose appropriate values. Never send empty strings for required parameters.

6. **Handle tool results gracefully**:
   - Present successful results in clear, user-friendly format
   - Explain when no data is found
   - Suggest alternatives when tools fail

7. **Be proactive**: Make reasonable assumptions rather than asking excessive clarifying questions.

8. **Chain tools when needed**: Combine tools for comprehensive answers (e.g., web_search → fetch_url → execute_python).

## RESPONSE FORMAT

- Be concise but informative
- Format data as readable lists or tables
- Include relevant details (prices, descriptions, availability)
- Cite sources when using web_search or wikipedia_query"""

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
