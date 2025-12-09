"""Get agent tools query with handler.

This is the CRITICAL query for Phase 4 - resolves the tools available
to an authenticated agent based on their JWT claims and access policies.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from application.services.access_resolver import AccessResolver
from domain.repositories import AccessPolicyDtoRepository, SourceToolDtoRepository, ToolGroupDtoRepository
from infrastructure.cache import RedisCacheService
from integration.models.source_tool_dto import SourceToolDto
from neuroglia.core import OperationResult
from neuroglia.mediation import Query, QueryHandler
from observability import agent_access_denied, agent_access_resolutions, agent_resolution_time, agent_tools_resolved

logger = logging.getLogger(__name__)


@dataclass
class ToolManifestEntry:
    """A tool available to an agent.

    This is the normalized tool representation sent to agents
    via SSE or the REST API.
    """

    tool_id: str
    """Unique tool identifier (format: source_id:operation_id)."""

    name: str
    """Human-readable tool name."""

    description: str
    """Detailed description of what the tool does."""

    input_schema: Dict[str, Any]
    """JSON Schema for tool arguments."""

    source_id: str
    """ID of the upstream source providing this tool."""

    source_path: str
    """Original API path (e.g., /api/v1/users)."""

    tags: List[str] = field(default_factory=list)
    """Tags for categorization."""

    version: Optional[str] = None
    """Tool version if available."""


@dataclass
class GetAgentToolsQuery(Query[OperationResult[List[ToolManifestEntry]]]):
    """Query to resolve the tools available to an authenticated agent.

    This query:
    1. Evaluates the agent's JWT claims against active AccessPolicies
    2. Resolves which ToolGroups the agent can access
    3. Resolves the tools in those groups (selectors + explicit - excluded)
    4. Returns a deduplicated list of tool manifests
    """

    claims: Dict[str, Any]
    """Decoded JWT claims from the agent's token."""

    skip_cache: bool = False
    """If True, bypass the access resolution cache."""

    include_disabled_tools: bool = False
    """If True, include disabled tools (for admin preview)."""


class GetAgentToolsQueryHandler(QueryHandler[GetAgentToolsQuery, OperationResult[List[ToolManifestEntry]]]):
    """Handle agent tool discovery.

    This is the core query for the SSE endpoint and tool discovery API.

    Resolution Flow:
    1. AccessResolver evaluates claims against policies → Set[group_ids]
    2. For each group, resolve tools (via CatalogProjector or cached manifests)
    3. Deduplicate tools across groups
    4. Return as ToolManifestEntry list
    """

    def __init__(
        self,
        policy_repository: AccessPolicyDtoRepository,
        group_repository: ToolGroupDtoRepository,
        tool_repository: SourceToolDtoRepository,
        cache: Optional[RedisCacheService] = None,
    ):
        super().__init__()
        self._policy_repository = policy_repository
        self._group_repository = group_repository
        self._tool_repository = tool_repository
        self._cache = cache

        # Create AccessResolver
        self._access_resolver = AccessResolver(
            policy_repository=policy_repository,
            group_repository=group_repository,
            cache=cache,
        )

    async def handle_async(self, request: GetAgentToolsQuery) -> OperationResult[List[ToolManifestEntry]]:
        """Handle the get agent tools query."""
        query = request
        start_time = time.time()

        # Record access resolution attempt
        agent_access_resolutions.add(1)

        # Step 1: Resolve which groups the agent can access
        allowed_group_ids = await self._access_resolver.resolve_agent_access(
            claims=query.claims,
            skip_cache=query.skip_cache,
        )

        if not allowed_group_ids:
            logger.debug("Agent has no access to any tool groups")
            agent_access_denied.add(1)
            processing_time_ms = (time.time() - start_time) * 1000
            agent_resolution_time.record(processing_time_ms, {"result": "denied"})
            return self.ok([])

        logger.debug(f"Agent has access to {len(allowed_group_ids)} groups: {allowed_group_ids}")

        # Step 2: Get the tool groups
        groups = await self._group_repository.get_by_ids_async(list(allowed_group_ids))
        logger.debug(f"Found {len(groups)} groups in repository for IDs: {list(allowed_group_ids)}")
        for g in groups:
            logger.debug(f"  Group '{g.name}' (id={g.id}, is_active={g.is_active})")
        active_groups = [g for g in groups if g.is_active]

        if not active_groups:
            logger.debug(f"No active tool groups found for agent (found {len(groups)} groups, but none active)")
            processing_time_ms = (time.time() - start_time) * 1000
            agent_resolution_time.record(processing_time_ms, {"result": "no_active_groups"})
            return self.ok([])

        # Step 3: Resolve tools for each group
        all_tool_ids: Set[str] = set()

        for group in active_groups:
            tool_ids = await self._resolve_group_tools(group.id)
            all_tool_ids.update(tool_ids)

        if not all_tool_ids:
            logger.debug("No tools resolved from accessible groups")
            processing_time_ms = (time.time() - start_time) * 1000
            agent_resolution_time.record(processing_time_ms, {"result": "no_tools"})
            return self.ok([])

        logger.debug(f"Resolved {len(all_tool_ids)} unique tools across {len(active_groups)} groups")

        # Step 4: Load tool definitions and build manifest
        tools = await self._tool_repository.get_by_ids_async(list(all_tool_ids))
        logger.debug(f"Loaded {len(tools)} tools from repository")
        for t in tools[:2]:  # Log first 2 tools for debugging
            logger.debug(f"  Tool '{t.tool_name}': input_schema={t.input_schema}, definition keys={list(t.definition.keys()) if t.definition else 'None'}")

        # Filter by enabled status unless include_disabled_tools is set
        if not query.include_disabled_tools:
            tools = [t for t in tools if t.is_enabled]

        # Step 5: Map to ToolManifestEntry
        manifest_entries = [self._to_manifest_entry(tool) for tool in tools]
        for entry in manifest_entries[:2]:  # Log first 2 entries for debugging
            logger.debug(f"  Manifest entry '{entry.name}': input_schema has {len(entry.input_schema)} keys")

        # Record success metrics
        processing_time_ms = (time.time() - start_time) * 1000
        agent_tools_resolved.add(len(manifest_entries))
        agent_resolution_time.record(processing_time_ms, {"result": "success"})
        logger.info(f"Agent tool discovery: {len(manifest_entries)} tools available in {processing_time_ms:.2f}ms")
        return self.ok(manifest_entries)

    async def _resolve_group_tools(self, group_id: str) -> Set[str]:
        """Resolve the tool IDs for a group.

        First checks Redis cache, then computes from group definition.

        Args:
            group_id: The tool group ID

        Returns:
            Set of tool IDs in the group
        """
        # Try cache first
        if self._cache:
            try:
                cached_tools = await self._cache.get_group_manifest(group_id)
                if cached_tools is not None:
                    logger.debug(f"Cache hit for group manifest: {group_id}")
                    return set(cached_tools)
            except Exception as e:
                logger.warning(f"Cache read failed for group {group_id}: {e}")

        # Load group and compute tools
        group = await self._group_repository.get_async(group_id)
        if not group:
            return set()

        # Resolve tools using selectors and explicit memberships
        tool_ids = await self._compute_group_tools(group)

        # Cache the result
        if self._cache:
            try:
                await self._cache.set_group_manifest(group_id, list(tool_ids))
            except Exception as e:
                logger.warning(f"Cache write failed for group {group_id}: {e}")

        return tool_ids

    async def _compute_group_tools(self, group) -> Set[str]:
        """Compute the tool IDs for a group based on selectors and memberships.

        Resolution Order:
        1. Start with empty set
        2. Add all ENABLED tools matching selectors (OR logic between selectors)
        3. Add all explicit_tool_ids
        4. Remove all excluded_tool_ids

        Args:
            group: ToolGroupDto with selectors and memberships

        Returns:
            Set of resolved tool IDs
        """
        from domain.models import ToolSelector

        matched_tools: Set[str] = set()

        # 1. Pattern matching via selectors
        if group.selectors:
            # Get all enabled tools for selector matching
            all_tools = await self._tool_repository.get_enabled_async()

            for selector_dict in group.selectors:
                try:
                    selector = ToolSelector.from_dict(selector_dict)
                    for tool in all_tools:
                        if selector.matches(
                            source_name=tool.source_name,
                            tool_name=tool.tool_name,
                            tags=tool.tags if hasattr(tool, "tags") else [],
                            source_path=tool.path if hasattr(tool, "path") else "",
                        ):
                            matched_tools.add(tool.id)
                except Exception as e:
                    logger.warning(f"Failed to evaluate selector in group {group.id}: {e}")

        # 2. Add explicit tools
        if group.explicit_tool_ids:
            for membership in group.explicit_tool_ids:
                tool_id = membership.get("tool_id") if isinstance(membership, dict) else membership.tool_id
                if tool_id:
                    matched_tools.add(tool_id)

        # 3. Remove excluded tools
        if group.excluded_tool_ids:
            for exclusion in group.excluded_tool_ids:
                tool_id = exclusion.get("tool_id") if isinstance(exclusion, dict) else exclusion.tool_id
                if tool_id:
                    matched_tools.discard(tool_id)

        return matched_tools

    def _to_manifest_entry(self, tool: SourceToolDto) -> ToolManifestEntry:
        """Convert a SourceToolDto to a ToolManifestEntry.

        Args:
            tool: The source tool DTO

        Returns:
            ToolManifestEntry for the agent
        """
        # Extract input schema - prefer direct field, fallback to definition
        input_schema = tool.input_schema or {}
        if not input_schema and tool.definition:
            if isinstance(tool.definition, dict):
                input_schema = tool.definition.get("input_schema", {})
            elif hasattr(tool.definition, "input_schema"):
                input_schema = tool.definition.input_schema

        # Extract description - prefer direct field, fallback to definition
        description = tool.description or ""
        if not description and tool.definition:
            if isinstance(tool.definition, dict):
                description = tool.definition.get("description", "")
            elif hasattr(tool.definition, "description"):
                description = tool.definition.description

        # Extract source path - prefer direct field, fallback to definition
        source_path = tool.path or ""
        if not source_path and tool.definition:
            if isinstance(tool.definition, dict):
                source_path = tool.definition.get("source_path", "")
            elif hasattr(tool.definition, "source_path"):
                source_path = tool.definition.source_path

        # Extract tags - prefer direct field, fallback to definition
        tags = tool.tags or []
        if not tags and tool.definition:
            if isinstance(tool.definition, dict):
                tags = tool.definition.get("tags", [])
            elif hasattr(tool.definition, "tags"):
                tags = tool.definition.tags

        # Extract version from definition (no direct field)
        version = None
        if tool.definition:
            if isinstance(tool.definition, dict):
                version = tool.definition.get("version")
            elif hasattr(tool.definition, "version"):
                version = tool.definition.version

        return ToolManifestEntry(
            tool_id=tool.id,
            name=tool.tool_name,
            description=description,
            input_schema=input_schema,
            source_id=tool.source_id,
            source_path=source_path,
            tags=tags,
            version=version,
        )
