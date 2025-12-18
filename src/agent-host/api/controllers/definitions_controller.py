"""Definitions controller for listing accessible AgentDefinitions.

This controller provides endpoints for users to list and view
the AgentDefinitions they have access to.
"""

import logging
from typing import Any

from classy_fastapi.decorators import get
from fastapi import Depends
from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from neuroglia.mvc import ControllerBase
from pydantic import BaseModel, Field

from api.dependencies import get_current_user
from application.queries.get_definitions_query import GetDefinitionQuery, GetDefinitionsQuery
from application.queries.get_templates_query import GetTemplateQuery, GetTemplatesQuery

logger = logging.getLogger(__name__)


class DefinitionResponse(BaseModel):
    """Response model for an AgentDefinition."""

    id: str
    name: str
    description: str | None = None
    icon: str | None = None
    model: str | None = None
    has_template: bool = False
    is_proactive: bool = False
    is_public: bool = True
    created_at: str | None = None
    updated_at: str | None = None


class DefinitionDetailResponse(DefinitionResponse):
    """Detailed response model for an AgentDefinition."""

    system_prompt: str | None = None
    tools: list[str] = Field(default_factory=list)
    model: str | None = None  # LLM model override (None = use default)
    conversation_template_id: str | None = None


class DefinitionsController(ControllerBase):
    """Controller for AgentDefinition endpoints.

    Provides read-only access for users to list definitions they can use.
    Admin CRUD operations would be in a separate admin_controller.py.
    """

    def __init__(
        self,
        service_provider: ServiceProviderBase,
        mapper: Mapper,
        mediator: Mediator,
    ):
        super().__init__(service_provider, mapper, mediator)

    @get("/")
    async def list_definitions(
        self,
        user: dict[str, Any] = Depends(get_current_user),
    ) -> Any:
        """
        List all accessible AgentDefinitions for the current user.

        **Output:**
        Returns an array of definitions the user can access:
        - System-owned (public) definitions
        - User-owned definitions
        - Definitions shared with the user
        - Role-restricted definitions where user has required roles

        **Use Case:**
        Frontend uses this to display available agents/assistants
        on the home screen for the user to start conversations with.
        """
        query = GetDefinitionsQuery(user_info=user)
        result = await self.mediator.execute_async(query)

        if result.is_success and result.data:
            # Fetch templates to determine is_proactive for each definition
            templates_query = GetTemplatesQuery(user_info=user)
            templates_result = await self.mediator.execute_async(templates_query)

            # Build a lookup map: template_id -> is_proactive
            proactive_templates: dict[str, bool] = {}
            if templates_result.is_success and templates_result.data:
                for template in templates_result.data:
                    proactive_templates[template.id] = template.agent_starts_first

            return [
                DefinitionResponse(
                    id=defn.id,
                    name=defn.name,
                    description=defn.description,
                    icon=defn.icon,
                    model=defn.model,
                    has_template=defn.has_template,
                    is_proactive=proactive_templates.get(defn.conversation_template_id, False) if defn.conversation_template_id else False,
                    is_public=defn.is_public,
                    created_at=defn.created_at.isoformat() if defn.created_at else None,
                    updated_at=defn.updated_at.isoformat() if defn.updated_at else None,
                )
                for defn in result.data
            ]

        return self.process(result)

    @get("/{definition_id}")
    async def get_definition(
        self,
        definition_id: str,
        user: dict[str, Any] = Depends(get_current_user),
    ) -> Any:
        """
        Get a specific AgentDefinition by ID.

        **Input:**
        - `definition_id`: The unique identifier of the definition

        **Output:**
        Returns the full definition details if the user has access.

        **Authorization:**
        Returns 403 if user doesn't have access to this definition.
        """
        query = GetDefinitionQuery(definition_id=definition_id, user_info=user)
        result = await self.mediator.execute_async(query)

        if result.is_success and result.data:
            defn = result.data

            # Determine is_proactive from template
            is_proactive = False
            if defn.conversation_template_id:
                template_query = GetTemplateQuery(template_id=defn.conversation_template_id, user_info=user)
                template_result = await self.mediator.execute_async(template_query)
                if template_result.is_success and template_result.data:
                    is_proactive = template_result.data.agent_starts_first

            return DefinitionDetailResponse(
                id=defn.id,
                name=defn.name,
                description=defn.description,
                icon=defn.icon,
                model=defn.model,
                has_template=defn.has_template,
                is_proactive=is_proactive,
                is_public=defn.is_public,
                created_at=defn.created_at.isoformat() if defn.created_at else None,
                updated_at=defn.updated_at.isoformat() if defn.updated_at else None,
                system_prompt=defn.system_prompt,
                tools=defn.tools or [],
                conversation_template_id=defn.conversation_template_id,
            )

        return self.process(result)
