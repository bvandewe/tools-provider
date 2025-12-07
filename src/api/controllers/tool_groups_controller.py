"""Tool Groups API controller for tool group management.

Provides endpoints for:
- Creating and managing tool groups
- Adding/removing selectors
- Explicit tool management
- Tool exclusions
- Resolving group tools
"""

from typing import List, Optional

from classy_fastapi.decorators import delete, get, post, put
from fastapi import Depends, Query
from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from neuroglia.mvc import ControllerBase
from pydantic import BaseModel, Field

from api.dependencies import get_current_user, require_roles
from application.commands import (
    ActivateToolGroupCommand,
    AddExplicitToolCommand,
    AddSelectorCommand,
    CreateToolGroupCommand,
    DeactivateToolGroupCommand,
    DeleteToolGroupCommand,
    ExcludeToolCommand,
    IncludeToolCommand,
    RemoveExplicitToolCommand,
    RemoveSelectorCommand,
    SelectorInput,
    SyncToolGroupSelectorsCommand,
    SyncToolGroupToolsCommand,
    UpdateToolGroupCommand,
)
from application.queries.get_tool_groups_query import GetGroupToolsQuery, GetToolGroupByIdQuery, GetToolGroupsQuery

# ============================================================================
# REQUEST MODELS
# ============================================================================


class SelectorRequest(BaseModel):
    """Request model for a tool selector."""

    source_pattern: str = Field(default="*", description="Pattern for source name matching (glob or regex:pattern)")
    name_pattern: str = Field(default="*", description="Pattern for tool name matching")
    path_pattern: Optional[str] = Field(default=None, description="Pattern for source path matching")
    required_tags: List[str] = Field(default_factory=list, description="Tags that must be present")
    excluded_tags: List[str] = Field(default_factory=list, description="Tags that must not be present")
    selector_id: Optional[str] = Field(default=None, description="Optional ID (auto-generated if not provided)")

    class Config:
        json_schema_extra = {
            "example": {
                "source_pattern": "billing-*",
                "name_pattern": "create_*",
                "required_tags": ["finance"],
                "excluded_tags": ["deprecated"],
            }
        }

    def to_selector_input(self) -> SelectorInput:
        """Convert to command SelectorInput."""
        return SelectorInput(
            source_pattern=self.source_pattern,
            name_pattern=self.name_pattern,
            path_pattern=self.path_pattern,
            required_tags=self.required_tags,
            excluded_tags=self.excluded_tags,
            selector_id=self.selector_id,
        )


class CreateToolGroupRequest(BaseModel):
    """Request to create a new tool group with optional initial selectors and tools."""

    name: str = Field(..., description="Human-readable name for the group")
    description: str = Field(default="", description="Description of the group's purpose")
    selectors: List[SelectorRequest] = Field(default_factory=list, description="Initial selectors for the group")
    explicit_tool_ids: List[str] = Field(default_factory=list, description="Initial explicit tool IDs")
    excluded_tool_ids: List[str] = Field(default_factory=list, description="Initial excluded tool IDs")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Finance Tools",
                "description": "Tools for financial operations including invoicing and payments",
                "selectors": [
                    {"source_pattern": "billing-*", "name_pattern": "*"},
                    {"source_pattern": "*", "name_pattern": "invoice_*"},
                ],
                "explicit_tool_ids": ["payment-service:process_refund"],
                "excluded_tool_ids": ["billing-service:delete_all_records"],
            }
        }


class UpdateToolGroupRequest(BaseModel):
    """Request to update a tool group's metadata."""

    name: Optional[str] = Field(default=None, description="New name (null to keep current)")
    description: Optional[str] = Field(default=None, description="New description (null to keep current)")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Updated Finance Tools",
                "description": "Updated description for finance tools",
            }
        }


class SyncSelectorsRequest(BaseModel):
    """Request to sync selectors for a group (diff-based update)."""

    selectors: List[SelectorRequest] = Field(default_factory=list, description="Desired selectors for the group")

    class Config:
        json_schema_extra = {
            "example": {
                "selectors": [
                    {"source_pattern": "billing-*", "name_pattern": "*"},
                    {"source_pattern": "*", "name_pattern": "invoice_*"},
                ]
            }
        }


class SyncToolsRequest(BaseModel):
    """Request to sync explicit and excluded tools for a group (diff-based update)."""

    explicit_tool_ids: List[str] = Field(default_factory=list, description="Desired explicit tool IDs")
    excluded_tool_ids: List[str] = Field(default_factory=list, description="Desired excluded tool IDs")

    class Config:
        json_schema_extra = {
            "example": {
                "explicit_tool_ids": ["payment-service:process_refund", "billing-service:create_invoice"],
                "excluded_tool_ids": ["billing-service:delete_all_records"],
            }
        }


class AddSelectorRequest(BaseModel):
    """Request to add a pattern-based selector to a group."""

    selector_id: Optional[str] = Field(default=None, description="Optional ID for the selector (auto-generated if not provided)")
    source_pattern: str = Field(default="*", description="Pattern for source name matching (glob or regex:pattern)")
    name_pattern: str = Field(default="*", description="Pattern for tool name matching")
    path_pattern: Optional[str] = Field(default=None, description="Pattern for source path matching")
    required_tags: List[str] = Field(default_factory=list, description="Tags that must be present")
    excluded_tags: List[str] = Field(default_factory=list, description="Tags that must not be present")

    class Config:
        json_schema_extra = {
            "example": {
                "source_pattern": "billing-*",
                "name_pattern": "create_*",
                "required_tags": ["finance"],
                "excluded_tags": ["deprecated"],
            }
        }


class AddToolRequest(BaseModel):
    """Request to add or manage a tool in a group."""

    tool_id: str = Field(..., description="ID of the tool (format: source_id:operation_id)")

    class Config:
        json_schema_extra = {
            "example": {
                "tool_id": "billing-service:create_invoice",
            }
        }


class ExcludeToolRequest(BaseModel):
    """Request to exclude a tool from a group."""

    tool_id: str = Field(..., description="ID of the tool to exclude")
    reason: Optional[str] = Field(default=None, description="Reason for exclusion")

    class Config:
        json_schema_extra = {
            "example": {
                "tool_id": "billing-service:delete_all_invoices",
                "reason": "Too dangerous for general use",
            }
        }


class DeactivateRequest(BaseModel):
    """Request to deactivate a group."""

    reason: Optional[str] = Field(default=None, description="Reason for deactivation")

    class Config:
        json_schema_extra = {
            "example": {
                "reason": "Under maintenance",
            }
        }


# ============================================================================
# CONTROLLER
# ============================================================================


class ToolGroupsController(ControllerBase):
    """Controller for tool group management endpoints.

    Provides CRUD operations for managing tool groups that curate
    tools for access policy assignment.

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
    async def get_tool_groups(
        self,
        include_inactive: bool = Query(False, description="Include inactive groups"),
        name_filter: Optional[str] = Query(None, description="Filter by name pattern (e.g., 'finance-*')"),
        user: dict = Depends(get_current_user),
    ):
        """List all tool groups with optional filtering.

        Returns active groups by default. Use filters to narrow results.

        Supports authentication via:
        - Session cookie (from OAuth2 login)
        - JWT Bearer token (for API clients)
        """
        query = GetToolGroupsQuery(
            include_inactive=include_inactive,
            name_filter=name_filter,
            user_info=user,
        )
        result = await self.mediator.execute_async(query)
        return self.process(result)

    @get("/{group_id}")
    async def get_tool_group(
        self,
        group_id: str,
        user: dict = Depends(get_current_user),
    ):
        """Get a single tool group by ID with full details.

        Returns complete group information including:
        - All selectors with their patterns
        - Explicitly added tools
        - Excluded tools

        Supports authentication via:
        - Session cookie (from OAuth2 login)
        - JWT Bearer token (for API clients)
        """
        query = GetToolGroupByIdQuery(group_id=group_id, user_info=user)
        result = await self.mediator.execute_async(query)
        return self.process(result)

    @get("/{group_id}/tools")
    async def get_group_tools(
        self,
        group_id: str,
        user: dict = Depends(get_current_user),
    ):
        """Get the resolved tools for a group.

        Computes which tools belong to this group by applying:
        1. Selector pattern matching (OR logic between selectors)
        2. Explicit tool additions
        3. Exclusion removals
        4. Filtering to only enabled tools

        Returns the actual list of tool IDs that would be exposed
        to agents with access to this group.

        Supports authentication via:
        - Session cookie (from OAuth2 login)
        - JWT Bearer token (for API clients)
        """
        query = GetGroupToolsQuery(group_id=group_id, user_info=user)
        result = await self.mediator.execute_async(query)
        return self.process(result)

    # =========================================================================
    # WRITE OPERATIONS (Require admin/manager role)
    # =========================================================================

    @post("/")
    async def create_tool_group(
        self,
        request: CreateToolGroupRequest,
        user: dict = Depends(require_roles("admin", "manager")),
    ):
        """Create a new tool group with optional initial configuration.

        Creates a group that can be populated with:
        - Pattern-based selectors for dynamic tool matching
        - Explicit tool references for direct inclusion
        - Exclusions to override selector matches

        You can provide initial selectors, explicit tools, and exclusions
        at creation time, or add them later via the respective endpoints.

        **RBAC Protected**: Only users with 'admin' or 'manager' roles can create groups.

        Supports authentication via:
        - Session cookie (from OAuth2 login)
        - JWT Bearer token (for API clients)
        """
        command = CreateToolGroupCommand(
            name=request.name,
            description=request.description,
            selectors=[s.to_selector_input() for s in request.selectors],
            explicit_tool_ids=request.explicit_tool_ids,
            excluded_tool_ids=request.excluded_tool_ids,
            user_info=user,
        )
        result = await self.mediator.execute_async(command)
        return self.process(result)

    @put("/{group_id}")
    async def update_tool_group(
        self,
        group_id: str,
        request: UpdateToolGroupRequest,
        user: dict = Depends(require_roles("admin", "manager")),
    ):
        """Update a tool group's name and/or description.

        Only provided fields are updated; null fields are ignored.

        **RBAC Protected**: Only users with 'admin' or 'manager' roles can update groups.

        Supports authentication via:
        - Session cookie (from OAuth2 login)
        - JWT Bearer token (for API clients)
        """
        command = UpdateToolGroupCommand(
            group_id=group_id,
            name=request.name,
            description=request.description,
            user_info=user,
        )
        result = await self.mediator.execute_async(command)
        return self.process(result)

    @delete("/{group_id}")
    async def delete_tool_group(
        self,
        group_id: str,
        user: dict = Depends(require_roles("admin", "manager")),
    ):
        """Delete a tool group.

        This removes the group from the system. Any access policies
        referencing this group should be updated.

        **RBAC Protected**: Only users with 'admin' or 'manager' roles can delete groups.

        Supports authentication via:
        - Session cookie (from OAuth2 login)
        - JWT Bearer token (for API clients)
        """
        command = DeleteToolGroupCommand(
            group_id=group_id,
            user_info=user,
        )
        result = await self.mediator.execute_async(command)
        return self.process(result)

    # =========================================================================
    # SELECTOR MANAGEMENT
    # =========================================================================

    @post("/{group_id}/selectors")
    async def add_selector(
        self,
        group_id: str,
        request: AddSelectorRequest,
        user: dict = Depends(require_roles("admin", "manager")),
    ):
        """Add a pattern-based selector to the group.

        Selectors define patterns that match tools:
        - source_pattern: Match source names (e.g., 'billing-*')
        - name_pattern: Match tool names (e.g., 'create_*')
        - path_pattern: Match source paths (e.g., '/api/v1/*')
        - required_tags: All must be present
        - excluded_tags: None must be present

        Patterns support:
        - Glob syntax: * (any chars), ? (single char)
        - Regex: prefix with 'regex:' (e.g., 'regex:^create_.*')

        Multiple selectors use OR logic - a tool matches if it
        matches ANY selector.

        **RBAC Protected**: Only users with 'admin' or 'manager' roles can modify groups.

        Supports authentication via:
        - Session cookie (from OAuth2 login)
        - JWT Bearer token (for API clients)
        """
        command = AddSelectorCommand(
            group_id=group_id,
            selector_id=request.selector_id,
            source_pattern=request.source_pattern,
            name_pattern=request.name_pattern,
            path_pattern=request.path_pattern,
            required_tags=request.required_tags,
            excluded_tags=request.excluded_tags,
            user_info=user,
        )
        result = await self.mediator.execute_async(command)
        return self.process(result)

    @delete("/{group_id}/selectors/{selector_id}")
    async def remove_selector(
        self,
        group_id: str,
        selector_id: str,
        user: dict = Depends(require_roles("admin", "manager")),
    ):
        """Remove a selector from the group.

        **RBAC Protected**: Only users with 'admin' or 'manager' roles can modify groups.

        Supports authentication via:
        - Session cookie (from OAuth2 login)
        - JWT Bearer token (for API clients)
        """
        command = RemoveSelectorCommand(
            group_id=group_id,
            selector_id=selector_id,
            user_info=user,
        )
        result = await self.mediator.execute_async(command)
        return self.process(result)

    @put("/{group_id}/selectors")
    async def sync_selectors(
        self,
        group_id: str,
        request: SyncSelectorsRequest,
        user: dict = Depends(require_roles("admin", "manager")),
    ):
        """Sync selectors for a group (diff-based update).

        This endpoint performs a smart diff between the current selectors
        and the desired state:
        - Selectors that exist but are not in the request are removed
        - Selectors that don't exist but are in the request are added
        - Selectors that match are unchanged (no events emitted)

        This is more efficient than removing all and re-adding, as it
        only emits events for actual changes.

        **RBAC Protected**: Only users with 'admin' or 'manager' roles can modify groups.

        Supports authentication via:
        - Session cookie (from OAuth2 login)
        - JWT Bearer token (for API clients)
        """
        command = SyncToolGroupSelectorsCommand(
            group_id=group_id,
            selectors=[s.to_selector_input() for s in request.selectors],
            user_info=user,
        )
        result = await self.mediator.execute_async(command)
        return self.process(result)

    @put("/{group_id}/tools")
    async def sync_tools(
        self,
        group_id: str,
        request: SyncToolsRequest,
        user: dict = Depends(require_roles("admin", "manager")),
    ):
        """Sync explicit and excluded tools for a group (diff-based update).

        This endpoint performs a smart diff between current and desired state
        for both explicit tools and exclusions:
        - Tools that exist but are not in the request are removed
        - Tools that don't exist but are in the request are added
        - Tools that match are unchanged (no events emitted)

        **RBAC Protected**: Only users with 'admin' or 'manager' roles can modify groups.

        Supports authentication via:
        - Session cookie (from OAuth2 login)
        - JWT Bearer token (for API clients)
        """
        command = SyncToolGroupToolsCommand(
            group_id=group_id,
            explicit_tool_ids=request.explicit_tool_ids,
            excluded_tool_ids=request.excluded_tool_ids,
            user_info=user,
        )
        result = await self.mediator.execute_async(command)
        return self.process(result)

    # =========================================================================
    # EXPLICIT TOOL MANAGEMENT
    # =========================================================================

    @post("/{group_id}/tools")
    async def add_explicit_tool(
        self,
        group_id: str,
        request: AddToolRequest,
        user: dict = Depends(require_roles("admin", "manager")),
    ):
        """Explicitly add a tool to the group.

        Explicit tools are always included in the group, regardless
        of selectors. Use this for tools that don't match any pattern
        but should be in the group.

        Tool ID format: source_id:operation_id
        Example: billing-service:create_invoice

        **RBAC Protected**: Only users with 'admin' or 'manager' roles can modify groups.

        Supports authentication via:
        - Session cookie (from OAuth2 login)
        - JWT Bearer token (for API clients)
        """
        command = AddExplicitToolCommand(
            group_id=group_id,
            tool_id=request.tool_id,
            user_info=user,
        )
        result = await self.mediator.execute_async(command)
        return self.process(result)

    @delete("/{group_id}/tools/{tool_id}")
    async def remove_explicit_tool(
        self,
        group_id: str,
        tool_id: str,
        user: dict = Depends(require_roles("admin", "manager")),
    ):
        """Remove an explicitly added tool from the group.

        Note: This only removes explicit additions. If the tool matches
        a selector, it will still be included via that selector.

        **RBAC Protected**: Only users with 'admin' or 'manager' roles can modify groups.

        Supports authentication via:
        - Session cookie (from OAuth2 login)
        - JWT Bearer token (for API clients)
        """
        command = RemoveExplicitToolCommand(
            group_id=group_id,
            tool_id=tool_id,
            user_info=user,
        )
        result = await self.mediator.execute_async(command)
        return self.process(result)

    # =========================================================================
    # EXCLUSION MANAGEMENT
    # =========================================================================

    @post("/{group_id}/exclusions")
    async def exclude_tool(
        self,
        group_id: str,
        request: ExcludeToolRequest,
        user: dict = Depends(require_roles("admin", "manager")),
    ):
        """Exclude a tool from the group.

        Excluded tools are NEVER included, even if they match a selector
        or are explicitly added. Use this to remove dangerous or
        inappropriate tools from a group.

        **RBAC Protected**: Only users with 'admin' or 'manager' roles can modify groups.

        Supports authentication via:
        - Session cookie (from OAuth2 login)
        - JWT Bearer token (for API clients)
        """
        command = ExcludeToolCommand(
            group_id=group_id,
            tool_id=request.tool_id,
            reason=request.reason,
            user_info=user,
        )
        result = await self.mediator.execute_async(command)
        return self.process(result)

    @delete("/{group_id}/exclusions/{tool_id}")
    async def include_tool(
        self,
        group_id: str,
        tool_id: str,
        user: dict = Depends(require_roles("admin", "manager")),
    ):
        """Remove a tool from the exclusion list.

        This re-enables the tool to be included via selectors or
        explicit additions.

        **RBAC Protected**: Only users with 'admin' or 'manager' roles can modify groups.

        Supports authentication via:
        - Session cookie (from OAuth2 login)
        - JWT Bearer token (for API clients)
        """
        command = IncludeToolCommand(
            group_id=group_id,
            tool_id=tool_id,
            user_info=user,
        )
        result = await self.mediator.execute_async(command)
        return self.process(result)

    # =========================================================================
    # LIFECYCLE MANAGEMENT
    # =========================================================================

    @post("/{group_id}/activate")
    async def activate_tool_group(
        self,
        group_id: str,
        user: dict = Depends(require_roles("admin", "manager")),
    ):
        """Activate a deactivated tool group.

        Active groups are included in access policy resolution.

        **RBAC Protected**: Only users with 'admin' or 'manager' roles can modify groups.

        Supports authentication via:
        - Session cookie (from OAuth2 login)
        - JWT Bearer token (for API clients)
        """
        command = ActivateToolGroupCommand(
            group_id=group_id,
            user_info=user,
        )
        result = await self.mediator.execute_async(command)
        return self.process(result)

    @post("/{group_id}/deactivate")
    async def deactivate_tool_group(
        self,
        group_id: str,
        request: DeactivateRequest = DeactivateRequest(),
        user: dict = Depends(require_roles("admin", "manager")),
    ):
        """Deactivate a tool group.

        Deactivated groups are excluded from access policy resolution.
        This is a soft disable - the group and all its configuration
        are preserved.

        **RBAC Protected**: Only users with 'admin' or 'manager' roles can modify groups.

        Supports authentication via:
        - Session cookie (from OAuth2 login)
        - JWT Bearer token (for API clients)
        """
        command = DeactivateToolGroupCommand(
            group_id=group_id,
            reason=request.reason,
            user_info=user,
        )
        result = await self.mediator.execute_async(command)
        return self.process(result)
