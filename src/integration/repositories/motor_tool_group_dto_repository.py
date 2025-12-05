"""MongoDB repository implementation for ToolGroupDto read model."""

import re
from typing import List, Optional, Tuple

from neuroglia.data.infrastructure.mongo import MotorRepository

from domain.repositories.tool_group_dto_repository import ToolGroupDtoRepository
from integration.models.tool_group_dto import ToolGroupDto


class MotorToolGroupDtoRepository(MotorRepository[ToolGroupDto, str], ToolGroupDtoRepository):
    """
    MongoDB-based repository for ToolGroupDto read model queries.

    Extends Neuroglia's MotorRepository to inherit standard CRUD operations
    and implements ToolGroupDtoRepository for custom query methods.

    This follows CQRS: Query handlers use this repository to query the read model,
    while command handlers use EventSourcingRepository for the write model.

    Note: Uses direct collection access with _find_with_options() helper instead of:
    1. Queryable lambda syntax - broken due to MotorQuery chaining bug
       (see notes/NEUROGLIA_MOTORQUERY_CHAINING_BUG.md)
    2. find_async() with sort - not supported
       (see notes/NEUROGLIA_MOTORREPOSITORY_FIND_ENHANCEMENT.md)
    """

    async def _find_with_options(
        self,
        filter_dict: dict,
        sort: Optional[List[Tuple[str, int]]] = None,
        limit: Optional[int] = None,
        skip: Optional[int] = None,
    ) -> List[ToolGroupDto]:
        """Helper method to query MongoDB with sorting and pagination.

        Workaround for Neuroglia's find_async() not supporting sort/limit/skip.

        Args:
            filter_dict: MongoDB query filter
            sort: List of (field, direction) tuples. 1=ascending, -1=descending
            limit: Maximum number of documents to return
            skip: Number of documents to skip

        Returns:
            List of ToolGroupDto entities
        """
        cursor = self.collection.find(filter_dict)

        if sort:
            cursor = cursor.sort(sort)
        if skip:
            cursor = cursor.skip(skip)
        if limit:
            cursor = cursor.limit(limit)

        entities = []
        async for doc in cursor:
            entity = self._deserialize_entity(doc)
            entities.append(entity)

        return entities

    async def get_all_async(self) -> List[ToolGroupDto]:
        """Retrieve all tool groups from MongoDB, ordered by name.

        Delegates to MotorRepository's built-in method and sorts by name.
        """
        return await self._find_with_options({}, sort=[("name", 1)])

    async def get_active_async(self) -> List[ToolGroupDto]:
        """Retrieve all active tool groups, ordered by name."""
        return await self._find_with_options({"is_active": True}, sort=[("name", 1)])

    async def get_by_ids_async(self, group_ids: List[str]) -> List[ToolGroupDto]:
        """Retrieve multiple tool groups by their IDs.

        Args:
            group_ids: List of group IDs to retrieve

        Returns:
            List of matching ToolGroupDto entities (may be less than requested if some don't exist)
        """
        if not group_ids:
            return []

        return await self._find_with_options(
            {"_id": {"$in": group_ids}},
            sort=[("name", 1)],
        )

    async def search_by_name_async(self, name_pattern: str) -> List[ToolGroupDto]:
        """Search tool groups by name pattern (case-insensitive).

        Args:
            name_pattern: Glob-style pattern to match against group names.
                          Supports * as wildcard.

        Returns:
            List of matching ToolGroupDto entities
        """
        # Convert glob pattern to regex
        regex_pattern = name_pattern.replace("*", ".*")
        regex_pattern = f"^{regex_pattern}$"

        return await self._find_with_options(
            {"name": {"$regex": regex_pattern, "$options": "i"}},
            sort=[("name", 1)],
        )

    async def get_groups_with_selector_matching_source_async(
        self,
        source_pattern: str,
    ) -> List[ToolGroupDto]:
        """Find groups with selectors that could match a given source.

        Used by CatalogProjector to determine which groups need
        recomputation when a source's inventory changes.

        Args:
            source_pattern: Source name to check against selector patterns

        Returns:
            List of groups with potentially matching selectors
        """
        # This is a simplified query - actual matching happens in the projector
        # We fetch all active groups and let the projector filter
        return await self.get_active_async()

    async def get_groups_containing_tool_async(
        self,
        tool_id: str,
    ) -> List[ToolGroupDto]:
        """Find groups that explicitly contain a tool.

        Args:
            tool_id: The tool ID to search for

        Returns:
            List of groups that have this tool in explicit_tool_ids
        """
        return await self._find_with_options(
            {"explicit_tool_ids": {"$elemMatch": {"tool_id": tool_id}}},
            sort=[("name", 1)],
        )

    async def get_groups_excluding_tool_async(
        self,
        tool_id: str,
    ) -> List[ToolGroupDto]:
        """Find groups that explicitly exclude a tool.

        Args:
            tool_id: The tool ID to search for

        Returns:
            List of groups that have this tool in excluded_tool_ids
        """
        return await self._find_with_options(
            {"excluded_tool_ids": {"$elemMatch": {"tool_id": tool_id}}},
            sort=[("name", 1)],
        )
