"""Tools API controller for source tool management.

Provides endpoints for:
- Listing tools for a source
- Getting tool details
- Searching tools across sources
- Getting lightweight tool summaries
"""

from classy_fastapi.decorators import delete, get, post, put
from fastapi import Depends, HTTPException, Query, status
from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from neuroglia.mvc import ControllerBase
from pydantic import BaseModel, Field

from api.dependencies import get_current_user, require_roles
from application.commands import AddLabelToToolCommand, DeleteToolCommand, DisableToolCommand, EnableToolCommand, RemoveLabelFromToolCommand, UpdateToolCommand
from application.queries import GetSourceByIdQuery, GetSourceToolsQuery, GetToolByIdQuery, GetToolSummariesQuery, SearchToolsQuery

# ============================================================================
# REQUEST MODELS
# ============================================================================


class DisableToolRequest(BaseModel):
    """Request to disable a tool."""

    reason: str | None = Field(default=None, description="Reason for disabling the tool")

    class Config:
        json_schema_extra = {
            "example": {
                "reason": "Tool is deprecated and should not be used",
            }
        }


class UpdateToolRequest(BaseModel):
    """Request to update tool metadata (name and/or description).

    Use this to fix poorly named tools or improve descriptions that
    were auto-discovered from low-quality upstream OpenAPI specs.
    Changes will be reflected to AI agents.
    """

    tool_name: str | None = Field(default=None, description="New display name for the tool (overrides auto-discovered name)")
    description: str | None = Field(default=None, description="New description for the tool (overrides auto-discovered description)")

    class Config:
        json_schema_extra = {
            "example": {
                "tool_name": "create_pizza_order",
                "description": "Creates a new pizza order with the specified toppings and delivery address",
            }
        }


class ToolsController(ControllerBase):
    """Controller for source tool discovery and listing endpoints.

    Provides read-only access to tools discovered from upstream sources.
    Tools are created/updated automatically during source inventory refresh.

    All endpoints require authentication via:
    - Session cookie (from OAuth2 login)
    - JWT Bearer token (for API clients)
    """

    def __init__(self, service_provider: ServiceProviderBase, mapper: Mapper, mediator: Mediator):
        super().__init__(service_provider, mapper, mediator)

    # =========================================================================
    # TOOL LISTING
    # =========================================================================

    @get("/")
    async def list_tools(
        self,
        source_id: str | None = Query(None, description="Filter by source ID"),
        include_disabled: bool = Query(False, description="Include disabled tools"),
        include_deprecated: bool = Query(False, description="Include deprecated tools"),
        user: dict = Depends(get_current_user),
    ):
        """List tools with optional filtering.

        Returns tools for a specific source or all sources.
        By default, only enabled and active tools are returned.

        Supports authentication via:
        - Session cookie (from OAuth2 login)
        - JWT Bearer token (for API clients)
        """
        if source_id:
            query = GetSourceToolsQuery(
                source_id=source_id,
                include_disabled=include_disabled,
                include_deprecated=include_deprecated,
                user_info=user,
            )
        else:
            # Use summaries for listing all tools (lighter payload)
            query = GetToolSummariesQuery(
                source_id=None,
                include_disabled=include_disabled,
                user_info=user,
            )
        result = await self.mediator.execute_async(query)
        return self.process(result)

    @get("/summaries")
    async def get_tool_summaries(
        self,
        source_id: str | None = Query(None, description="Filter by source ID"),
        include_disabled: bool = Query(False, description="Include disabled tools"),
        user: dict = Depends(get_current_user),
    ):
        """Get lightweight tool summaries for listing.

        Returns SourceToolSummaryDto which excludes the full definition
        for faster queries and smaller payloads. Ideal for populating
        dropdowns or tool selection UIs.

        Supports authentication via:
        - Session cookie (from OAuth2 login)
        - JWT Bearer token (for API clients)
        """
        query = GetToolSummariesQuery(
            source_id=source_id,
            include_disabled=include_disabled,
            user_info=user,
        )
        result = await self.mediator.execute_async(query)
        return self.process(result)

    @get("/search")
    async def search_tools(
        self,
        q: str = Query(..., min_length=2, description="Search query (min 2 chars)"),
        source_id: str | None = Query(None, description="Filter by source ID"),
        tags: str | None = Query(None, description="Comma-separated tags to filter by"),
        include_disabled: bool = Query(False, description="Include disabled tools"),
        user: dict = Depends(get_current_user),
    ):
        """Search tools by name, description, or tags.

        Performs text search across tool names and descriptions.
        Optionally filter by source and/or tags.

        Supports authentication via:
        - Session cookie (from OAuth2 login)
        - JWT Bearer token (for API clients)
        """
        # Parse comma-separated tags
        tag_list = [t.strip() for t in tags.split(",")] if tags else None

        query = SearchToolsQuery(
            query=q,
            source_id=source_id,
            tags=tag_list,
            include_disabled=include_disabled,
            user_info=user,
        )
        result = await self.mediator.execute_async(query)
        return self.process(result)

    # =========================================================================
    # ADMIN OPERATIONS (must be before /{tool_id} routes to match first)
    # =========================================================================

    @get("/diagnostics/sync-status")
    async def check_sync_status(
        self,
        sample_size: int = Query(50, description="Number of tools to sample (0 = check all)"),
        user: dict = Depends(require_roles("admin")),
    ):
        """Check if tools in read model (MongoDB) exist in write model (EventStoreDB).

        This diagnostic endpoint detects "orphaned" tools - tools that appear
        in the UI but cannot be modified because their event stream is missing.
        This can happen if EventStoreDB was cleared but MongoDB wasn't.

        **Resolution:** Refresh the source inventory to recreate missing tools.

        **Admin Only**: Only users with 'admin' role can run diagnostics.

        Supports authentication via:
        - Session cookie (from OAuth2 login)
        - JWT Bearer token (for API clients)
        """
        from application.queries import CheckToolSyncStatusQuery

        query = CheckToolSyncStatusQuery(
            sample_size=sample_size,
            user_info=user,
        )
        result = await self.mediator.execute_async(query)
        return self.process(result)

    @delete("/orphaned/cleanup")
    async def cleanup_orphaned_tools(
        self,
        dry_run: bool = Query(True, description="If true, only report orphans without deleting"),
        user: dict = Depends(require_roles("admin")),
    ):
        """Find and optionally delete orphaned tools.

        Orphaned tools are tools whose upstream source no longer exists.
        This can happen if a source was deleted before cascading deletion
        was implemented.

        By default, this runs in dry-run mode which only reports orphaned
        tools without deleting them. Set dry_run=false to actually delete.

        **Admin Only**: Only users with 'admin' role can run cleanup.

        Supports authentication via:
        - Session cookie (from OAuth2 login)
        - JWT Bearer token (for API clients)
        """
        from application.commands import CleanupOrphanedToolsCommand

        command = CleanupOrphanedToolsCommand(
            dry_run=dry_run,
            reason="Admin-initiated orphaned tools cleanup",
            user_info=user,
        )
        result = await self.mediator.execute_async(command)
        return self.process(result)

    # =========================================================================
    # TOOL DETAILS
    # =========================================================================

    @get("/{tool_id}")
    async def get_tool(
        self,
        tool_id: str,
        user: dict = Depends(get_current_user),
    ):
        """Get a single tool by ID.

        Returns full tool details including the complete definition
        with input schema and execution profile.

        Tool IDs follow the format: "{source_id}:{operation_id}"

        Supports authentication via:
        - Session cookie (from OAuth2 login)
        - JWT Bearer token (for API clients)
        """
        query = GetToolByIdQuery(tool_id=tool_id, user_info=user)
        result = await self.mediator.execute_async(query)
        return self.process(result)

    @put("/{tool_id}")
    async def update_tool(
        self,
        tool_id: str,
        request: UpdateToolRequest,
        user: dict = Depends(require_roles("admin", "manager")),
    ):
        """Update tool metadata (name and/or description).

        Use this endpoint to fix poorly named tools or improve descriptions
        that were auto-discovered from low-quality upstream OpenAPI specs.
        Changes are persisted and will be reflected to AI agents.

        At least one of tool_name or description must be provided.

        Tool IDs follow the format: "{source_id}:{operation_id}"

        **RBAC Protected**: Only users with 'admin' or 'manager' roles can update tools.

        Supports authentication via:
        - Session cookie (from OAuth2 login)
        - JWT Bearer token (for API clients)
        """
        # Validate at least one field is provided
        if request.tool_name is None and request.description is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one of tool_name or description must be provided",
            )

        command = UpdateToolCommand(
            tool_id=tool_id,
            tool_name=request.tool_name,
            description=request.description,
            user_info=user,
        )
        result = await self.mediator.execute_async(command)
        return self.process(result)

    @get("/{tool_id}/source")
    async def get_tool_source(
        self,
        tool_id: str,
        user: dict = Depends(require_roles("admin")),
    ):
        """Get source information for a tool.

        Returns details about the upstream service that provides this tool,
        including the OpenAPI service URL and configuration.

        Tool IDs can be provided in two formats:
        - Full format: "{source_id}:{operation_id}"
        - Short format: "{operation_id}" (will search for the tool by operation_id)

        **Admin Only**: Only users with 'admin' role can view source details.

        Supports authentication via:
        - Session cookie (from OAuth2 login)
        - JWT Bearer token (for API clients)
        """
        # Determine source_id - either from tool_id format or by searching
        if ":" in tool_id:
            # Full format: extract source_id directly
            source_id = tool_id.split(":")[0]
        else:
            # Short format: search for tool by operation_id/tool_name
            search_query = SearchToolsQuery(
                query=tool_id,
                source_id=None,
                tags=None,
                include_disabled=True,
                user_info=user,
            )
            search_result = await self.mediator.execute_async(search_query)

            if not search_result.is_success or not search_result.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Tool not found: {tool_id}",
                )

            # Find exact match by operation_id or tool_name
            matching_tool = None
            for tool in search_result.data:
                if tool.operation_id == tool_id or tool.tool_name == tool_id:
                    matching_tool = tool
                    break

            if not matching_tool:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Tool not found: {tool_id}",
                )

            source_id = matching_tool.source_id

        # Get source details
        source_query = GetSourceByIdQuery(source_id=source_id, user_info=user)
        source_result = await self.mediator.execute_async(source_query)

        if not source_result.is_success:
            return self.process(source_result)

        source = source_result.data

        # Return source info relevant for tool inspection
        return {
            "source_id": source.id,
            "source_name": source.name,
            "source_url": source.url,
            "openapi_url": source.openapi_url,
            "source_type": source.source_type.value if hasattr(source.source_type, "value") else str(source.source_type),
            "is_enabled": source.is_enabled,
            "health_status": source.health_status.value if hasattr(source.health_status, "value") else str(source.health_status),
            "last_sync_at": source.last_sync_at.isoformat() if source.last_sync_at else None,
            "default_audience": source.default_audience,
            "tool_count": source.inventory_count,
        }

    # =========================================================================
    # ENABLE/DISABLE OPERATIONS
    # =========================================================================

    @post("/{tool_id}/enable")
    async def enable_tool(
        self,
        tool_id: str,
        user: dict = Depends(require_roles("admin", "manager")),
    ):
        """Enable a disabled tool.

        Enabled tools can be included in ToolGroups and made available
        to AI agents. This reverses a previous disable action.

        Tool IDs follow the format: "{source_id}:{operation_id}"

        **RBAC Protected**: Only users with 'admin' or 'manager' roles can enable tools.

        Supports authentication via:
        - Session cookie (from OAuth2 login)
        - JWT Bearer token (for API clients)
        """
        command = EnableToolCommand(
            tool_id=tool_id,
            user_info=user,
        )
        result = await self.mediator.execute_async(command)
        return self.process(result)

    @post("/{tool_id}/disable")
    async def disable_tool(
        self,
        tool_id: str,
        request: DisableToolRequest = DisableToolRequest(),
        user: dict = Depends(require_roles("admin", "manager")),
    ):
        """Disable a tool.

        Disabled tools are excluded from ALL ToolGroups regardless of
        selectors or explicit additions. Use this to prevent dangerous
        or inappropriate tools from being exposed to AI agents.

        Tool IDs follow the format: "{source_id}:{operation_id}"

        **RBAC Protected**: Only users with 'admin' or 'manager' roles can disable tools.

        Supports authentication via:
        - Session cookie (from OAuth2 login)
        - JWT Bearer token (for API clients)
        """
        command = DisableToolCommand(
            tool_id=tool_id,
            reason=request.reason,
            user_info=user,
        )
        result = await self.mediator.execute_async(command)
        return self.process(result)

    # =========================================================================
    # DELETE OPERATIONS
    # =========================================================================

    @delete("/{tool_id}")
    async def delete_tool(
        self,
        tool_id: str,
        user: dict = Depends(require_roles("admin")),
    ):
        """Permanently delete a source tool.

        This is a hard delete that removes the tool from both the
        event store and read model. This operation cannot be undone.

        Tool IDs follow the format: "{source_id}:{operation_id}"

        **Admin Only**: Only users with 'admin' role can delete tools.

        Supports authentication via:
        - Session cookie (from OAuth2 login)
        - JWT Bearer token (for API clients)
        """
        command = DeleteToolCommand(
            tool_id=tool_id,
            user_info=user,
        )
        result = await self.mediator.execute_async(command)
        return self.process(result)

    # =========================================================================
    # LABEL OPERATIONS
    # =========================================================================

    @post("/{tool_id}/labels/{label_id}")
    async def add_label_to_tool(
        self,
        tool_id: str,
        label_id: str,
        user: dict = Depends(require_roles("admin", "manager")),
    ):
        """Add a label to a tool.

        Labels help categorize tools for filtering and organization.
        A tool can have multiple labels assigned.

        Tool IDs follow the format: "{source_id}:{operation_id}"

        **RBAC Protected**: Only users with 'admin' or 'manager' roles can manage labels.

        Supports authentication via:
        - Session cookie (from OAuth2 login)
        - JWT Bearer token (for API clients)
        """
        command = AddLabelToToolCommand(
            tool_id=tool_id,
            label_id=label_id,
            user_info=user,
        )
        result = await self.mediator.execute_async(command)
        return self.process(result)

    @delete("/{tool_id}/labels/{label_id}")
    async def remove_label_from_tool(
        self,
        tool_id: str,
        label_id: str,
        user: dict = Depends(require_roles("admin", "manager")),
    ):
        """Remove a label from a tool.

        This removes the label association but does not delete the label itself.

        Tool IDs follow the format: "{source_id}:{operation_id}"

        **RBAC Protected**: Only users with 'admin' or 'manager' roles can manage labels.

        Supports authentication via:
        - Session cookie (from OAuth2 login)
        - JWT Bearer token (for API clients)
        """
        command = RemoveLabelFromToolCommand(
            tool_id=tool_id,
            label_id=label_id,
            user_info=user,
        )
        result = await self.mediator.execute_async(command)
        return self.process(result)
