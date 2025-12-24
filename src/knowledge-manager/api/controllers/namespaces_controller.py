"""Namespaces controller with full CRUD for namespaces and terms."""

import logging
from typing import Any

from classy_fastapi import delete, get, post, put
from fastapi import Depends, Query
from neuroglia.mediation.mediator import Mediator
from neuroglia.mvc.controller_base import ControllerBase
from pydantic import BaseModel, Field

from api.dependencies import get_current_user, get_mediator, require_roles
from application.commands import (
    AddTermCommand,
    CreateNamespaceCommand,
    DeleteNamespaceCommand,
    RemoveTermCommand,
    UpdateNamespaceCommand,
    UpdateTermCommand,
)
from application.queries import (
    GetNamespaceQuery,
    GetNamespacesQuery,
    GetTermQuery,
    GetTermsQuery,
)
from integration.models import KnowledgeNamespaceDto, KnowledgeTermDto

log = logging.getLogger(__name__)


# ============================================================================
# REQUEST MODELS
# ============================================================================


class CreateNamespaceRequest(BaseModel):
    """Request to create a new namespace."""

    slug: str = Field(..., description="Unique slug identifier for the namespace")
    name: str = Field(..., description="Human-readable name")
    description: str | None = Field(default=None, description="Namespace description")
    tenant_id: str | None = Field(default=None, description="Optional tenant ID")
    is_public: bool = Field(default=False, description="Whether publicly accessible")

    class Config:
        json_schema_extra = {
            "example": {
                "slug": "finance-terms",
                "name": "Finance Terms",
                "description": "Financial terminology and definitions",
                "is_public": True,
            }
        }


class UpdateNamespaceRequest(BaseModel):
    """Request to update a namespace."""

    name: str | None = Field(default=None, description="New name (null to keep current)")
    description: str | None = Field(default=None, description="New description (null to keep current)")
    is_public: bool | None = Field(default=None, description="New public flag (null to keep current)")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Updated Finance Terms",
                "description": "Updated financial terminology",
            }
        }


class CreateTermRequest(BaseModel):
    """Request to create a new term."""

    slug: str = Field(..., description="Unique term slug within the namespace")
    label: str = Field(..., description="Human-readable term label")
    definition: str | None = Field(default=None, description="Term definition")
    aliases: list[str] = Field(default_factory=list, description="Alternative names")
    examples: list[str] = Field(default_factory=list, description="Usage examples")
    context_hint: str | None = Field(default=None, description="Context hint for disambiguation")

    class Config:
        json_schema_extra = {
            "example": {
                "slug": "roi",
                "label": "ROI",
                "definition": "Return on Investment - a measure of profitability",
                "aliases": ["return-on-investment"],
                "examples": ["The project achieved 150% ROI"],
            }
        }


class UpdateTermRequest(BaseModel):
    """Request to update a term."""

    label: str | None = Field(default=None, description="New label")
    definition: str | None = Field(default=None, description="New definition")
    aliases: list[str] | None = Field(default=None, description="New aliases")
    examples: list[str] | None = Field(default=None, description="New examples")
    context_hint: str | None = Field(default=None, description="New context hint")

    class Config:
        json_schema_extra = {
            "example": {
                "definition": "Updated definition for the term",
            }
        }


# ============================================================================
# CONTROLLER
# ============================================================================


class NamespacesController(ControllerBase):
    """Controller for knowledge namespace and term operations."""

    # =========================================================================
    # Namespace CRUD
    # =========================================================================

    @post("/", status_code=201, response_model=KnowledgeNamespaceDto)
    async def create_namespace(
        self,
        request: CreateNamespaceRequest,
        mediator: Mediator = Depends(get_mediator),
        user: dict[str, Any] = Depends(require_roles("admin")),
    ):
        """Create a new knowledge namespace.

        Requires admin role.

        Args:
            request: Create namespace request body
            mediator: Command mediator
            user: Current user info (must have admin role)

        Returns:
            Created namespace DTO
        """
        # Map is_public to access_level
        access_level = "public" if request.is_public else ("tenant" if request.tenant_id else "private")

        command = CreateNamespaceCommand(
            namespace_id=request.slug,
            name=request.name,
            description=request.description or "",
            access_level=access_level,
            user_info=user,
        )

        result = await mediator.execute_async(command)
        return self.process(result)

    @get("/", response_model=list[KnowledgeNamespaceDto])
    async def get_namespaces(
        self,
        tenant_id: str | None = Query(None, description="Filter by tenant"),
        include_public: bool = Query(True, description="Include public namespaces"),
        limit: int = Query(100, ge=1, le=500, description="Maximum results"),
        offset: int = Query(0, ge=0, description="Results offset"),
        mediator: Mediator = Depends(get_mediator),
        user: dict[str, Any] = Depends(get_current_user),
    ):
        """List knowledge namespaces.

        Args:
            tenant_id: Optional tenant filter
            include_public: Whether to include public namespaces
            limit: Maximum number of results
            offset: Number of results to skip
            mediator: Query mediator
            user: Current user info

        Returns:
            List of namespace DTOs
        """
        query = GetNamespacesQuery(
            tenant_id=tenant_id,
            include_public=include_public,
            limit=limit,
            offset=offset,
            user_info=user,
        )

        result = await mediator.execute_async(query)
        return self.process(result)

    @get("/{namespace_id}", response_model=KnowledgeNamespaceDto)
    async def get_namespace(
        self,
        namespace_id: str,
        mediator: Mediator = Depends(get_mediator),
        user: dict[str, Any] = Depends(get_current_user),
    ):
        """Get a knowledge namespace by ID.

        Args:
            namespace_id: The namespace ID
            mediator: Query mediator
            user: Current user info

        Returns:
            Namespace DTO
        """
        query = GetNamespaceQuery(
            namespace_id=namespace_id,
            user_info=user,
        )

        result = await mediator.execute_async(query)
        return self.process(result)

    @put("/{namespace_id}", response_model=KnowledgeNamespaceDto)
    async def update_namespace(
        self,
        namespace_id: str,
        request: UpdateNamespaceRequest,
        mediator: Mediator = Depends(get_mediator),
        user: dict[str, Any] = Depends(require_roles("admin")),
    ):
        """Update a knowledge namespace.

        Requires admin role.

        Args:
            namespace_id: The namespace ID
            request: Update namespace request body
            mediator: Command mediator
            user: Current user info (must have admin role)

        Returns:
            Updated namespace DTO
        """
        command = UpdateNamespaceCommand(
            namespace_id=namespace_id,
            name=request.name,
            description=request.description,
            is_public=request.is_public,
            user_info=user,
        )

        result = await mediator.execute_async(command)
        return self.process(result)

    @delete("/{namespace_id}", status_code=204)
    async def delete_namespace(
        self,
        namespace_id: str,
        mediator: Mediator = Depends(get_mediator),
        user: dict[str, Any] = Depends(require_roles("admin")),
    ):
        """Delete a knowledge namespace (soft delete).

        Requires admin role.

        Args:
            namespace_id: The namespace ID
            mediator: Command mediator
            user: Current user info (must have admin role)
        """
        command = DeleteNamespaceCommand(
            namespace_id=namespace_id,
            user_info=user,
        )

        result = await mediator.execute_async(command)
        return self.process(result)

    # =========================================================================
    # Term CRUD
    # =========================================================================

    @post("/{namespace_id}/terms", status_code=201, response_model=KnowledgeTermDto)
    async def add_term(
        self,
        namespace_id: str,
        request: CreateTermRequest,
        mediator: Mediator = Depends(get_mediator),
        user: dict[str, Any] = Depends(require_roles("admin")),
    ):
        """Add a term to a namespace.

        Requires admin role.

        Args:
            namespace_id: The namespace ID
            request: Create term request body
            mediator: Command mediator
            user: Current user info (must have admin role)

        Returns:
            Created term DTO
        """
        command = AddTermCommand(
            namespace_id=namespace_id,
            term=request.slug,
            definition=request.definition or "",
            aliases=request.aliases or [],
            examples=request.examples or [],
            context_hint=request.context_hint,
            user_info=user,
        )

        result = await mediator.execute_async(command)
        return self.process(result)

    @get("/{namespace_id}/terms", response_model=list[KnowledgeTermDto])
    async def get_terms(
        self,
        namespace_id: str,
        search: str | None = Query(None, description="Search filter"),
        limit: int = Query(100, ge=1, le=500, description="Maximum results"),
        offset: int = Query(0, ge=0, description="Results offset"),
        mediator: Mediator = Depends(get_mediator),
        user: dict[str, Any] = Depends(get_current_user),
    ):
        """List terms in a namespace.

        Args:
            namespace_id: The namespace ID
            search: Optional search filter
            limit: Maximum number of results
            offset: Number of results to skip
            mediator: Query mediator
            user: Current user info

        Returns:
            List of term DTOs
        """
        query = GetTermsQuery(
            namespace_id=namespace_id,
            search=search,
            limit=limit,
            offset=offset,
            user_info=user,
        )

        result = await mediator.execute_async(query)
        return self.process(result)

    @get("/{namespace_id}/terms/{term_id}", response_model=KnowledgeTermDto)
    async def get_term(
        self,
        namespace_id: str,
        term_id: str,
        mediator: Mediator = Depends(get_mediator),
        user: dict[str, Any] = Depends(get_current_user),
    ):
        """Get a term by ID.

        Args:
            namespace_id: The namespace ID
            term_id: The term ID
            mediator: Query mediator
            user: Current user info

        Returns:
            Term DTO
        """
        query = GetTermQuery(
            namespace_id=namespace_id,
            term_id=term_id,
            user_info=user,
        )

        result = await mediator.execute_async(query)
        return self.process(result)

    @put("/{namespace_id}/terms/{term_id}", response_model=KnowledgeTermDto)
    async def update_term(
        self,
        namespace_id: str,
        term_id: str,
        request: UpdateTermRequest,
        mediator: Mediator = Depends(get_mediator),
        user: dict[str, Any] = Depends(require_roles("admin")),
    ):
        """Update a term.

        Requires admin role.

        Args:
            namespace_id: The namespace ID
            term_id: The term ID
            request: Update term request body
            mediator: Command mediator
            user: Current user info (must have admin role)

        Returns:
            Updated term DTO
        """
        command = UpdateTermCommand(
            namespace_id=namespace_id,
            term_id=term_id,
            term=request.label,
            definition=request.definition,
            aliases=request.aliases,
            examples=request.examples,
            context_hint=request.context_hint,
            user_info=user,
        )

        result = await mediator.execute_async(command)
        return self.process(result)

    @delete("/{namespace_id}/terms/{term_id}", status_code=204)
    async def remove_term(
        self,
        namespace_id: str,
        term_id: str,
        mediator: Mediator = Depends(get_mediator),
        user: dict[str, Any] = Depends(require_roles("admin")),
    ):
        """Remove a term from a namespace (soft delete).

        Requires admin role.

        Args:
            namespace_id: The namespace ID
            term_id: The term ID
            mediator: Command mediator
            user: Current user info (must have admin role)
        """
        command = RemoveTermCommand(
            namespace_id=namespace_id,
            term_id=term_id,
            user_info=user,
        )

        result = await mediator.execute_async(command)
        return self.process(result)


# Import dependencies for use in route decorators
