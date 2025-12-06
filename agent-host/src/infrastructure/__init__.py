"""Infrastructure layer for Agent Host.

Contains:
- adapters/: External service adapters (Ollama, etc.)
- repositories/: Repository implementations
- session_store.py: Redis session management
"""

from infrastructure.adapters.ollama_adapter import OllamaAdapter
from infrastructure.session_store import RedisSessionStore

__all__ = [
    "OllamaAdapter",
    "RedisSessionStore",
]
