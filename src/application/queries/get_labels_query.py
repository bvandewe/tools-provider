"""Label queries and handlers.

Provides queries for:
- GetLabelsQuery: Get all labels (with optional filtering)
- GetLabelByIdQuery: Get a single label by ID
- GetLabelSummariesQuery: Get lightweight label summaries
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from neuroglia.core import OperationResult
from neuroglia.mediation import Query, QueryHandler
from neuroglia.observability.tracing import add_span_attributes

from domain.repositories.label_dto_repository import LabelDtoRepository
from integration.models.label_dto import LabelDto, LabelSummaryDto

log = logging.getLogger(__name__)


# =============================================================================
# Get All Labels Query
# =============================================================================


@dataclass
class GetLabelsQuery(Query[OperationResult[List[LabelDto]]]):
    """Query to get all labels.

    Optionally filter by:
    - include_deleted: Include soft-deleted labels
    - name_filter: Filter by name (partial match)
    """

    include_deleted: bool = False
    """Include soft-deleted labels in results."""

    name_filter: Optional[str] = None
    """Filter labels by name (case-insensitive partial match)."""

    user_info: Optional[Dict[str, Any]] = None
    """User information from authentication context."""


class GetLabelsQueryHandler(QueryHandler[GetLabelsQuery, OperationResult[List[LabelDto]]]):
    """Handler for GetLabelsQuery."""

    def __init__(self, label_dto_repository: LabelDtoRepository):
        super().__init__()
        self.label_dto_repository = label_dto_repository

    async def handle_async(self, request: GetLabelsQuery) -> OperationResult[List[LabelDto]]:
        """Handle get labels query."""
        query = request

        add_span_attributes(
            {
                "labels.include_deleted": query.include_deleted,
                "labels.has_name_filter": query.name_filter is not None,
            }
        )

        try:
            # Get labels based on filters
            if query.name_filter:
                labels = await self.label_dto_repository.search_by_name_async(query.name_filter)
                if not query.include_deleted:
                    labels = [lbl for lbl in labels if not lbl.is_deleted]
            elif query.include_deleted:
                labels = await self.label_dto_repository.get_all_async()
            else:
                labels = await self.label_dto_repository.get_active_async()

            # Sort by name
            labels.sort(key=lambda x: x.name.lower())

            return self.ok(labels)

        except Exception as e:
            log.exception(f"Error querying labels: {e}")
            return self.internal_server_error(f"Failed to retrieve labels: {str(e)}")


# =============================================================================
# Get Label By ID Query
# =============================================================================


@dataclass
class GetLabelByIdQuery(Query[OperationResult[LabelDto]]):
    """Query to get a single label by ID."""

    label_id: str
    """ID of the label to retrieve."""

    user_info: Optional[Dict[str, Any]] = None
    """User information from authentication context."""


class GetLabelByIdQueryHandler(QueryHandler[GetLabelByIdQuery, OperationResult[LabelDto]]):
    """Handler for GetLabelByIdQuery."""

    def __init__(self, label_dto_repository: LabelDtoRepository):
        super().__init__()
        self.label_dto_repository = label_dto_repository

    async def handle_async(self, request: GetLabelByIdQuery) -> OperationResult[LabelDto]:
        """Handle get label by ID query."""
        query = request

        add_span_attributes({"label.id": query.label_id})

        try:
            # Get from read model
            label = await self.label_dto_repository.get_async(query.label_id)
            if not label:
                return self.not_found(LabelDto, query.label_id)

            if label.is_deleted:
                return self.not_found(LabelDto, query.label_id)

            return self.ok(label)

        except Exception as e:
            log.exception(f"Error retrieving label {query.label_id}: {e}")
            return self.internal_server_error(f"Failed to retrieve label: {str(e)}")


# =============================================================================
# Get Label Summaries Query (lightweight)
# =============================================================================


@dataclass
class GetLabelSummariesQuery(Query[OperationResult[List[LabelSummaryDto]]]):
    """Query to get lightweight label summaries for dropdowns."""

    user_info: Optional[Dict[str, Any]] = None
    """User information from authentication context."""


class GetLabelSummariesQueryHandler(QueryHandler[GetLabelSummariesQuery, OperationResult[List[LabelSummaryDto]]]):
    """Handler for GetLabelSummariesQuery."""

    def __init__(self, label_dto_repository: LabelDtoRepository):
        super().__init__()
        self.label_dto_repository = label_dto_repository

    async def handle_async(self, request: GetLabelSummariesQuery) -> OperationResult[List[LabelSummaryDto]]:
        """Handle get label summaries query."""
        try:
            # Query non-deleted labels from read model
            labels = await self.label_dto_repository.get_active_async()

            # Map to summaries
            summaries = [
                LabelSummaryDto(
                    id=label.id,
                    name=label.name,
                    color=label.color,
                    tool_count=label.tool_count,
                )
                for label in labels
            ]

            # Sort by name
            summaries.sort(key=lambda x: x.name.lower())

            return self.ok(summaries)

        except Exception as e:
            log.exception(f"Error querying label summaries: {e}")
            return self.internal_server_error(f"Failed to retrieve label summaries: {str(e)}")
