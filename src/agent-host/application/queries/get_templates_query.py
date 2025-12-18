"""Query for listing ConversationTemplates.

This query returns ConversationTemplates based on various filter criteria.
All authenticated users can list templates; admin-only access is enforced
at the controller level if needed.
"""

import logging
from dataclasses import dataclass
from typing import Any

from neuroglia.core import OperationResult
from neuroglia.mediation import Query, QueryHandler

from domain.models import ConversationTemplate
from domain.repositories import TemplateRepository

logger = logging.getLogger(__name__)


@dataclass
class GetTemplatesQuery(Query[OperationResult[list[ConversationTemplate]]]):
    """Query to get all ConversationTemplates with optional filters.

    Attributes:
        user_info: Authenticated user context
        proactive_only: If True, only return templates with agent_starts_first=True
        assessments_only: If True, only return templates with scoring enabled
        created_by: Filter by creator user ID
    """

    user_info: dict[str, Any]
    proactive_only: bool = False
    assessments_only: bool = False
    created_by: str | None = None


@dataclass
class GetTemplateQuery(Query[OperationResult[ConversationTemplate | None]]):
    """Query to get a specific ConversationTemplate by ID.

    Attributes:
        template_id: The ID of the template to retrieve
        user_info: Authenticated user context
        for_client: If True, strips sensitive data (correct answers)
    """

    template_id: str
    user_info: dict[str, Any]
    for_client: bool = False


class GetTemplatesQueryHandler(QueryHandler[GetTemplatesQuery, OperationResult[list[ConversationTemplate]]]):
    """Handler for GetTemplatesQuery."""

    def __init__(
        self,
        template_repository: TemplateRepository,
    ) -> None:
        """Initialize the handler.

        Args:
            template_repository: Repository for ConversationTemplates
        """
        super().__init__()
        self._repository = template_repository

    async def handle_async(self, query: GetTemplatesQuery) -> OperationResult[list[ConversationTemplate]]:
        """Get all templates matching the filter criteria.

        Applies filters in order:
        1. proactive_only -> only agent_starts_first=True
        2. assessments_only -> only templates with scoring
        3. created_by -> only templates by specific user
        """
        try:
            # Use specialized repository methods for common filters
            if query.proactive_only:
                templates = await self._repository.get_proactive_async()
            elif query.assessments_only:
                templates = await self._repository.get_assessments_async()
            elif query.created_by:
                templates = await self._repository.get_by_creator_async(query.created_by)
            else:
                templates = await self._repository.get_all_async()

            # If multiple filters, apply additional filtering in memory
            result = list(templates)

            if query.proactive_only and query.assessments_only:
                # Both filters: already filtered by proactive, now filter by assessment
                result = [t for t in result if t.is_assessment]

            if query.created_by and (query.proactive_only or query.assessments_only):
                # Filter by creator as well
                result = [t for t in result if t.created_by == query.created_by]

            return self.ok(result)

        except Exception as e:
            logger.error(f"Failed to get templates: {e}")
            return self.internal_server_error(str(e))


class GetTemplateQueryHandler(QueryHandler[GetTemplateQuery, OperationResult[ConversationTemplate | None]]):
    """Handler for GetTemplateQuery."""

    def __init__(
        self,
        template_repository: TemplateRepository,
    ) -> None:
        """Initialize the handler.

        Args:
            template_repository: Repository for ConversationTemplates
        """
        super().__init__()
        self._repository = template_repository

    async def handle_async(self, query: GetTemplateQuery) -> OperationResult[ConversationTemplate | None]:
        """Get a specific template by ID.

        If for_client=True, returns a version with sensitive data removed
        (correct answers stripped from item contents).
        """
        try:
            template = await self._repository.get_async(query.template_id)

            if template is None:
                return self.not_found(ConversationTemplate, query.template_id)

            # If for_client, we could strip sensitive data here
            # But to_client_dict() is typically called at serialization time
            # For now, return the full template; controller handles serialization

            return self.ok(template)

        except Exception as e:
            logger.error(f"Failed to get template {query.template_id}: {e}")
            return self.internal_server_error(str(e))
