"""Get terms query with handler.

Uses the aggregate repository directly.
"""

import logging
from dataclasses import dataclass
from typing import Any

from neuroglia.core import OperationResult
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.mediation import Query, QueryHandler

from domain.entities import KnowledgeNamespace
from integration.models import KnowledgeTermDto

log = logging.getLogger(__name__)


@dataclass
class GetTermsQuery(Query[OperationResult[list[KnowledgeTermDto]]]):
    """Query to get all terms in a namespace."""

    namespace_id: str
    """The namespace to get terms from."""

    search: str | None = None
    """Optional search filter."""

    limit: int = 100
    """Maximum number of results."""

    offset: int = 0
    """Number of results to skip."""

    # Context
    user_info: dict[str, Any] | None = None
    """User information from authentication context."""


class GetTermsQueryHandler(QueryHandler[GetTermsQuery, OperationResult[list[KnowledgeTermDto]]]):
    """Handler for GetTermsQuery."""

    def __init__(
        self,
        repository: Repository[KnowledgeNamespace, str],
    ):
        self._repository = repository

    async def handle_async(self, query: GetTermsQuery) -> OperationResult[list[KnowledgeTermDto]]:
        """Handle the get terms query.

        Args:
            query: The query to handle

        Returns:
            OperationResult containing list of term DTOs
        """
        log.debug(f"Getting terms from namespace: {query.namespace_id}")

        # Load the namespace
        namespace = await self._repository.get_async(query.namespace_id)
        if namespace is None:
            return self.not_found(KnowledgeNamespace, query.namespace_id)

        # Get active terms
        terms = namespace.get_active_terms()

        # Apply search filter if provided
        if query.search:
            search_lower = query.search.lower()
            terms = [t for t in terms if t.matches(search_lower)]

        # Apply pagination
        paginated_terms = terms[query.offset : query.offset + query.limit]

        # Map to DTOs
        dtos = [
            KnowledgeTermDto(
                id=term.id,
                namespace_id=query.namespace_id,
                term=term.term,
                definition=term.definition,
                aliases=list(term.aliases),
                examples=list(term.examples),
                context_hint=term.context_hint,
                created_at=term.created_at,
                updated_at=term.updated_at,
                is_active=term.is_active,
            )
            for term in paginated_terms
        ]

        return self.ok(dtos)
