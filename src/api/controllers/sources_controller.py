"""Sources API controller for upstream source management.

Provides endpoints for:
- Registering new upstream sources (OpenAPI specs, workflow engines)
- Listing and filtering sources
- Getting source details
- Triggering inventory refresh
- Enabling/disabling sources
"""

from typing import Optional

from classy_fastapi.decorators import delete, get, post
from fastapi import Depends, Query
from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from neuroglia.mvc import ControllerBase
from pydantic import BaseModel, Field

from api.dependencies import get_current_user, require_roles
from application.commands import DeleteSourceCommand, RefreshInventoryCommand, RegisterSourceCommand
from application.queries import GetSourceByIdQuery, GetSourcesQuery

# ============================================================================
# REQUEST MODELS
# ============================================================================


class RegisterSourceRequest(BaseModel):
    """Request to register a new upstream source."""

    name: str = Field(..., description="Human-readable name for the source")
    url: str = Field(..., description="URL to the specification (OpenAPI JSON/YAML)")
    source_type: str = Field(default="openapi", description="Type of source: 'openapi' or 'workflow'")

    # Authentication configuration
    auth_type: Optional[str] = Field(default=None, description="Auth type: 'none', 'bearer', 'api_key', 'oauth2'")
    bearer_token: Optional[str] = Field(default=None, description="Bearer token for authentication")
    api_key_name: Optional[str] = Field(default=None, description="API key header/query name")
    api_key_value: Optional[str] = Field(default=None, description="API key value")
    api_key_in: Optional[str] = Field(default=None, description="Where to send API key: 'header' or 'query'")
    oauth2_client_id: Optional[str] = Field(default=None, description="OAuth2 client ID")
    oauth2_client_secret: Optional[str] = Field(default=None, description="OAuth2 client secret")
    oauth2_token_url: Optional[str] = Field(default=None, description="OAuth2 token endpoint URL")
    oauth2_scopes: Optional[list[str]] = Field(default=None, description="OAuth2 scopes to request")

    # Validation
    validate_url: bool = Field(default=True, description="Whether to validate URL before registration")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "PetStore API",
                "url": "https://petstore3.swagger.io/api/v3/openapi.json",
                "source_type": "openapi",
                "validate_url": True,
            }
        }


class RefreshInventoryRequest(BaseModel):
    """Request to refresh source inventory."""

    force: bool = Field(default=False, description="Force refresh even if inventory hash unchanged")

    class Config:
        json_schema_extra = {
            "example": {
                "force": False,
            }
        }


# ============================================================================
# CONTROLLER
# ============================================================================


class SourcesController(ControllerBase):
    """Controller for upstream source management endpoints.

    Provides CRUD operations for managing external API sources
    that provide tools to AI agents.

    All endpoints require authentication via:
    - Session cookie (from OAuth2 login)
    - JWT Bearer token (for API clients)

    Admin/manager roles required for write operations.
    """

    def __init__(self, service_provider: ServiceProviderBase, mapper: Mapper, mediator: Mediator):
        super().__init__(service_provider, mapper, mediator)

    # =========================================================================
    # READ OPERATIONS
    # =========================================================================

    @get("/")
    async def get_sources(
        self,
        include_disabled: bool = Query(False, description="Include disabled sources"),
        health_status: Optional[str] = Query(None, description="Filter by health: healthy, degraded, unhealthy, unknown"),
        source_type: Optional[str] = Query(None, description="Filter by type: openapi, workflow"),
        user: dict = Depends(get_current_user),
    ):
        """List all upstream sources with optional filtering.

        Returns enabled sources by default. Use filters to narrow results.

        Supports authentication via:
        - Session cookie (from OAuth2 login)
        - JWT Bearer token (for API clients)
        """
        query = GetSourcesQuery(
            include_disabled=include_disabled,
            health_status=health_status,
            source_type=source_type,
            user_info=user,
        )
        result = await self.mediator.execute_async(query)
        return self.process(result)

    @get("/{source_id}")
    async def get_source(
        self,
        source_id: str,
        user: dict = Depends(get_current_user),
    ):
        """Get a single upstream source by ID.

        Returns full source details including health status,
        inventory count, and last sync information.

        Supports authentication via:
        - Session cookie (from OAuth2 login)
        - JWT Bearer token (for API clients)
        """
        query = GetSourceByIdQuery(source_id=source_id, user_info=user)
        result = await self.mediator.execute_async(query)
        return self.process(result)

    # =========================================================================
    # WRITE OPERATIONS (Require admin/manager role)
    # =========================================================================

    @post("/")
    async def register_source(
        self,
        request: RegisterSourceRequest,
        user: dict = Depends(require_roles("admin", "manager")),
    ):
        """Register a new upstream source.

        Creates a new source entry and optionally validates the URL.
        After registration, use the refresh endpoint to sync the tool inventory.

        **RBAC Protected**: Only users with 'admin' or 'manager' roles can register sources.

        Supports authentication via:
        - Session cookie (from OAuth2 login)
        - JWT Bearer token (for API clients)
        """
        command = RegisterSourceCommand(
            name=request.name,
            url=request.url,
            source_type=request.source_type,
            auth_type=request.auth_type,
            bearer_token=request.bearer_token,
            api_key_name=request.api_key_name,
            api_key_value=request.api_key_value,
            api_key_in=request.api_key_in,
            oauth2_client_id=request.oauth2_client_id,
            oauth2_client_secret=request.oauth2_client_secret,
            oauth2_token_url=request.oauth2_token_url,
            oauth2_scopes=request.oauth2_scopes,
            validate_url=request.validate_url,
            user_info=user,
        )
        result = await self.mediator.execute_async(command)
        return self.process(result)

    @post("/{source_id}/refresh")
    async def refresh_inventory(
        self,
        source_id: str,
        request: RefreshInventoryRequest = RefreshInventoryRequest(),
        user: dict = Depends(require_roles("admin", "manager")),
    ):
        """Refresh the tool inventory for a source.

        Fetches the latest specification from the source URL,
        parses tools, and updates the inventory. Uses hash-based
        change detection to skip unnecessary updates unless forced.

        Returns details about discovered, created, updated, and
        deprecated tools.

        **RBAC Protected**: Only users with 'admin' or 'manager' roles can refresh inventory.

        Supports authentication via:
        - Session cookie (from OAuth2 login)
        - JWT Bearer token (for API clients)
        """
        command = RefreshInventoryCommand(
            source_id=source_id,
            force=request.force,
            user_info=user,
        )
        result = await self.mediator.execute_async(command)
        return self.process(result)

    # =========================================================================
    # DELETE OPERATIONS
    # =========================================================================

    @delete("/{source_id}")
    async def delete_source(
        self,
        source_id: str,
        user: dict = Depends(require_roles("admin")),
    ):
        """Permanently delete an upstream source and all its tools.

        This is a hard delete that removes the source from both the
        event store and read model. This operation cannot be undone.

        **Cascading Deletion**: All tools associated with this source
        will also be permanently deleted. Each tool is marked as deleted
        (emitting a domain event) before being removed from the event store.

        **Admin Only**: Only users with 'admin' role can delete sources.

        Supports authentication via:
        - Session cookie (from OAuth2 login)
        - JWT Bearer token (for API clients)
        """
        command = DeleteSourceCommand(
            source_id=source_id,
            user_info=user,
        )
        result = await self.mediator.execute_async(command)
        return self.process(result)
