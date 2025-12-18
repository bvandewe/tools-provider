"""UI controller for Agent Host - serves HTML pages."""

from pathlib import Path

from classy_fastapi.decorators import get
from classy_fastapi.routable import Routable
from fastapi import Request
from fastapi.responses import FileResponse, HTMLResponse
from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from neuroglia.mvc import ControllerBase
from neuroglia.mvc.controller_base import generate_unique_id_function


class UIController(ControllerBase):
    """Controller for Agent Host UI pages."""

    def __init__(
        self,
        service_provider: ServiceProviderBase,
        mapper: Mapper,
        mediator: Mediator,
    ):
        """Initialize the UI controller.

        Args:
            service_provider: DI service provider
            mapper: Object mapper
            mediator: CQRS mediator
        """
        self.service_provider = service_provider
        self.mapper = mapper
        self.mediator = mediator
        self.name = "UI"

        # Get absolute path to static directory where Parcel builds the HTML
        # From src/ui/controllers/ui_controller.py -> ../../../static
        self.static_dir = Path(__file__).parent.parent.parent / "static"

        # Call Routable.__init__ directly with empty prefix for root routes
        Routable.__init__(
            self,
            prefix="",
            tags=["UI"],
            generate_unique_id_function=generate_unique_id_function,
        )

    @get("/", response_class=HTMLResponse)
    async def index(self, request: Request) -> FileResponse:
        """Serve the main chat application page.

        Args:
            request: FastAPI request object

        Returns:
            The index.html file
        """
        index_path = self.static_dir / "index.html"
        return FileResponse(index_path, media_type="text/html")

    @get("/admin", response_class=HTMLResponse)
    async def admin(self, request: Request) -> FileResponse:
        """Serve the admin page.

        Note: Role-based access control is handled client-side with a redirect
        to login if the user doesn't have admin role. The API endpoints for
        admin operations perform server-side role checks.

        Args:
            request: FastAPI request object

        Returns:
            The admin.html file
        """
        admin_path = self.static_dir / "admin.html"
        return FileResponse(admin_path, media_type="text/html")

    @get("/health", response_class=HTMLResponse)
    async def health(self, request: Request) -> dict:
        """Health check endpoint for UI.

        Args:
            request: FastAPI request object

        Returns:
            Health status
        """
        return {"status": "healthy", "service": "agent-host-ui"}
