"""Application health check and info controller."""

import logging

from classy_fastapi.decorators import get
from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from neuroglia.mvc import ControllerBase

from application.settings import app_settings

log = logging.getLogger(__name__)


class AppController(ControllerBase):
    """Controller for application health checks and info."""

    def __init__(self, service_provider: ServiceProviderBase, mapper: Mapper, mediator: Mediator):
        super().__init__(service_provider, mapper, mediator)

    @get("/health")
    async def health(self) -> dict:
        """Health check endpoint to verify the application is online."""
        return {"online": True, "status": "healthy", "detail": "The application is online and running."}

    @get("/info")
    async def info(self) -> dict:
        """Application info endpoint returning version and other metadata."""
        return {
            "name": app_settings.app_name,
            "version": app_settings.app_version,
            "environment": "development" if app_settings.debug else "production",
        }
