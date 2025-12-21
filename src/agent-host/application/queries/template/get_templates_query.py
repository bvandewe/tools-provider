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

from domain.entities import ConversationTemplate
from domain.repositories import ConversationTemplateRepository
from integration.models.template_dto import ConversationItemDto, ConversationTemplateDto, ItemContentDto

logger = logging.getLogger(__name__)


@dataclass
class GetTemplatesQuery(Query[OperationResult[list[ConversationTemplateDto]]]):
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
class GetTemplateQuery(Query[OperationResult[ConversationTemplateDto | None]]):
    """Query to get a specific ConversationTemplate by ID.

    Attributes:
        template_id: The ID of the template to retrieve
        user_info: Authenticated user context
        for_client: If True, strips sensitive data (correct answers)
    """

    template_id: str
    user_info: dict[str, Any]
    for_client: bool = False


@dataclass
class GetTemplateItemQuery(Query[OperationResult[ConversationItemDto | None]]):
    """Query to get a specific item from a ConversationTemplate.

    Used by the orchestrator to efficiently retrieve the current item
    during proactive conversation flow without loading the entire template.

    Attributes:
        template_id: The ID of the template
        item_index: The 0-based index of the item to retrieve
        user_info: Authenticated user context
        for_client: If True, strips sensitive data (correct answers)
    """

    template_id: str
    item_index: int
    user_info: dict[str, Any]
    for_client: bool = False


class GetTemplatesQueryHandler(QueryHandler[GetTemplatesQuery, OperationResult[list[ConversationTemplateDto]]]):
    """Handler for GetTemplatesQuery."""

    def __init__(
        self,
        template_repository: ConversationTemplateRepository,
    ) -> None:
        """Initialize the handler.

        Args:
            template_repository: Repository for ConversationTemplates
        """
        super().__init__()
        self._repository = template_repository

    async def handle_async(self, query: GetTemplatesQuery) -> OperationResult[list[ConversationTemplateDto]]:
        """Get all templates matching the filter criteria.

        Applies filters in order:
        1. proactive_only -> only agent_starts_first=True
        2. assessments_only -> only templates with scoring
        3. created_by -> only templates by specific user
        """
        try:
            # Get all templates and filter in memory
            templates = await self._repository.get_all_async()
            result = list(templates)

            # Apply filters
            if query.proactive_only:
                result = [t for t in result if t.state.agent_starts_first]

            if query.assessments_only:
                # is_assessment is a property on aggregate (passing_score_percent is not None)
                result = [t for t in result if t.state.passing_score_percent is not None]

            if query.created_by:
                result = [t for t in result if t.state.created_by == query.created_by]

            # Map aggregates to DTOs
            dtos = [_map_template_to_dto(t) for t in result]
            return self.ok(dtos)

        except Exception as e:
            logger.error(f"Failed to get templates: {e}")
            return self.internal_server_error(str(e))


class GetTemplateQueryHandler(QueryHandler[GetTemplateQuery, OperationResult[ConversationTemplateDto | None]]):
    """Handler for GetTemplateQuery."""

    def __init__(
        self,
        template_repository: ConversationTemplateRepository,
    ) -> None:
        """Initialize the handler.

        Args:
            template_repository: Repository for ConversationTemplates
        """
        super().__init__()
        self._repository = template_repository

    async def handle_async(self, query: GetTemplateQuery) -> OperationResult[ConversationTemplateDto | None]:
        """Get a specific template by ID.

        If for_client=True, returns a version with sensitive data removed
        (correct answers stripped from item contents).
        """
        try:
            template = await self._repository.get_async(query.template_id)

            if template is None:
                return self.not_found(ConversationTemplate, query.template_id)

            # Map aggregate to DTO
            dto = _map_template_to_dto(template)

            # If for_client, strip sensitive data (correct answers)
            if query.for_client:
                dto = _strip_sensitive_data(dto)

            return self.ok(dto)

        except Exception as e:
            logger.error(f"Failed to get template {query.template_id}: {e}")
            return self.internal_server_error(str(e))


class GetTemplateItemQueryHandler(QueryHandler[GetTemplateItemQuery, OperationResult[ConversationItemDto | None]]):
    """Handler for GetTemplateItemQuery.

    Retrieves a specific item from a template by index, allowing the orchestrator
    to efficiently process template items one at a time.
    """

    def __init__(
        self,
        template_repository: ConversationTemplateRepository,
    ) -> None:
        """Initialize the handler.

        Args:
            template_repository: Repository for ConversationTemplates
        """
        super().__init__()
        self._repository = template_repository

    async def handle_async(self, query: GetTemplateItemQuery) -> OperationResult[ConversationItemDto | None]:
        """Get a specific item from a template by index.

        Args:
            query: The query containing template_id and item_index

        Returns:
            OperationResult containing the item DTO or None if not found
        """
        try:
            template = await self._repository.get_async(query.template_id)

            if template is None:
                return self.not_found(ConversationTemplate, query.template_id)

            state = template.state
            items = state.items or []

            # Handle shuffle_items configuration
            # Note: For consistency, shuffle should be deterministic per conversation
            # This is handled at the orchestrator level, not here
            # Items are returned in their natural order
            sorted_items = sorted(items, key=lambda i: i.order)

            # Check if item_index is valid
            if query.item_index < 0 or query.item_index >= len(sorted_items):
                logger.warning(f"Item index {query.item_index} out of range for template {query.template_id}")
                return self.ok(None)

            item = sorted_items[query.item_index]

            # Map item to DTO
            item_dto = _map_item_to_dto(item)

            # Strip sensitive data if for_client
            if query.for_client:
                item_dto = _strip_item_sensitive_data(item_dto)

            return self.ok(item_dto)

        except Exception as e:
            logger.error(f"Failed to get item {query.item_index} from template {query.template_id}: {e}")
            return self.internal_server_error(str(e))


def _map_item_to_dto(item) -> ConversationItemDto:
    """Map a ConversationItem to DTO."""
    contents_dto = [
        ItemContentDto(
            id=c.id,
            order=c.order,
            is_templated=c.is_templated,
            source_id=c.source_id,
            widget_type=c.widget_type,
            widget_config=c.widget_config,
            skippable=c.skippable,
            required=c.required,
            show_user_response=c.show_user_response,
            max_score=c.max_score,
            stem=c.stem,
            options=c.options,
            correct_answer=c.correct_answer,
            explanation=c.explanation,
            initial_value=c.initial_value,
        )
        for c in item.contents or []
    ]

    return ConversationItemDto(
        id=item.id,
        order=item.order,
        title=item.title,
        enable_chat_input=item.enable_chat_input,
        show_expiration_warning=item.show_expiration_warning,
        expiration_warning_seconds=item.expiration_warning_seconds,
        warning_message=item.warning_message,
        provide_feedback=item.provide_feedback,
        reveal_correct_answer=item.reveal_correct_answer,
        time_limit_seconds=item.time_limit_seconds,
        instructions=item.instructions,
        require_user_confirmation=item.require_user_confirmation,
        confirmation_button_text=item.confirmation_button_text,
        contents=contents_dto,
    )


def _strip_item_sensitive_data(item_dto: ConversationItemDto) -> ConversationItemDto:
    """Strip sensitive data from a single item DTO."""
    if item_dto.contents:
        for content in item_dto.contents:
            content.correct_answer = None
    return item_dto


def _map_template_to_dto(template: ConversationTemplate) -> ConversationTemplateDto:
    """Map ConversationTemplate aggregate to DTO."""
    state = template.state

    # Map items using the shared helper function
    items_dto = [_map_item_to_dto(item) for item in state.items or []]

    return ConversationTemplateDto(
        id=template.id(),
        name=state.name,
        description=state.description,
        agent_starts_first=state.agent_starts_first,
        allow_agent_switching=state.allow_agent_switching,
        allow_navigation=state.allow_navigation,
        allow_backward_navigation=state.allow_backward_navigation,
        enable_chat_input_initially=state.enable_chat_input_initially,
        continue_after_completion=state.continue_after_completion,
        min_duration_seconds=state.min_duration_seconds,
        max_duration_seconds=state.max_duration_seconds,
        shuffle_items=state.shuffle_items,
        display_progress_indicator=state.display_progress_indicator,
        display_item_score=state.display_item_score,
        display_item_title=state.display_item_title,
        display_final_score_report=state.display_final_score_report,
        include_feedback=state.include_feedback,
        append_items_to_view=state.append_items_to_view,
        introduction_message=state.introduction_message,
        completion_message=state.completion_message,
        passing_score_percent=state.passing_score_percent,
        items=items_dto,
        created_by=state.created_by,
        created_at=state.created_at,
        updated_at=state.updated_at,
        version=state.version,
    )


def _strip_sensitive_data(dto: ConversationTemplateDto) -> ConversationTemplateDto:
    """Strip sensitive data (correct answers) from DTO for client consumption."""
    if dto.items:
        for item in dto.items:
            if item.contents:
                for content in item.contents:
                    content.correct_answer = None
    return dto
