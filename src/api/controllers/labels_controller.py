"""Labels API controller for label management.

Provides endpoints for:
- Creating and managing labels
- Listing labels
- Getting label details
"""

from typing import Optional

from classy_fastapi.decorators import delete, get, post, put
from fastapi import Depends, Query
from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from neuroglia.mvc import ControllerBase
from pydantic import BaseModel, Field

from api.dependencies import get_current_user, require_roles
from application.commands.create_label_command import CreateLabelCommand
from application.commands.delete_label_command import DeleteLabelCommand
from application.commands.update_label_command import UpdateLabelCommand
from application.queries.get_labels_query import GetLabelByIdQuery, GetLabelsQuery, GetLabelSummariesQuery

# ============================================================================
# REQUEST MODELS
# ============================================================================


class CreateLabelRequest(BaseModel):
    """Request to create a new label."""

    name: str = Field(..., description="Display name for the label")
    description: str = Field(default="", description="Description of the label's purpose")
    color: str = Field(default="#6b7280", description="CSS color for visual styling (hex or named)")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Production",
                "description": "Tools used in production environments",
                "color": "#ef4444",
            }
        }


class UpdateLabelRequest(BaseModel):
    """Request to update a label."""

    name: Optional[str] = Field(default=None, description="New name (null to keep current)")
    description: Optional[str] = Field(default=None, description="New description (null to keep current)")
    color: Optional[str] = Field(default=None, description="New color (null to keep current)")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Prod",
                "color": "#dc2626",
            }
        }


# ============================================================================
# CONTROLLER
# ============================================================================


class LabelsController(ControllerBase):
    """Controller for label management operations."""

    def __init__(
        self,
        service_provider: ServiceProviderBase,
        mediator: Mediator,
        mapper: Mapper,
    ) -> None:
        super().__init__(service_provider, mediator, mapper)

    # =========================================================================
    # READ OPERATIONS
    # =========================================================================

    @get("/")
    async def get_labels(
        self,
        include_deleted: bool = Query(default=False, description="Include soft-deleted labels"),
        name_filter: Optional[str] = Query(default=None, description="Filter by name (partial match)"),
        user: dict = Depends(get_current_user),
    ):
        """Get all labels.

        Returns a list of all labels with their details.
        Optionally filter by name or include deleted labels.

        Supports authentication via:
        - Session cookie (from OAuth2 login)
        - JWT Bearer token (for API clients)
        """
        query = GetLabelsQuery(
            include_deleted=include_deleted,
            name_filter=name_filter,
            user_info=user,
        )
        result = await self.mediator.execute_async(query)
        return self.process(result)

    @get("/summaries")
    async def get_label_summaries(
        self,
        user: dict = Depends(get_current_user),
    ):
        """Get lightweight label summaries.

        Returns a list of labels with minimal data for dropdowns and selectors.
        Only includes non-deleted labels.

        Supports authentication via:
        - Session cookie (from OAuth2 login)
        - JWT Bearer token (for API clients)
        """
        query = GetLabelSummariesQuery(user_info=user)
        result = await self.mediator.execute_async(query)
        return self.process(result)

    @get("/{label_id}")
    async def get_label(
        self,
        label_id: str,
        user: dict = Depends(get_current_user),
    ):
        """Get a single label by ID.

        Returns full label details including usage statistics.

        Supports authentication via:
        - Session cookie (from OAuth2 login)
        - JWT Bearer token (for API clients)
        """
        query = GetLabelByIdQuery(label_id=label_id, user_info=user)
        result = await self.mediator.execute_async(query)
        return self.process(result)

    # =========================================================================
    # WRITE OPERATIONS (Require admin/manager role)
    # =========================================================================

    @post("/")
    async def create_label(
        self,
        request: CreateLabelRequest,
        user: dict = Depends(require_roles("admin", "manager")),
    ):
        """Create a new label.

        Creates a label that can be assigned to tools for organization.

        **RBAC Protected**: Only users with 'admin' or 'manager' roles can create labels.

        Supports authentication via:
        - Session cookie (from OAuth2 login)
        - JWT Bearer token (for API clients)
        """
        command = CreateLabelCommand(
            name=request.name,
            description=request.description,
            color=request.color,
            user_info=user,
        )
        result = await self.mediator.execute_async(command)
        return self.process(result)

    @put("/{label_id}")
    async def update_label(
        self,
        label_id: str,
        request: UpdateLabelRequest,
        user: dict = Depends(require_roles("admin", "manager")),
    ):
        """Update a label's properties.

        Updates name, description, and/or color of an existing label.

        **RBAC Protected**: Only users with 'admin' or 'manager' roles can update labels.

        Supports authentication via:
        - Session cookie (from OAuth2 login)
        - JWT Bearer token (for API clients)
        """
        command = UpdateLabelCommand(
            label_id=label_id,
            name=request.name,
            description=request.description,
            color=request.color,
            user_info=user,
        )
        result = await self.mediator.execute_async(command)
        return self.process(result)

    @delete("/{label_id}")
    async def delete_label(
        self,
        label_id: str,
        user: dict = Depends(require_roles("admin", "manager")),
    ):
        """Delete a label.

        Soft-deletes the label. The label will be removed from all associated tools.

        **RBAC Protected**: Only users with 'admin' or 'manager' roles can delete labels.

        Supports authentication via:
        - Session cookie (from OAuth2 login)
        - JWT Bearer token (for API clients)
        """
        command = DeleteLabelCommand(label_id=label_id, user_info=user)
        result = await self.mediator.execute_async(command)
        return self.process(result)
