"""Tools API controller for source tool management.

Provides endpoints for:
- Listing tools for a source
- Getting tool details
- Searching tools across sources
- Getting lightweight tool summaries
"""

from typing import Optional

from classy_fastapi.decorators import delete, get
from fastapi import Depends, Query
from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from neuroglia.mvc import ControllerBase

from api.dependencies import get_current_user, require_roles
from application.commands import DeleteToolCommand
from application.queries import GetSourceToolsQuery, GetToolByIdQuery, GetToolSummariesQuery, SearchToolsQuery


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
        source_id: Optional[str] = Query(None, description="Filter by source ID"),
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
        source_id: Optional[str] = Query(None, description="Filter by source ID"),
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
        source_id: Optional[str] = Query(None, description="Filter by source ID"),
        tags: Optional[str] = Query(None, description="Comma-separated tags to filter by"),
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
