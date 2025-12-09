"""Get tool groups queries with handlers.

Retrieves tool groups from the read model with optional filtering.
"""

import time
from dataclasses import dataclass
from datetime import UTC
from typing import Any

from neuroglia.core import OperationResult
from neuroglia.mediation import Query, QueryHandler
from neuroglia.observability.tracing import add_span_attributes
from observability import tool_group_processing_time, tool_group_resolution_time
from opentelemetry import trace

from domain.models import ToolSelector
from domain.repositories import SourceToolDtoRepository
from domain.repositories.tool_group_dto_repository import ToolGroupDtoRepository
from integration.models.source_tool_dto import SourceToolDto
from integration.models.tool_group_dto import ResolvedToolGroupDto, ToolGroupDto

tracer = trace.get_tracer(__name__)


@dataclass
class GetToolGroupsQuery(Query[OperationResult[list[ToolGroupDto]]]):
    """Query to retrieve tool groups with optional filtering.

    Returns full DTOs (with selectors/memberships) for listing and display.
    """

    include_inactive: bool = False
    """Whether to include inactive groups. Default is active only."""

    name_filter: str | None = None
    """Filter by name pattern (glob-style, e.g., 'finance-*')."""

    user_info: dict[str, Any] | None = None
    """User information from authentication context."""


class GetToolGroupsQueryHandler(QueryHandler[GetToolGroupsQuery, OperationResult[list[ToolGroupDto]]]):
    """Handler for retrieving tool groups from the read model."""

    def __init__(self, tool_group_repository: ToolGroupDtoRepository):
        super().__init__()
        self.tool_group_repository = tool_group_repository

    async def handle_async(self, request: GetToolGroupsQuery) -> OperationResult[list[ToolGroupDto]]:
        """Handle get tool groups query with filtering."""
        query = request
        start_time = time.time()

        # Add business context to automatic span created by CQRS middleware
        add_span_attributes(
            {
                "tool_groups.include_inactive": query.include_inactive,
                "tool_groups.has_name_filter": query.name_filter is not None,
            }
        )

        with tracer.start_as_current_span("query_tool_groups") as span:
            # Base query
            if query.include_inactive:
                groups = await self.tool_group_repository.get_all_async()
            else:
                groups = await self.tool_group_repository.get_active_async()

            span.set_attribute("tool_groups.base_count", len(groups))

            # Apply name filter
            if query.name_filter:
                groups = await self.tool_group_repository.search_by_name_async(query.name_filter)
                if not query.include_inactive:
                    groups = [g for g in groups if g.is_active]
                span.set_attribute("tool_groups.filtered_count", len(groups))

            # Return full DTOs (includes selectors, explicit_tool_ids, excluded_tool_ids)
            span.set_attribute("tool_groups.result_count", len(groups))

        # Record metrics
        processing_time_ms = (time.time() - start_time) * 1000
        tool_group_processing_time.record(processing_time_ms, {"operation": "list"})

        return self.ok(groups)


@dataclass
class GetToolGroupByIdQuery(Query[OperationResult[ToolGroupDto]]):
    """Query to retrieve a single tool group by ID with full details."""

    group_id: str
    """ID of the group to retrieve."""

    user_info: dict[str, Any] | None = None
    """User information from authentication context."""


class GetToolGroupByIdQueryHandler(QueryHandler[GetToolGroupByIdQuery, OperationResult[ToolGroupDto]]):
    """Handler for retrieving a single tool group by ID."""

    def __init__(self, tool_group_repository: ToolGroupDtoRepository):
        super().__init__()
        self.tool_group_repository = tool_group_repository

    async def handle_async(self, request: GetToolGroupByIdQuery) -> OperationResult[ToolGroupDto]:
        """Handle get tool group by ID query."""
        start_time = time.time()

        # Add business context to automatic span created by CQRS middleware
        add_span_attributes({"tool_group.id": request.group_id})

        with tracer.start_as_current_span("get_tool_group_by_id") as span:
            group = await self.tool_group_repository.get_async(request.group_id)

            if not group:
                span.set_attribute("tool_group.found", False)
                return self.not_found(ToolGroupDto, request.group_id)

            span.set_attribute("tool_group.found", True)
            span.set_attribute("tool_group.name", group.name)
            span.set_attribute("tool_group.is_active", group.is_active)

        # Record metrics
        processing_time_ms = (time.time() - start_time) * 1000
        tool_group_processing_time.record(processing_time_ms, {"operation": "get_by_id"})

        return self.ok(group)


@dataclass
class GetGroupToolsQuery(Query[OperationResult[ResolvedToolGroupDto]]):
    """Query to get the resolved tools for a specific group.

    This computes which tools belong to the group by applying:
    1. Selector pattern matching
    2. Explicit tool additions
    3. Exclusion removals
    4. Only enabled tools

    The result is the actual list of tool IDs that would be exposed
    to agents with access to this group.
    """

    group_id: str
    """ID of the group to resolve."""

    user_info: dict[str, Any] | None = None
    """User information from authentication context."""


class GetGroupToolsQueryHandler(QueryHandler[GetGroupToolsQuery, OperationResult[ResolvedToolGroupDto]]):
    """Handler for resolving the tools in a group.

    Applies the tool resolution algorithm:
    1. Start with empty set
    2. Add all ENABLED tools matching ANY selector (OR logic)
    3. Add all explicit_tool_ids
    4. Remove all excluded_tool_ids
    5. Filter to only enabled tools
    """

    def __init__(
        self,
        tool_group_repository: ToolGroupDtoRepository,
        source_tool_repository: SourceToolDtoRepository,
    ):
        super().__init__()
        self.tool_group_repository = tool_group_repository
        self.source_tool_repository = source_tool_repository

    async def handle_async(self, request: GetGroupToolsQuery) -> OperationResult[ResolvedToolGroupDto]:
        """Handle get group tools query - resolves tools using selectors."""
        from datetime import datetime

        start_time = time.time()

        # Add business context to automatic span created by CQRS middleware
        add_span_attributes({"tool_group.id": request.group_id})

        with tracer.start_as_current_span("resolve_tool_group") as span:
            # Get the group
            group = await self.tool_group_repository.get_async(request.group_id)
            if not group:
                span.set_attribute("tool_group.found", False)
                return self.not_found(ToolGroupDto, request.group_id)

            span.set_attribute("tool_group.found", True)
            span.set_attribute("tool_group.name", group.name)
            span.set_attribute("tool_group.selector_count", len(group.selectors))
            span.set_attribute("tool_group.explicit_tool_count", len(group.explicit_tool_ids))
            span.set_attribute("tool_group.excluded_tool_count", len(group.excluded_tool_ids))

            # Get all enabled tools from all sources
            all_tools = await self.source_tool_repository.get_enabled_async()
            span.set_attribute("tools.available_count", len(all_tools))

            matched_tool_ids: set[str] = set()

            # Step 1: Pattern matching with selectors (OR logic between selectors)
            for selector_dict in group.selectors:
                selector = ToolSelector.from_dict(selector_dict)
                for tool in all_tools:
                    if self._tool_matches_selector(tool, selector):
                        matched_tool_ids.add(tool.id)

            span.set_attribute("tools.matched_by_selectors", len(matched_tool_ids))

            # Step 2: Add explicit tools (they must exist and be enabled)
            explicit_added = 0
            for membership in group.explicit_tool_ids:
                tool_id = membership.get("tool_id")
                if tool_id:
                    # Verify tool exists and is enabled
                    if any(t.id == tool_id for t in all_tools):
                        matched_tool_ids.add(tool_id)
                        explicit_added += 1

            span.set_attribute("tools.explicit_added", explicit_added)

            # Step 3: Remove excluded tools
            excluded_count = 0
            for exclusion in group.excluded_tool_ids:
                tool_id = exclusion.get("tool_id")
                if tool_id and tool_id in matched_tool_ids:
                    matched_tool_ids.discard(tool_id)
                    excluded_count += 1

            span.set_attribute("tools.excluded", excluded_count)
            span.set_attribute("tools.final_count", len(matched_tool_ids))

        # Build result
        resolved = ResolvedToolGroupDto(
            id=group.id,
            name=group.name,
            description=group.description,
            tool_ids=sorted(list(matched_tool_ids)),
            tool_count=len(matched_tool_ids),
            resolved_at=datetime.now(UTC),
            is_stale=False,
        )

        # Record metrics
        processing_time_ms = (time.time() - start_time) * 1000
        tool_group_resolution_time.record(
            processing_time_ms,
            {
                "selector_count": str(len(group.selectors)),
                "tool_count": str(len(matched_tool_ids)),
            },
        )

        return self.ok(resolved)

    def _tool_matches_selector(self, tool: SourceToolDto, selector: ToolSelector) -> bool:
        """Check if a tool matches a selector's criteria.

        Uses the ToolSelector.matches() method which handles:
        - Source pattern matching (glob/regex)
        - Tool name pattern matching
        - Path pattern matching
        - Required tags (all must be present)
        - Excluded tags (none must be present)
        """
        return selector.matches(
            source_name=tool.source_name,
            tool_name=tool.tool_name,
            source_path=tool.path,
            tags=tool.tags,
        )


@dataclass
class GetToolsByGroupIdsQuery(Query[OperationResult[dict[str, list[str]]]]):
    """Query to get resolved tools for multiple groups at once.

    Returns a dictionary mapping group_id to list of tool_ids.
    Used for efficient batch resolution during access policy evaluation.
    """

    group_ids: list[str]
    """IDs of the groups to resolve."""

    user_info: dict[str, Any] | None = None
    """User information from authentication context."""


class GetToolsByGroupIdsQueryHandler(QueryHandler[GetToolsByGroupIdsQuery, OperationResult[dict[str, list[str]]]]):
    """Handler for batch resolving tools across multiple groups."""

    def __init__(
        self,
        tool_group_repository: ToolGroupDtoRepository,
        source_tool_repository: SourceToolDtoRepository,
    ):
        super().__init__()
        self.tool_group_repository = tool_group_repository
        self.source_tool_repository = source_tool_repository

    async def handle_async(self, request: GetToolsByGroupIdsQuery) -> OperationResult[dict[str, list[str]]]:
        """Handle batch get tools by group IDs query."""
        if not request.group_ids:
            return self.ok({})

        # Get all requested groups
        groups = await self.tool_group_repository.get_by_ids_async(request.group_ids)
        group_map = {g.id: g for g in groups}

        # Get all enabled tools once (shared across all groups)
        all_tools = await self.source_tool_repository.get_enabled_async()

        # Resolve each group
        result: dict[str, list[str]] = {}
        for group_id in request.group_ids:
            group = group_map.get(group_id)
            if not group or not group.is_active:
                result[group_id] = []
                continue

            matched_tool_ids: set[str] = set()

            # Pattern matching
            for selector_dict in group.selectors:
                selector = ToolSelector.from_dict(selector_dict)
                for tool in all_tools:
                    if self._tool_matches_selector(tool, selector):
                        matched_tool_ids.add(tool.id)

            # Add explicit tools
            for membership in group.explicit_tool_ids:
                tool_id = membership.get("tool_id")
                if tool_id and any(t.id == tool_id for t in all_tools):
                    matched_tool_ids.add(tool_id)

            # Remove excluded
            for exclusion in group.excluded_tool_ids:
                tool_id = exclusion.get("tool_id")
                if tool_id:
                    matched_tool_ids.discard(tool_id)

            result[group_id] = sorted(list(matched_tool_ids))

        return self.ok(result)

    def _tool_matches_selector(self, tool: SourceToolDto, selector: ToolSelector) -> bool:
        """Check if a tool matches a selector's criteria."""
        return selector.matches(
            source_name=tool.source_name,
            tool_name=tool.tool_name,
            source_path=tool.path,
            tags=tool.tags,
        )
