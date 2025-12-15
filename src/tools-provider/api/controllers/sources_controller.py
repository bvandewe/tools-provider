"""Sources API controller for upstream source management.

Provides endpoints for:
- Registering new upstream sources (OpenAPI specs, workflow engines)
- Listing and filtering sources
- Getting source details
- Updating source details
- Triggering inventory refresh
- Enabling/disabling sources
"""

from classy_fastapi.decorators import delete, get, patch, post
from fastapi import Depends, Query
from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from neuroglia.mvc import ControllerBase
from pydantic import BaseModel, Field

from api.dependencies import get_current_user, require_roles
from application.commands import DeleteSourceCommand, RefreshInventoryCommand, RegisterSourceCommand, UpdateSourceCommand
from application.queries import GetSourceByIdQuery, GetSourcesQuery

# ============================================================================
# REQUEST MODELS
# ============================================================================


class RegisterSourceRequest(BaseModel):
    """Request to register a new upstream source."""

    name: str = Field(..., description="Human-readable name for the source")
    url: str = Field(..., description="Service base URL (e.g., https://api.example.com)")
    openapi_url: str | None = Field(default=None, description="URL to the OpenAPI specification. If not provided, url will be used.")
    description: str | None = Field(default=None, description="Human-readable description of the source")
    source_type: str = Field(default="openapi", description="Type of source: 'openapi' or 'workflow'")

    # Authentication configuration
    auth_type: str | None = Field(default=None, description="Auth type: 'none', 'bearer', 'api_key', 'oauth2'")
    bearer_token: str | None = Field(default=None, description="Bearer token for authentication")
    api_key_name: str | None = Field(default=None, description="API key header/query name")
    api_key_value: str | None = Field(default=None, description="API key value")
    api_key_in: str | None = Field(default=None, description="Where to send API key: 'header' or 'query'")
    oauth2_client_id: str | None = Field(default=None, description="OAuth2 client ID")
    oauth2_client_secret: str | None = Field(default=None, description="OAuth2 client secret")
    oauth2_token_url: str | None = Field(default=None, description="OAuth2 token endpoint URL")
    oauth2_scopes: list[str] | None = Field(default=None, description="OAuth2 scopes to request")

    # Token exchange configuration
    default_audience: str | None = Field(
        default=None,
        description="Target audience for token exchange (Keycloak client_id of the upstream service). When set, tokens will be exchanged with this audience before calling the upstream API.",
    )

    # Authentication mode for tool execution
    auth_mode: str = Field(
        default="token_exchange",
        description="Authentication mode for tool execution: 'none' (public API), 'api_key', 'client_credentials', 'token_exchange' (default)",
    )

    # Scope-based access control
    required_scopes: list[str] | None = Field(
        default=None,
        description="Scopes required for all tools from this source. Overrides auto-discovered scopes from OpenAPI. Empty list means no source-level scope requirements.",
    )

    # Validation
    validate_url: bool = Field(default=True, description="Whether to validate URL before registration")

    # MCP-specific configuration (required when source_type='mcp')
    mcp_plugin_dir: str | None = Field(default=None, description="Absolute path to the MCP plugin directory containing plugin.json manifest (for local plugins)")
    mcp_manifest_path: str | None = Field(default=None, description="Path to the plugin manifest file (defaults to plugin.json in plugin_dir)")
    mcp_transport_type: str = Field(default="stdio", description="MCP transport type: 'stdio', 'sse', or 'streamable_http'")
    mcp_lifecycle_mode: str = Field(default="transient", description="Lifecycle mode: 'transient' (start per call) or 'singleton' (long-running)")
    mcp_runtime_hint: str | None = Field(default=None, description="Runtime hint: 'python', 'node', 'go', or None for auto-detection")
    mcp_command: str | None = Field(default=None, description="Custom command to start the plugin (overrides manifest)")
    mcp_args: list[str] | None = Field(default=None, description="Additional arguments for the plugin command")
    mcp_env_vars: dict[str, str] | None = Field(default=None, description="Environment variables to set for the plugin process")
    mcp_server_url: str | None = Field(default=None, description="URL for remote MCP server (e.g., http://cml-mcp:9000). When set, mcp_plugin_dir is not required.")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "PetStore API",
                "url": "https://petstore.swagger.io",
                "openapi_url": "https://petstore3.swagger.io/api/v3/openapi.json",
                "description": "Pet store sample API for testing",
                "source_type": "openapi",
                "default_audience": "petstore-backend",
                "required_scopes": ["petstore:read", "petstore:write"],
                "validate_url": True,
            }
        }


class UpdateSourceRequest(BaseModel):
    """Request to update an existing upstream source.

    All fields are optional - only provided fields will be updated.
    Note: openapi_url cannot be changed after registration.
    """

    name: str | None = Field(default=None, description="New name for the source")
    description: str | None = Field(default=None, description="New description for the source")
    url: str | None = Field(default=None, description="New service base URL")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Updated API Name",
                "description": "Updated description",
                "url": "https://new-api.example.com",
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
        health_status: str | None = Query(None, description="Filter by health: healthy, degraded, unhealthy, unknown"),
        source_type: str | None = Query(None, description="Filter by type: openapi, workflow"),
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
            openapi_url=request.openapi_url,
            description=request.description,
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
            default_audience=request.default_audience,
            auth_mode=request.auth_mode,
            required_scopes=request.required_scopes,
            validate_url=request.validate_url,
            user_info=user,
            # MCP-specific fields
            mcp_plugin_dir=request.mcp_plugin_dir,
            mcp_manifest_path=request.mcp_manifest_path,
            mcp_transport_type=request.mcp_transport_type,
            mcp_lifecycle_mode=request.mcp_lifecycle_mode,
            mcp_runtime_hint=request.mcp_runtime_hint,
            mcp_command=request.mcp_command,
            mcp_args=request.mcp_args or [],
            mcp_env_vars=request.mcp_env_vars or {},
            mcp_server_url=request.mcp_server_url,
        )
        result = await self.mediator.execute_async(command)
        return self.process(result)

    @patch("/{source_id}")
    async def update_source(
        self,
        source_id: str,
        request: UpdateSourceRequest,
        user: dict = Depends(require_roles("admin", "manager")),
    ):
        """Update an existing upstream source.

        Updates editable fields of the source: name, description, url (service base URL).
        Note: openapi_url cannot be changed after registration.

        **RBAC Protected**: Only users with 'admin' or 'manager' roles can update sources.

        Supports authentication via:
        - Session cookie (from OAuth2 login)
        - JWT Bearer token (for API clients)
        """
        command = UpdateSourceCommand(
            source_id=source_id,
            name=request.name,
            description=request.description,
            url=request.url,
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
