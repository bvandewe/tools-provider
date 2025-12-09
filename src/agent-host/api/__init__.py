"""API layer for Agent Host.

Contains:
- controllers/: FastAPI route handlers
- services/: API services (auth, etc.)
- dependencies.py: FastAPI dependencies
"""

from api.dependencies import get_current_user
from api.services.auth_service import AuthService

__all__ = [
    "AuthService",
    "get_current_user",
]
