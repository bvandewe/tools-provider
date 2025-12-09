"""Infrastructure layer for Agent Host.

Contains:
- adapters/: External service adapters (Ollama, etc.)
- repositories/: Repository implementations
- session_store.py: Redis session management
- app_settings_service.py: MongoDB-based settings storage
"""

from infrastructure.adapters.ollama_adapter import OllamaAdapter
from infrastructure.app_settings_service import AppSettingsService, get_settings_service
from infrastructure.session_store import RedisSessionStore

__all__ = [
    "AppSettingsService",
    "get_settings_service",
    "OllamaAdapter",
    "RedisSessionStore",
]
