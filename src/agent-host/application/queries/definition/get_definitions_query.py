"""Query for listing accessible AgentDefinitions.

This query returns all AgentDefinitions that a user has access to,
based on public visibility, user ownership, and role/scope requirements.
"""

import logging
from dataclasses import dataclass
from typing import Any

from neuroglia.core import OperationResult
from neuroglia.mediation import Query, QueryHandler

from domain.entities import AgentDefinition
from domain.repositories import AgentDefinitionRepository
from integration.models.definition_dto import AgentDefinitionDto

logger = logging.getLogger(__name__)


@dataclass
class GetDefinitionsQuery(Query[OperationResult[list[AgentDefinitionDto]]]):
    """Query to get all accessible AgentDefinitions for a user."""

    user_info: dict[str, Any]
    include_system: bool = True  # Include system-owned definitions


@dataclass
class GetDefinitionQuery(Query[OperationResult[AgentDefinitionDto | None]]):
    """Query to get a specific AgentDefinition by ID."""

    definition_id: str
    user_info: dict[str, Any]


class GetDefinitionsQueryHandler(QueryHandler[GetDefinitionsQuery, OperationResult[list[AgentDefinitionDto]]]):
    """Handler for GetDefinitionsQuery."""

    def __init__(
        self,
        definition_repository: AgentDefinitionRepository,
    ) -> None:
        """Initialize the handler.

        Args:
            definition_repository: Repository for AgentDefinitions
        """
        super().__init__()
        self._repository = definition_repository

    async def handle_async(self, query: GetDefinitionsQuery) -> OperationResult[list[AgentDefinitionDto]]:
        """Get all accessible definitions for the user.

        Access rules:
        1. Public definitions (is_public=True)
        2. User-owned definitions (owner_user_id matches)
        3. System definitions if include_system=True
        4. Role-restricted definitions where user has required_roles
        5. User explicitly in allowed_users list
        """
        user_id = query.user_info.get("sub", "unknown")
        user_roles = query.user_info.get("realm_access", {}).get("roles", [])

        try:
            # Get all definitions from repository
            all_definitions = await self._repository.get_all_async()

            accessible = []
            for defn in all_definitions:
                state = defn.state
                # System definitions (no owner)
                if state.owner_user_id is None:
                    if query.include_system:
                        accessible.append(defn)
                    continue

                # User owns the definition
                if state.owner_user_id == user_id:
                    accessible.append(defn)
                    continue

                # Check if public
                if state.is_public:
                    accessible.append(defn)
                    continue

                # Check role requirements
                if state.required_roles:
                    if any(role in user_roles for role in state.required_roles):
                        accessible.append(defn)
                        continue

                # Check explicit user access
                if state.allowed_users and user_id in state.allowed_users:
                    accessible.append(defn)
                    continue

            # Map aggregates to DTOs
            dtos = [_map_definition_to_dto(d) for d in accessible]
            return self.ok(dtos)

        except Exception as e:
            logger.error(f"Failed to get definitions: {e}")
            return self.internal_server_error(str(e))


class GetDefinitionQueryHandler(QueryHandler[GetDefinitionQuery, OperationResult[AgentDefinitionDto | None]]):
    """Handler for GetDefinitionQuery."""

    def __init__(
        self,
        definition_repository: AgentDefinitionRepository,
    ) -> None:
        """Initialize the handler.

        Args:
            definition_repository: Repository for AgentDefinitions
        """
        super().__init__()
        self._repository = definition_repository

    async def handle_async(self, query: GetDefinitionQuery) -> OperationResult[AgentDefinitionDto | None]:
        """Get a specific definition by ID.

        Returns the definition only if the user has access to it.
        """
        user_id = query.user_info.get("sub", "unknown")
        user_roles = query.user_info.get("realm_access", {}).get("roles", [])

        try:
            defn = await self._repository.get_async(query.definition_id)

            if defn is None:
                return self.not_found(AgentDefinition, query.definition_id)

            state = defn.state
            # Check access
            has_access = False

            # System definitions are accessible to all
            if state.owner_user_id is None:
                has_access = True

            # User owns the definition
            elif state.owner_user_id == user_id:
                has_access = True

            # Public definitions
            elif state.is_public:
                has_access = True

            # Role-based access
            elif state.required_roles and any(role in user_roles for role in state.required_roles):
                has_access = True

            # Explicit user access
            elif state.allowed_users and user_id in state.allowed_users:
                has_access = True

            if not has_access:
                return self.forbidden("Access denied to this definition")

            # Map aggregate to DTO
            dto = _map_definition_to_dto(defn)
            return self.ok(dto)

        except Exception as e:
            logger.error(f"Failed to get definition {query.definition_id}: {e}")
            return self.internal_server_error(str(e))


# =============================================================================
# ADMIN QUERIES (no access filtering)
# =============================================================================


@dataclass
class GetAllDefinitionsQuery(Query[OperationResult[list[AgentDefinitionDto]]]):
    """Admin query to get ALL AgentDefinitions without access filtering.

    This query is for admin users only and returns all definitions
    in the system regardless of ownership or visibility settings.
    """

    # Optional filters
    include_system: bool = True  # Include system-owned definitions (owner_user_id is None)
    owner_user_id: str | None = None  # Filter by specific owner


class GetAllDefinitionsQueryHandler(QueryHandler[GetAllDefinitionsQuery, OperationResult[list[AgentDefinitionDto]]]):
    """Handler for GetAllDefinitionsQuery (Admin)."""

    def __init__(
        self,
        definition_repository: AgentDefinitionRepository,
    ) -> None:
        """Initialize the handler.

        Args:
            definition_repository: Repository for AgentDefinitions
        """
        super().__init__()
        self._repository = definition_repository

    async def handle_async(self, query: GetAllDefinitionsQuery) -> OperationResult[list[AgentDefinitionDto]]:
        """Get all definitions without access filtering.

        This is an admin-only query that returns all definitions.
        Authorization is enforced at the controller level.
        """
        try:
            # Get all definitions from repository
            all_definitions = await self._repository.get_all_async()

            # Apply optional filters
            results = []
            for defn in all_definitions:
                state = defn.state
                # Filter by system ownership if requested
                if not query.include_system and state.owner_user_id is None:
                    continue

                # Filter by specific owner if provided
                if query.owner_user_id and state.owner_user_id != query.owner_user_id:
                    continue

                results.append(defn)

            # Sort by name for consistent ordering
            results.sort(key=lambda d: d.state.name.lower())

            # Map aggregates to DTOs
            dtos = [_map_definition_to_dto(d) for d in results]
            return self.ok(dtos)

        except Exception as e:
            logger.error(f"Failed to get all definitions: {e}")
            return self.internal_server_error(str(e))


def _map_definition_to_dto(defn: AgentDefinition) -> AgentDefinitionDto:
    """Map AgentDefinition aggregate to DTO."""
    state = defn.state
    return AgentDefinitionDto(
        id=defn.id(),
        owner_user_id=state.owner_user_id,
        name=state.name,
        description=state.description,
        icon=state.icon,
        system_prompt=state.system_prompt,
        tools=state.tools or [],
        model=state.model,
        allow_model_selection=getattr(state, "allow_model_selection", True),
        conversation_template_id=state.conversation_template_id,
        is_public=state.is_public,
        required_roles=state.required_roles or [],
        required_scopes=state.required_scopes or [],
        allowed_users=state.allowed_users,
        created_by=state.created_by,
        created_at=state.created_at,
        updated_at=state.updated_at,
        version=getattr(state, "version", 1),
    )
