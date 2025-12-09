"""API layer package.

This package contains:
- Controllers: REST API endpoints using Neuroglia ControllerBase
- Dependencies: FastAPI dependencies for auth, services, etc.
- Services: Authentication, OpenAPI configuration, etc.
"""

from .controllers import SourcesController, TasksController, ToolsController
from .dependencies import get_current_user, require_roles
from .services import DualAuthService

__all__ = [
    "DualAuthService",
    "SourcesController",
    "TasksController",
    "ToolsController",
    "get_current_user",
    "require_roles",
]
