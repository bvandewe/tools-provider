"""Application Settings DTO for MongoDB storage.

Settings are stored as a single document with subsections for LLM, Agent, and UI configuration.
These settings override the default application settings from environment variables.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from neuroglia.data.abstractions import Identifiable, queryable


@dataclass
class LlmSettingsDto:
    """LLM configuration settings for Ollama and OpenAI providers."""

    # ==========================================================================
    # Ollama Configuration
    # ==========================================================================
    ollama_enabled: bool = True
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    ollama_timeout: float = 120.0
    ollama_stream: bool = True
    ollama_temperature: float = 0.7
    ollama_top_p: float = 0.9
    ollama_num_ctx: int = 8192

    # ==========================================================================
    # OpenAI Configuration
    # ==========================================================================
    openai_enabled: bool = False
    openai_api_endpoint: str = ""
    openai_api_version: str = "2024-05-01-preview"
    openai_model: str = "gpt-4o"
    openai_timeout: float = 120.0
    openai_temperature: float = 0.7
    openai_top_p: float = 0.9
    openai_max_tokens: int = 4096

    # OpenAI Authentication
    openai_auth_type: str = "api_key"  # "api_key" or "oauth2"
    openai_api_key: str = ""  # For API key auth
    openai_oauth_endpoint: str = ""  # For OAuth2 auth
    openai_oauth_client_id: str = ""
    openai_oauth_client_secret: str = ""
    openai_oauth_token_ttl: int = 3600

    # OpenAI Custom Headers (for Circuit-style endpoints)
    openai_app_key: str = ""
    openai_client_id_header: str = ""

    # ==========================================================================
    # Model Selection
    # ==========================================================================
    allow_model_selection: bool = True
    available_models: str = ""  # JSON array of model definitions
    default_llm_provider: str = "ollama"  # "ollama" or "openai"


@dataclass
class AgentSettingsDto:
    """Agent behavior configuration settings."""

    # Agent identity
    agent_name: str = "assistant"

    # Agent behavior limits
    max_iterations: int = 10
    max_tool_calls_per_iteration: int = 5
    stop_on_error: bool = False
    retry_on_error: bool = True
    max_retries: int = 2
    timeout_seconds: float = 300.0

    # System prompt
    system_prompt: str = ""


@dataclass
class UiSettingsDto:
    """UI configuration settings."""

    # Welcome message
    welcome_message: str = "Your AI assistant with access to powerful tools."

    # Rate limiting
    rate_limit_requests_per_minute: int = 20
    rate_limit_concurrent_requests: int = 1

    # Application metadata
    app_tag: str = ""
    app_repo_url: str = ""


@queryable
@dataclass
class AppSettingsDto(Identifiable[str]):
    """Application settings document stored in MongoDB.

    Uses a singleton pattern with a fixed ID to ensure only one settings document exists.
    """

    # Fixed ID for singleton pattern
    id: str = "app_settings"

    # Subsections
    llm: LlmSettingsDto = field(default_factory=LlmSettingsDto)
    agent: AgentSettingsDto = field(default_factory=AgentSettingsDto)
    ui: UiSettingsDto = field(default_factory=UiSettingsDto)

    # Audit fields
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None

    def __post_init__(self) -> None:
        """Ensure subsections are properly initialized."""
        if isinstance(self.llm, dict):
            self.llm = LlmSettingsDto(**self.llm)
        if isinstance(self.agent, dict):
            self.agent = AgentSettingsDto(**self.agent)
        if isinstance(self.ui, dict):
            self.ui = UiSettingsDto(**self.ui)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppSettingsDto":
        """Create an AppSettingsDto from a dictionary."""
        return cls(
            id=data.get("id", "app_settings"),
            llm=LlmSettingsDto(**data.get("llm", {})) if data.get("llm") else LlmSettingsDto(),
            agent=AgentSettingsDto(**data.get("agent", {})) if data.get("agent") else AgentSettingsDto(),
            ui=UiSettingsDto(**data.get("ui", {})) if data.get("ui") else UiSettingsDto(),
            updated_at=data.get("updated_at"),
            updated_by=data.get("updated_by"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for MongoDB storage."""
        return {
            "id": self.id,
            "llm": {
                # Ollama settings
                "ollama_enabled": self.llm.ollama_enabled,
                "ollama_url": self.llm.ollama_url,
                "ollama_model": self.llm.ollama_model,
                "ollama_timeout": self.llm.ollama_timeout,
                "ollama_stream": self.llm.ollama_stream,
                "ollama_temperature": self.llm.ollama_temperature,
                "ollama_top_p": self.llm.ollama_top_p,
                "ollama_num_ctx": self.llm.ollama_num_ctx,
                # OpenAI settings
                "openai_enabled": self.llm.openai_enabled,
                "openai_api_endpoint": self.llm.openai_api_endpoint,
                "openai_api_version": self.llm.openai_api_version,
                "openai_model": self.llm.openai_model,
                "openai_timeout": self.llm.openai_timeout,
                "openai_temperature": self.llm.openai_temperature,
                "openai_top_p": self.llm.openai_top_p,
                "openai_max_tokens": self.llm.openai_max_tokens,
                "openai_auth_type": self.llm.openai_auth_type,
                "openai_api_key": self.llm.openai_api_key,
                "openai_oauth_endpoint": self.llm.openai_oauth_endpoint,
                "openai_oauth_client_id": self.llm.openai_oauth_client_id,
                "openai_oauth_client_secret": self.llm.openai_oauth_client_secret,
                "openai_oauth_token_ttl": self.llm.openai_oauth_token_ttl,
                "openai_app_key": self.llm.openai_app_key,
                "openai_client_id_header": self.llm.openai_client_id_header,
                # Model selection
                "allow_model_selection": self.llm.allow_model_selection,
                "available_models": self.llm.available_models,
                "default_llm_provider": self.llm.default_llm_provider,
            },
            "agent": {
                "agent_name": self.agent.agent_name,
                "max_iterations": self.agent.max_iterations,
                "max_tool_calls_per_iteration": self.agent.max_tool_calls_per_iteration,
                "stop_on_error": self.agent.stop_on_error,
                "retry_on_error": self.agent.retry_on_error,
                "max_retries": self.agent.max_retries,
                "timeout_seconds": self.agent.timeout_seconds,
                "system_prompt": self.agent.system_prompt,
            },
            "ui": {
                "welcome_message": self.ui.welcome_message,
                "rate_limit_requests_per_minute": self.ui.rate_limit_requests_per_minute,
                "rate_limit_concurrent_requests": self.ui.rate_limit_concurrent_requests,
                "app_tag": self.ui.app_tag,
                "app_repo_url": self.ui.app_repo_url,
            },
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "updated_by": self.updated_by,
        }
