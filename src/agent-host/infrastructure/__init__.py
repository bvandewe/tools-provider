"""Infrastructure layer for Agent Host.

Contains:
- adapters/: External service adapters (Ollama, OpenAI, etc.)
- repositories/: Repository implementations
- session_store.py: Redis session management
- app_settings_service.py: MongoDB-based settings storage
- openai_token_cache.py: OAuth2 token caching for OpenAI
- llm_provider_factory.py: Factory for runtime LLM provider selection
- database_seeder.py: YAML-based database seeding
- skill_loader.py: Skill template loading
- yaml_exporter.py: Export to seed-compatible YAML
"""

from infrastructure.adapters.ollama_adapter import OllamaAdapter
from infrastructure.adapters.ollama_llm_provider import OllamaError, OllamaLlmProvider
from infrastructure.adapters.openai_llm_provider import OpenAiLlmProvider
from infrastructure.app_settings_service import AppSettingsService, get_settings_service
from infrastructure.database_seeder import DatabaseSeeder, DatabaseSeederService, get_database_seeder
from infrastructure.definition_store_initializer import DefinitionRepositoryInitializer  # Deprecated
from infrastructure.llm_provider_factory import LlmProviderFactory, get_provider_factory, set_provider_factory
from infrastructure.openai_token_cache import CachedToken, OpenAiTokenCache, get_openai_token_cache, set_openai_token_cache
from infrastructure.session_store import RedisSessionStore
from infrastructure.skill_loader import SkillLoader, get_skill_loader, set_skill_loader
from infrastructure.yaml_exporter import YamlExporter, export_definition_to_yaml, export_template_to_yaml

__all__ = [
    # Settings
    "AppSettingsService",
    "get_settings_service",
    # Database Seeder (replaces DefinitionRepositoryInitializer)
    "DatabaseSeeder",
    "DatabaseSeederService",
    "get_database_seeder",
    # Skill Loader
    "SkillLoader",
    "get_skill_loader",
    "set_skill_loader",
    # YAML Exporter
    "YamlExporter",
    "export_definition_to_yaml",
    "export_template_to_yaml",
    # Definition Initializer (deprecated - use DatabaseSeederService)
    "DefinitionRepositoryInitializer",
    # LLM Adapters
    "OllamaAdapter",
    "OllamaError",
    "OllamaLlmProvider",
    "OpenAiLlmProvider",
    # LLM Provider Factory
    "LlmProviderFactory",
    "get_provider_factory",
    "set_provider_factory",
    # Token Cache
    "CachedToken",
    "OpenAiTokenCache",
    "get_openai_token_cache",
    "set_openai_token_cache",
    # Session
    "RedisSessionStore",
]
