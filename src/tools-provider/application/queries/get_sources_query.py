"""Get sources query with handler.

Retrieves upstream sources from the read model with optional filtering.
"""

from dataclasses import dataclass
from typing import Any

from neuroglia.core import OperationResult
from neuroglia.mediation import Query, QueryHandler

from domain.enums import HealthStatus, SourceType
from domain.repositories import SourceDtoRepository
from integration.models.source_dto import SourceDto


@dataclass
class GetSourcesQuery(Query[OperationResult[list[SourceDto]]]):
    """Query to retrieve upstream sources with optional filtering.

    Supports filtering by:
    - is_enabled: Only enabled/disabled sources
    - health_status: Only sources with specific health status
    - source_type: Only OpenAPI or Workflow sources
    """

    include_disabled: bool = False
    """Whether to include disabled sources. Default is enabled only."""

    health_status: str | None = None
    """Filter by health status: 'healthy', 'degraded', 'unhealthy', 'unknown'."""

    source_type: str | None = None
    """Filter by source type: 'openapi' or 'workflow'."""

    user_info: dict[str, Any] | None = None
    """User information from authentication context."""


class GetSourcesQueryHandler(QueryHandler[GetSourcesQuery, OperationResult[list[SourceDto]]]):
    """Handler for retrieving upstream sources from the read model.

    Uses SourceDtoRepository (MongoDB) for efficient querying.
    """

    def __init__(self, source_repository: SourceDtoRepository):
        super().__init__()
        self.source_repository = source_repository

    async def handle_async(self, request: GetSourcesQuery) -> OperationResult[list[SourceDto]]:
        """Handle get sources query with filtering."""
        query = request

        # Start with base query based on enabled filter
        if query.include_disabled:
            sources = await self.source_repository.get_all_async()
        else:
            sources = await self.source_repository.get_enabled_async()

        # Apply additional filters
        if query.health_status:
            try:
                status = HealthStatus(query.health_status.lower())
                sources = [s for s in sources if s.health_status == status]
            except ValueError:
                pass  # Ignore invalid health status

        if query.source_type:
            try:
                src_type = SourceType(query.source_type.lower())
                sources = [s for s in sources if s.source_type == src_type]
            except ValueError:
                pass  # Ignore invalid source type

        return self.ok(sources)


@dataclass
class GetSourceByIdQuery(Query[OperationResult[SourceDto]]):
    """Query to retrieve a single upstream source by ID."""

    source_id: str
    """ID of the source to retrieve."""

    user_info: dict[str, Any] | None = None
    """User information from authentication context."""


class GetSourceByIdQueryHandler(QueryHandler[GetSourceByIdQuery, OperationResult[SourceDto]]):
    """Handler for retrieving a single source by ID."""

    def __init__(self, source_repository: SourceDtoRepository):
        super().__init__()
        self.source_repository = source_repository

    async def handle_async(self, request: GetSourceByIdQuery) -> OperationResult[SourceDto]:
        """Handle get source by ID query."""
        source = await self.source_repository.get_async(request.source_id)

        if not source:
            return self.not_found(SourceDto, request.source_id)

        return self.ok(source)
