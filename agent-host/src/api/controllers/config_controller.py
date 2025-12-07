"""Configuration controller for frontend app settings."""

import logging

from classy_fastapi.decorators import get
from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from neuroglia.mvc import ControllerBase
from pydantic import BaseModel

from application.settings import app_settings

logger = logging.getLogger(__name__)


class AppConfigResponse(BaseModel):
    """Response containing frontend application configuration."""

    app_name: str
    welcome_message: str
    rate_limit_requests_per_minute: int
    rate_limit_concurrent_requests: int
    app_tag: str
    app_repo_url: str


class ConfigController(ControllerBase):
    """Controller for application configuration endpoints.

    Provides configuration data to the frontend without requiring authentication.
    This allows the UI to fetch dynamic settings on initialization.
    """

    def __init__(self, service_provider: ServiceProviderBase, mapper: Mapper, mediator: Mediator):
        super().__init__(service_provider, mapper, mediator)

    @get("/")
    async def get_config(self) -> AppConfigResponse:
        """
        Get application configuration for the frontend.

        Returns configuration values that the UI needs to initialize,
        including the welcome message and rate limit settings.

        This endpoint does not require authentication so it can be
        called before the user logs in.
        """
        return AppConfigResponse(
            app_name=app_settings.app_name,
            welcome_message=app_settings.welcome_message,
            rate_limit_requests_per_minute=app_settings.rate_limit_requests_per_minute,
            rate_limit_concurrent_requests=app_settings.rate_limit_concurrent_requests,
            app_tag=app_settings.app_tag,
            app_repo_url=app_settings.app_repo_url,
        )
