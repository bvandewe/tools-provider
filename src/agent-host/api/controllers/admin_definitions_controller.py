"""Admin controller for AgentDefinition CRUD operations.

This controller provides administrative endpoints for managing AgentDefinitions.
All endpoints require admin role (enforced via require_roles dependency).
"""

import logging
from typing import Any

from classy_fastapi.decorators import delete, get, post, put
from fastapi import Depends
from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from neuroglia.mvc import ControllerBase
from pydantic import BaseModel, Field

from api.dependencies import require_roles
from application.commands.definition.create_definition_command import CreateDefinitionCommand
from application.commands.definition.delete_definition_command import DeleteDefinitionCommand
from application.commands.definition.update_definition_command import UpdateDefinitionCommand
from application.queries.definition.get_definitions_query import GetAllDefinitionsQuery, GetDefinitionQuery
from application.queries.template.get_templates_query import GetTemplatesQuery

logger = logging.getLogger(__name__)


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================


class DefinitionListResponse(BaseModel):
    """Response model for listing AgentDefinitions."""

    id: str
    name: str
    description: str | None = None
    icon: str | None = None
    has_template: bool = False
    conversation_template_id: str | None = None
    conversation_template_name: str | None = None
    is_public: bool = True
    owner_user_id: str | None = None
    created_by: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    version: int = 1


class DefinitionDetailResponse(DefinitionListResponse):
    """Detailed response model for an AgentDefinition."""

    system_prompt: str | None = None
    tools: list[str] = Field(default_factory=list)
    model: str | None = None
    allow_model_selection: bool = True
    conversation_template_id: str | None = None
    required_roles: list[str] = Field(default_factory=list)
    required_scopes: list[str] = Field(default_factory=list)
    allowed_users: list[str] | None = None


class CreateDefinitionRequest(BaseModel):
    """Request model for creating an AgentDefinition."""

    id: str = Field(..., description="Unique slug identifier (immutable)")
    name: str = Field(..., description="Display name")
    system_prompt: str = Field(..., description="LLM system prompt")

    description: str = Field(default="", description="Longer description for UI")
    icon: str | None = Field(default=None, description="Bootstrap icon class")
    tools: list[str] = Field(default_factory=list, description="List of MCP tool IDs")
    model: str | None = Field(default=None, description="LLM model override")
    allow_model_selection: bool = Field(default=True, description="Allow users to change model during conversation")
    conversation_template_id: str | None = Field(default=None, description="Template reference")
    is_public: bool = Field(default=True, description="Available to all authenticated users")
    required_roles: list[str] = Field(default_factory=list, description="JWT roles required")
    required_scopes: list[str] = Field(default_factory=list, description="OAuth scopes required")
    allowed_users: list[str] | None = Field(default=None, description="Explicit user allow list")


class UpdateDefinitionRequest(BaseModel):
    """Request model for updating an AgentDefinition.

    All fields except version are optional. Only provided fields are updated.
    """

    version: int = Field(..., description="Current version for optimistic concurrency")

    name: str | None = Field(default=None, description="Updated display name")
    description: str | None = Field(default=None, description="Updated description")
    icon: str | None = Field(default=None, description="Updated icon")
    system_prompt: str | None = Field(default=None, description="Updated system prompt")
    tools: list[str] | None = Field(default=None, description="Updated tool list")
    model: str | None = Field(default=None, description="Updated model override")
    allow_model_selection: bool | None = Field(default=None, description="Updated allow model selection setting")
    conversation_template_id: str | None = Field(default=None, description="Updated template reference")
    is_public: bool | None = Field(default=None, description="Updated visibility")
    required_roles: list[str] | None = Field(default=None, description="Updated role requirements")
    required_scopes: list[str] | None = Field(default=None, description="Updated scope requirements")
    allowed_users: list[str] | None = Field(default=None, description="Updated allow list")

    # Sentinel flags to explicitly clear nullable fields
    clear_model: bool = Field(default=False, description="Set model to null")
    clear_template: bool = Field(default=False, description="Set template to null")
    clear_allowed_users: bool = Field(default=False, description="Set allowed_users to null")


class DeleteDefinitionRequest(BaseModel):
    """Request model for deleting an AgentDefinition."""

    version: int | None = Field(default=None, description="Version for optimistic concurrency")
    force: bool = Field(default=False, description="Skip version check and force delete")


# =============================================================================
# ADMIN CONTROLLER
# =============================================================================


class AdminDefinitionsController(ControllerBase):
    """Controller for administrative AgentDefinition operations.

    All endpoints require the 'admin' role.

    Provides CRUD operations:
    - GET /admin/definitions - List all definitions
    - GET /admin/definitions/{id} - Get a specific definition
    - POST /admin/definitions - Create a new definition
    - PUT /admin/definitions/{id} - Update a definition
    - DELETE /admin/definitions/{id} - Delete a definition
    """

    def __init__(
        self,
        service_provider: ServiceProviderBase,
        mapper: Mapper,
        mediator: Mediator,
    ):
        from neuroglia.serialization.json import JsonSerializer

        self.service_provider = service_provider
        self.mapper = mapper
        self.mediator = mediator
        self.json_serializer = self.service_provider.get_required_service(JsonSerializer)

        # Initialize ControllerBase
        self.name = "AdminDefinitions"

        # Import here to avoid circular imports
        from classy_fastapi.routable import Routable
        from neuroglia.mvc.controller_base import generate_unique_id_function

        # Override prefix to /admin/definitions instead of default /admin-definitions
        Routable.__init__(
            self,
            prefix="/admin/definitions",
            tags=["Admin - Definitions"],
            generate_unique_id_function=generate_unique_id_function,
        )

    @get(
        "/",
        response_model=list[DefinitionListResponse],
        summary="List all AgentDefinitions",
        description="Returns all AgentDefinitions in the system (admin access only).",
    )
    async def list_definitions(
        self,
        include_system: bool = True,
        owner_user_id: str | None = None,
        user: dict[str, Any] = Depends(require_roles("admin")),
    ) -> Any:
        """List all AgentDefinitions.

        **Parameters:**
        - `include_system`: Include system-owned definitions (default: true)
        - `owner_user_id`: Filter by specific owner

        **Returns:**
        Array of all definitions in the system.
        """
        query = GetAllDefinitionsQuery(
            include_system=include_system,
            owner_user_id=owner_user_id,
        )
        result = await self.mediator.execute_async(query)

        if result.is_success and result.data:
            # Fetch all templates to build a name lookup map
            template_names: dict[str, str] = {}
            templates_result = await self.mediator.execute_async(GetTemplatesQuery(user_info=user))
            if templates_result.is_success and templates_result.data:
                template_names = {t.id: t.name for t in templates_result.data}

            return [
                DefinitionListResponse(
                    id=defn.id,
                    name=defn.name,
                    description=defn.description,
                    icon=defn.icon,
                    has_template=defn.has_template,
                    conversation_template_id=defn.conversation_template_id,
                    conversation_template_name=template_names.get(defn.conversation_template_id) if defn.conversation_template_id else None,
                    is_public=defn.is_public,
                    owner_user_id=defn.owner_user_id,
                    created_by=defn.created_by,
                    created_at=defn.created_at.isoformat() if defn.created_at else None,
                    updated_at=defn.updated_at.isoformat() if defn.updated_at else None,
                    version=defn.version,
                )
                for defn in result.data
            ]

        return self.process(result)

    @get(
        "/{definition_id}",
        response_model=DefinitionDetailResponse,
        summary="Get an AgentDefinition",
        description="Returns a specific AgentDefinition by ID (admin access only).",
    )
    async def get_definition(
        self,
        definition_id: str,
        user: dict[str, Any] = Depends(require_roles("admin")),
    ) -> Any:
        """Get a specific AgentDefinition by ID.

        **Parameters:**
        - `definition_id`: The unique identifier of the definition

        **Returns:**
        The full definition details.
        """
        # Use the regular query but as admin we have implicit access
        query = GetDefinitionQuery(definition_id=definition_id, user_info=user)
        result = await self.mediator.execute_async(query)

        if result.is_success and result.data:
            defn = result.data
            return DefinitionDetailResponse(
                id=defn.id,
                name=defn.name,
                description=defn.description,
                icon=defn.icon,
                has_template=defn.has_template,
                is_public=defn.is_public,
                owner_user_id=defn.owner_user_id,
                created_by=defn.created_by,
                created_at=defn.created_at.isoformat() if defn.created_at else None,
                updated_at=defn.updated_at.isoformat() if defn.updated_at else None,
                version=defn.version,
                system_prompt=defn.system_prompt,
                tools=defn.tools or [],
                model=defn.model,
                allow_model_selection=defn.allow_model_selection,
                conversation_template_id=defn.conversation_template_id,
                required_roles=defn.required_roles or [],
                required_scopes=defn.required_scopes or [],
                allowed_users=defn.allowed_users,
            )

        return self.process(result)

    @post(
        "/",
        response_model=DefinitionDetailResponse,
        summary="Create an AgentDefinition",
        description="Creates a new AgentDefinition (admin access only).",
        status_code=201,
    )
    async def create_definition(
        self,
        request: CreateDefinitionRequest,
        user: dict[str, Any] = Depends(require_roles("admin")),
    ) -> Any:
        """Create a new AgentDefinition.

        **Request Body:**
        - `id`: Unique slug identifier (immutable after creation)
        - `name`: Display name
        - `system_prompt`: LLM system prompt (required)
        - Other fields are optional

        **Returns:**
        The created definition.
        """
        command = CreateDefinitionCommand(
            id=request.id,
            name=request.name,
            system_prompt=request.system_prompt,
            description=request.description,
            icon=request.icon,
            tools=request.tools,
            model=request.model,
            allow_model_selection=request.allow_model_selection,
            conversation_template_id=request.conversation_template_id,
            is_public=request.is_public,
            required_roles=request.required_roles,
            required_scopes=request.required_scopes,
            allowed_users=request.allowed_users,
            user_info=user,
        )
        result = await self.mediator.execute_async(command)

        if result.is_success and result.data:
            dto = result.data
            return DefinitionDetailResponse(
                id=dto.id,
                name=dto.name,
                description=dto.description,
                icon=dto.icon,
                has_template=dto.has_template,
                is_public=dto.is_public,
                owner_user_id=dto.owner_user_id,
                created_by=dto.created_by,
                created_at=dto.created_at.isoformat() if dto.created_at else None,
                updated_at=dto.updated_at.isoformat() if dto.updated_at else None,
                version=dto.version,
                system_prompt=dto.system_prompt,
                tools=dto.tools or [],
                model=dto.model,
                allow_model_selection=dto.allow_model_selection,
                conversation_template_id=dto.conversation_template_id,
                required_roles=dto.required_roles or [],
                required_scopes=dto.required_scopes or [],
                allowed_users=dto.allowed_users,
            )

        return self.process(result)

    @put(
        "/{definition_id}",
        response_model=DefinitionDetailResponse,
        summary="Update an AgentDefinition",
        description="Updates an existing AgentDefinition (admin access only).",
    )
    async def update_definition(
        self,
        definition_id: str,
        request: UpdateDefinitionRequest,
        user: dict[str, Any] = Depends(require_roles("admin")),
    ) -> Any:
        """Update an existing AgentDefinition.

        Uses optimistic concurrency - provide the current version
        to ensure no concurrent modifications.

        **Parameters:**
        - `definition_id`: The ID of the definition to update

        **Request Body:**
        - `version`: Current version (required for concurrency check)
        - Other fields are optional - only provided fields are updated

        **Returns:**
        The updated definition.
        """
        command = UpdateDefinitionCommand(
            id=definition_id,
            version=request.version,
            name=request.name,
            description=request.description,
            icon=request.icon,
            system_prompt=request.system_prompt,
            tools=request.tools,
            model=request.model,
            allow_model_selection=request.allow_model_selection,
            conversation_template_id=request.conversation_template_id,
            is_public=request.is_public,
            required_roles=request.required_roles,
            required_scopes=request.required_scopes,
            allowed_users=request.allowed_users,
            clear_model=request.clear_model,
            clear_template=request.clear_template,
            clear_allowed_users=request.clear_allowed_users,
            user_info=user,
        )
        result = await self.mediator.execute_async(command)

        if result.is_success and result.data:
            dto = result.data
            return DefinitionDetailResponse(
                id=dto.id,
                name=dto.name,
                description=dto.description,
                icon=dto.icon,
                has_template=dto.has_template,
                is_public=dto.is_public,
                owner_user_id=dto.owner_user_id,
                created_by=dto.created_by,
                created_at=dto.created_at.isoformat() if dto.created_at else None,
                updated_at=dto.updated_at.isoformat() if dto.updated_at else None,
                version=dto.version,
                system_prompt=dto.system_prompt,
                tools=dto.tools or [],
                model=dto.model,
                allow_model_selection=dto.allow_model_selection,
                conversation_template_id=dto.conversation_template_id,
                required_roles=dto.required_roles or [],
                required_scopes=dto.required_scopes or [],
                allowed_users=dto.allowed_users,
            )

        return self.process(result)

    @delete(
        "/{definition_id}",
        summary="Delete an AgentDefinition",
        description="Deletes an AgentDefinition (admin access only).",
        status_code=204,
    )
    async def delete_definition(
        self,
        definition_id: str,
        version: int | None = None,
        force: bool = False,
        user: dict[str, Any] = Depends(require_roles("admin")),
    ) -> Any:
        """Delete an AgentDefinition.

        **Parameters:**
        - `definition_id`: The ID of the definition to delete
        - `version`: Optional version for optimistic concurrency
        - `force`: Skip version check and force delete

        **Returns:**
        No content on success.
        """
        command = DeleteDefinitionCommand(
            id=definition_id,
            version=version,
            force=force,
            user_info=user,
        )
        result = await self.mediator.execute_async(command)

        if result.is_success:
            return None  # 204 No Content

        return self.process(result)
