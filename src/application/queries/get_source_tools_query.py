"""Get source tools query with handler.

Retrieves tools for a specific source from the read model.
"""

from dataclasses import dataclass
from typing import Any, List, Optional

from neuroglia.core import OperationResult
from neuroglia.mediation import Query, QueryHandler

from domain.repositories import SourceToolDtoRepository
from integration.models.source_tool_dto import SourceToolDto, SourceToolSummaryDto


@dataclass
class GetSourceToolsQuery(Query[OperationResult[List[SourceToolDto]]]):
    """Query to retrieve tools for a specific upstream source.

    Supports filtering by enabled/disabled and active/deprecated status.
    """

    source_id: str
    """ID of the upstream source to get tools for."""

    include_disabled: bool = False
    """Whether to include disabled tools. Default is enabled only."""

    include_deprecated: bool = False
    """Whether to include deprecated tools. Default is active only."""

    user_info: Optional[dict[str, Any]] = None
    """User information from authentication context."""


class GetSourceToolsQueryHandler(QueryHandler[GetSourceToolsQuery, OperationResult[List[SourceToolDto]]]):
    """Handler for retrieving source tools from the read model.

    Uses SourceToolDtoRepository (MongoDB) for efficient querying.
    """

    def __init__(self, tool_repository: SourceToolDtoRepository):
        super().__init__()
        self.tool_repository = tool_repository

    async def handle_async(self, request: GetSourceToolsQuery) -> OperationResult[List[SourceToolDto]]:
        """Handle get source tools query."""
        tools = await self.tool_repository.get_by_source_id_async(
            source_id=request.source_id,
            include_disabled=request.include_disabled,
            include_deprecated=request.include_deprecated,
        )

        return self.ok(tools)


@dataclass
class GetToolByIdQuery(Query[OperationResult[SourceToolDto]]):
    """Query to retrieve a single tool by ID."""

    tool_id: str
    """ID of the tool to retrieve (format: "{source_id}:{operation_id}")."""

    user_info: Optional[dict[str, Any]] = None
    """User information from authentication context."""


class GetToolByIdQueryHandler(QueryHandler[GetToolByIdQuery, OperationResult[SourceToolDto]]):
    """Handler for retrieving a single tool by ID."""

    def __init__(self, tool_repository: SourceToolDtoRepository):
        super().__init__()
        self.tool_repository = tool_repository

    async def handle_async(self, request: GetToolByIdQuery) -> OperationResult[SourceToolDto]:
        """Handle get tool by ID query."""
        tool = await self.tool_repository.get_async(request.tool_id)

        if not tool:
            return self.not_found(SourceToolDto, request.tool_id)

        return self.ok(tool)


@dataclass
class SearchToolsQuery(Query[OperationResult[List[SourceToolDto]]]):
    """Query to search tools by name, description, or tags."""

    query: str
    """Search query string."""

    source_id: Optional[str] = None
    """Optional: filter to specific source."""

    tags: Optional[List[str]] = None
    """Optional: filter by tags (all must match)."""

    include_disabled: bool = False
    """Whether to include disabled tools. Default is enabled only."""

    user_info: Optional[dict[str, Any]] = None
    """User information from authentication context."""


class SearchToolsQueryHandler(QueryHandler[SearchToolsQuery, OperationResult[List[SourceToolDto]]]):
    """Handler for searching tools across sources."""

    def __init__(self, tool_repository: SourceToolDtoRepository):
        super().__init__()
        self.tool_repository = tool_repository

    async def handle_async(self, request: SearchToolsQuery) -> OperationResult[List[SourceToolDto]]:
        """Handle search tools query."""
        tools = await self.tool_repository.search_async(
            query=request.query,
            source_id=request.source_id,
            tags=request.tags,
            include_disabled=request.include_disabled,
        )

        return self.ok(tools)


@dataclass
class GetToolSummariesQuery(Query[OperationResult[List[SourceToolSummaryDto]]]):
    """Query to retrieve lightweight tool summaries for listing.

    Returns SourceToolSummaryDto which excludes the full definition
    for faster queries and smaller payloads.
    """

    source_id: Optional[str] = None
    """Optional: filter to specific source."""

    include_disabled: bool = False
    """Whether to include disabled tools. Default is enabled only."""

    user_info: Optional[dict[str, Any]] = None
    """User information from authentication context."""


class GetToolSummariesQueryHandler(QueryHandler[GetToolSummariesQuery, OperationResult[List[SourceToolSummaryDto]]]):
    """Handler for retrieving tool summaries."""

    def __init__(self, tool_repository: SourceToolDtoRepository):
        super().__init__()
        self.tool_repository = tool_repository

    async def handle_async(self, request: GetToolSummariesQuery) -> OperationResult[List[SourceToolSummaryDto]]:
        """Handle get tool summaries query."""
        summaries = await self.tool_repository.get_summaries_async(
            source_id=request.source_id,
            include_disabled=request.include_disabled,
        )

        return self.ok(summaries)
