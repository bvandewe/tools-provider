"""Get namespaces query with handler.

Uses the aggregate repository directly (same as agent-host pattern).
Aggregates are mapped to DTOs inline for simplicity.
"""

import logging
from dataclasses import dataclass
from typing import Any

from neuroglia.core import OperationResult
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.mediation import Query, QueryHandler

from domain.entities import KnowledgeNamespace
from domain.enums import AccessLevel
from integration.models import KnowledgeNamespaceDto

log = logging.getLogger(__name__)


def _map_namespace_to_dto(namespace: KnowledgeNamespace) -> KnowledgeNamespaceDto:
    """Map a KnowledgeNamespace aggregate to its DTO representation.

    Args:
        namespace: The aggregate to map

    Returns:
        The mapped DTO
    """
    state = namespace.state
    access_level = state.access_level if isinstance(state.access_level, AccessLevel) else AccessLevel(state.access_level)

    return KnowledgeNamespaceDto(
        id=state.id,
        name=state.name,
        description=state.description,
        tenant_id=state.owner_tenant_id,
        owner_id=state.owner_user_id,
        access_level=access_level,
        is_public=access_level == AccessLevel.PUBLIC,
        term_count=state.term_count,
        relationship_count=state.relationship_count,
        rule_count=state.rule_count,
        revision_count=len(state.revisions),
        current_revision=state.current_revision,
        created_at=state.created_at,
        updated_at=state.updated_at,
        is_deleted=getattr(state, "is_deleted", False),
    )


@dataclass
class GetNamespacesQuery(Query[OperationResult[list[KnowledgeNamespaceDto]]]):
    """Query to get all namespaces with pagination."""

    tenant_id: str | None = None
    """Filter by tenant (None = all accessible)."""

    include_public: bool = True
    """Whether to include public namespaces."""

    limit: int = 100
    """Maximum number of results."""

    offset: int = 0
    """Number of results to skip."""

    # Context
    user_info: dict[str, Any] | None = None
    """User information from authentication context."""


class GetNamespacesQueryHandler(QueryHandler[GetNamespacesQuery, OperationResult[list[KnowledgeNamespaceDto]]]):
    """Handler for GetNamespacesQuery.

    Uses the aggregate repository directly and maps to DTOs inline,
    following the same pattern as agent-host for simplicity.
    """

    def __init__(
        self,
        repository: Repository[KnowledgeNamespace, str],
    ):
        self._repository = repository

    async def handle_async(self, query: GetNamespacesQuery) -> OperationResult[list[KnowledgeNamespaceDto]]:
        """Handle the get namespaces query.

        Args:
            query: The query to handle

        Returns:
            OperationResult containing list of namespace DTOs
        """
        log.debug(f"Getting namespaces (tenant={query.tenant_id}, limit={query.limit})")

        # Get aggregates from repository
        if query.tenant_id:
            namespaces = await self._repository.get_by_tenant_async(query.tenant_id)
            if query.include_public:
                public_namespaces = await self._repository.get_public_async()
                # Combine and deduplicate by ID
                seen_ids = {ns.id() for ns in namespaces}
                for ns in public_namespaces:
                    if ns.id() not in seen_ids:
                        namespaces.append(ns)
        else:
            namespaces = await self._repository.get_all_async()

        # Apply pagination manually (repository doesn't support it directly)
        paginated = namespaces[query.offset : query.offset + query.limit]

        # Map aggregates to DTOs
        dtos = [_map_namespace_to_dto(ns) for ns in paginated]

        return self.ok(dtos)
