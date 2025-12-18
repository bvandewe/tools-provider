"""API controllers for Agent Host.

Controllers are auto-discovered by WebApplicationBuilder from this package.
"""

from api.controllers.admin_data_controller import AdminDataController
from api.controllers.admin_definitions_controller import AdminDefinitionsController
from api.controllers.admin_templates_controller import AdminTemplatesController
from api.controllers.auth_controller import AuthController
from api.controllers.chat_controller import ChatController
from api.controllers.config_controller import ConfigController
from api.controllers.definitions_controller import DefinitionsController
from api.controllers.files_controller import FilesController
from api.controllers.health_controller import HealthController
from api.controllers.settings_controller import SettingsController
from api.controllers.tools_controller import ToolsController

__all__ = [
    "AdminDataController",
    "AdminDefinitionsController",
    "AdminTemplatesController",
    "AuthController",
    "ChatController",
    "ConfigController",
    "DefinitionsController",
    "FilesController",
    "HealthController",
    "SettingsController",
    "ToolsController",
]
