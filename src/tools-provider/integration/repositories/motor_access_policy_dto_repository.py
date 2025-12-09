"""MongoDB repository implementation for AccessPolicyDto read model."""

import re
from typing import List, Optional, Tuple

from domain.repositories.access_policy_dto_repository import AccessPolicyDtoRepository
from integration.models.access_policy_dto import AccessPolicyDto
from neuroglia.data.infrastructure.mongo import MotorRepository


class MotorAccessPolicyDtoRepository(MotorRepository[AccessPolicyDto, str], AccessPolicyDtoRepository):
    """
    MongoDB-based repository for AccessPolicyDto read model queries.

    Extends Neuroglia's MotorRepository to inherit standard CRUD operations
    and implements AccessPolicyDtoRepository for custom query methods.

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
    ) -> List[AccessPolicyDto]:
        """Helper method to query MongoDB with sorting and pagination.

        Workaround for Neuroglia's find_async() not supporting sort/limit/skip.

        Args:
            filter_dict: MongoDB query filter
            sort: List of (field, direction) tuples. 1=ascending, -1=descending
            limit: Maximum number of documents to return
            skip: Number of documents to skip

        Returns:
            List of AccessPolicyDto entities
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

    async def get_all_async(self) -> List[AccessPolicyDto]:
        """Retrieve all access policies from MongoDB, ordered by priority (descending).

        Returns:
            All access policies sorted by priority (highest first)
        """
        return await self._find_with_options({}, sort=[("priority", -1), ("name", 1)])

    async def get_active_async(self) -> List[AccessPolicyDto]:
        """Retrieve all active access policies, sorted by priority (descending).

        This is the primary method used by AccessResolver for claim evaluation.
        Higher priority policies are returned first.

        Returns:
            Active access policies sorted by priority (highest first)
        """
        return await self._find_with_options(
            {"is_active": True},
            sort=[("priority", -1)],
        )

    async def get_by_priority_async(self, min_priority: int = 0) -> List[AccessPolicyDto]:
        """Retrieve policies with priority >= min_priority, sorted by priority (descending).

        Args:
            min_priority: Minimum priority threshold

        Returns:
            Matching access policies sorted by priority (highest first)
        """
        return await self._find_with_options(
            {"priority": {"$gte": min_priority}, "is_active": True},
            sort=[("priority", -1)],
        )

    async def get_by_group_id_async(self, group_id: str) -> List[AccessPolicyDto]:
        """Retrieve all policies that grant access to a specific group.

        Useful for finding which policies would be affected by group changes.

        Args:
            group_id: The tool group ID to search for

        Returns:
            Access policies that include the group in their allowed_group_ids
        """
        return await self._find_with_options(
            {"allowed_group_ids": group_id},
            sort=[("priority", -1), ("name", 1)],
        )

    async def search_by_name_async(self, name_pattern: str) -> List[AccessPolicyDto]:
        """Search access policies by name pattern (case-insensitive).

        Args:
            name_pattern: Glob-style pattern to match against policy names.
                          Supports * as wildcard.

        Returns:
            Matching access policies sorted by priority (highest first)
        """
        # Convert glob pattern to regex
        # Escape special regex characters except *
        escaped = re.escape(name_pattern).replace(r"\*", ".*")
        regex_pattern = f"^{escaped}$"

        return await self._find_with_options(
            {"name": {"$regex": regex_pattern, "$options": "i"}},
            sort=[("priority", -1), ("name", 1)],
        )
