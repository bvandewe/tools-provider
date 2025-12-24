"""Get term query with handler.

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
class GetTermQuery(Query[OperationResult[KnowledgeTermDto]]):
    """Query to get a term by ID."""

    namespace_id: str
    """The namespace containing the term."""

    term_id: str
    """The term to retrieve."""

    # Context
    user_info: dict[str, Any] | None = None
    """User information from authentication context."""


class GetTermQueryHandler(QueryHandler[GetTermQuery, OperationResult[KnowledgeTermDto]]):
    """Handler for GetTermQuery."""

    def __init__(
        self,
        repository: Repository[KnowledgeNamespace, str],
    ):
        self._repository = repository

    async def handle_async(self, query: GetTermQuery) -> OperationResult[KnowledgeTermDto]:
        """Handle the get term query.

        Args:
            query: The query to handle

        Returns:
            OperationResult containing the term DTO or error
        """
        log.debug(f"Getting term: {query.term_id} from namespace: {query.namespace_id}")

        # Load the namespace
        namespace = await self._repository.get_async(query.namespace_id)
        if namespace is None:
            return self.not_found(KnowledgeNamespace, query.namespace_id)

        # Get the term
        term = namespace.get_term(query.term_id)
        if term is None:
            return self.not_found("Term", query.term_id)

        # Map to DTO
        dto = KnowledgeTermDto(
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

        return self.ok(dto)
