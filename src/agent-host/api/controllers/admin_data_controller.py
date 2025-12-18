"""Admin controller for data management operations.

This controller provides administrative endpoints for managing application data,
including the ability to reset all data and re-seed from YAML files.

All endpoints require the 'admin' role.
"""

import logging

from classy_fastapi.decorators import post
from fastapi import Depends
from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from neuroglia.mvc import ControllerBase
from pydantic import BaseModel, Field

from api.dependencies import require_roles
from application.commands.admin.reset_database_command import ResetDatabaseCommand
from infrastructure.database_resetter import ResetDatabaseResult

logger = logging.getLogger(__name__)


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================


class ResetDatabaseRequest(BaseModel):
    """Request model for resetting the database.

    This is a destructive operation that clears all data from both
    WriteModel (EventStoreDB) and ReadModel (MongoDB), then re-seeds
    from YAML files.
    """

    confirm: bool = Field(
        default=False,
        description="Safety flag - must be True to proceed. Prevents accidental resets.",
    )


class ResetDatabaseResponse(BaseModel):
    """Response model for database reset operation."""

    success: bool = Field(description="Whether the operation completed successfully")
    cleared_write_model: bool = Field(description="Whether EventStoreDB was cleared")
    cleared_read_model: bool = Field(description="Whether MongoDB was cleared")
    seeded: dict[str, int] = Field(
        default_factory=dict,
        description="Counts of entities seeded (skills, definitions, templates)",
    )
    message: str = Field(default="", description="Human-readable summary")
    reset_by: str | None = Field(default=None, description="Username of admin who triggered reset")


# =============================================================================
# ADMIN DATA CONTROLLER
# =============================================================================


class AdminDataController(ControllerBase):
    """Controller for administrative data management operations.

    All endpoints require the 'admin' role.

    Provides operations:
    - POST /admin/data/reset - Reset all data and re-seed from YAML
    """

    def __init__(
        self,
        service_provider: ServiceProviderBase,
        mapper: Mapper,
        mediator: Mediator,
    ):
        self.service_provider = service_provider
        self.mapper = mapper
        self.mediator = mediator

        # Initialize ControllerBase
        self.name = "AdminData"

        # Initialize classy-fastapi Routable
        from classy_fastapi.routable import Routable
        from neuroglia.mvc.controller_base import generate_unique_id_function

        Routable.__init__(
            self,
            prefix="/admin/data",
            tags=["Admin - Data Management"],
            generate_unique_id_function=generate_unique_id_function,
        )

    @post(
        "/reset",
        response_model=ResetDatabaseResponse,
        summary="Reset all data and re-seed",
        description="""
Reset all application data and re-seed from YAML files.

**⚠️ WARNING: This is a destructive operation!**

This operation will:
1. **Clear MongoDB** (ReadModel) - Drops all collections:
   - `conversation` - All conversation projections
   - `agentdefinition` - All agent definition projections
   - `conversationtemplate` - All template projections
   - `appsettings` - Application settings

2. **Clear EventStoreDB** (WriteModel) - Orphans aggregate streams:
   - Old event streams remain but are disconnected from ReadModel
   - For complete ESDB reset, use `make reset-app-data`

3. **Re-seed from YAML files**:
   - Agent definitions from `data/agents/*.yaml`
   - Conversation templates from `data/templates/*.yaml`
   - Skills from `data/skills/*.yaml`

**Use Cases:**
- Development: Reset to clean state after testing
- Demo: Prepare fresh environment for demonstrations
- Testing: Ensure consistent starting state for tests

**Safety:**
- Requires `confirm: true` in request body
- Requires `admin` role
- Operation is logged for audit purposes
""",
    )
    async def reset_database(
        self,
        request: ResetDatabaseRequest,
        user: dict = Depends(require_roles("admin")),
    ) -> ResetDatabaseResponse:
        """Reset all data and re-seed from YAML files.

        Args:
            request: Request with confirmation flag
            user: Authenticated admin user info

        Returns:
            ResetDatabaseResponse with operation results
        """
        logger.warning(f"Database reset requested by: {user.get('preferred_username', user.get('sub', 'unknown'))}")

        # Create and execute command
        command = ResetDatabaseCommand(
            user_info=user,
            confirm=request.confirm,
        )

        result = await self.mediator.execute_async(command)

        # Handle OperationResult
        if not result.is_success:
            # Return error response
            from fastapi import HTTPException

            status_code = getattr(result, "status", 400)
            # OperationResult uses 'detail' for error message
            detail = getattr(result, "detail", "Reset failed")
            raise HTTPException(status_code=status_code, detail=str(detail))

        # Extract the ResetDatabaseResult from OperationResult
        if result.data is None:
            from fastapi import HTTPException

            raise HTTPException(status_code=500, detail="No data returned from reset operation")

        reset_result: ResetDatabaseResult = result.data

        return ResetDatabaseResponse(
            success=True,
            cleared_write_model=reset_result.cleared_write_model,
            cleared_read_model=reset_result.cleared_read_model,
            seeded=reset_result.seeded,
            message=reset_result.message,
            reset_by=reset_result.reset_by,
        )
