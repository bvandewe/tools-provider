"""Get namespace query with handler.

Uses the aggregate repository directly (same as agent-host pattern).
"""

import logging
from dataclasses import dataclass
from typing import Any

from neuroglia.core import OperationResult
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.mediation import Query, QueryHandler

from domain.entities import KnowledgeNamespace
from integration.models import KnowledgeNamespaceDto

from .get_namespaces_query import _map_namespace_to_dto

log = logging.getLogger(__name__)


@dataclass
class GetNamespaceQuery(Query[OperationResult[KnowledgeNamespaceDto]]):
    """Query to get a namespace by ID."""

    namespace_id: str
    """The namespace to retrieve."""

    # Context
    user_info: dict[str, Any] | None = None
    """User information from authentication context."""


class GetNamespaceQueryHandler(QueryHandler[GetNamespaceQuery, OperationResult[KnowledgeNamespaceDto]]):
    """Handler for GetNamespaceQuery.

    Uses the aggregate repository directly and maps to DTO inline.
    """

    def __init__(
        self,
        repository: Repository[KnowledgeNamespace, str],
    ):
        self._repository = repository

    async def handle_async(self, query: GetNamespaceQuery) -> OperationResult[KnowledgeNamespaceDto]:
        """Handle the get namespace query.

        Args:
            query: The query to handle

        Returns:
            OperationResult containing the namespace DTO or error
        """
        log.debug(f"Getting namespace: {query.namespace_id}")

        namespace = await self._repository.get_async(query.namespace_id)
        if namespace is None:
            return self.not_found(KnowledgeNamespaceDto, query.namespace_id)

        dto = _map_namespace_to_dto(namespace)
        return self.ok(dto)
