"""Abstract repository for AccessPolicyDto read model queries."""

from abc import ABC, abstractmethod
from typing import List

from integration.models.access_policy_dto import AccessPolicyDto
from neuroglia.data.infrastructure.abstractions import Repository


class AccessPolicyDtoRepository(Repository[AccessPolicyDto, str], ABC):
    """Abstract repository for AccessPolicyDto read model queries.

    This repository provides optimized query methods for the read model (MongoDB).
    It centralizes query logic that would otherwise be repeated across query handlers.

    For write operations (create, update, delete), use Repository[AccessPolicy, str]
    which handles the write model (KurrentDB) with automatic event publishing.
    """

    @abstractmethod
    async def get_all_async(self) -> List[AccessPolicyDto]:
        """Retrieve all access policies from the read model."""
        pass

    @abstractmethod
    async def get_active_async(self) -> List[AccessPolicyDto]:
        """Retrieve all active access policies, sorted by priority (descending)."""
        pass

    @abstractmethod
    async def get_by_priority_async(self, min_priority: int = 0) -> List[AccessPolicyDto]:
        """Retrieve policies with priority >= min_priority, sorted by priority (descending)."""
        pass

    @abstractmethod
    async def get_by_group_id_async(self, group_id: str) -> List[AccessPolicyDto]:
        """Retrieve all policies that grant access to a specific group."""
        pass

    @abstractmethod
    async def search_by_name_async(self, name_pattern: str) -> List[AccessPolicyDto]:
        """Search access policies by name pattern (case-insensitive)."""
        pass
