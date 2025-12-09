"""Abstract repository for ToolGroupDto read model queries."""

from abc import ABC, abstractmethod

from neuroglia.data.infrastructure.abstractions import Repository

from integration.models.tool_group_dto import ToolGroupDto


class ToolGroupDtoRepository(Repository[ToolGroupDto, str], ABC):
    """Abstract repository for ToolGroupDto read model queries.

    This repository provides optimized query methods for the read model (MongoDB).
    It centralizes query logic that would otherwise be repeated across query handlers.

    For write operations (create, update, delete), use Repository[ToolGroup, str]
    which handles the write model (KurrentDB) with automatic event publishing.
    """

    @abstractmethod
    async def get_all_async(self) -> list[ToolGroupDto]:
        """Retrieve all tool groups from the read model."""
        pass

    @abstractmethod
    async def get_active_async(self) -> list[ToolGroupDto]:
        """Retrieve all active tool groups."""
        pass

    @abstractmethod
    async def get_by_ids_async(self, group_ids: list[str]) -> list[ToolGroupDto]:
        """Retrieve multiple tool groups by their IDs."""
        pass

    @abstractmethod
    async def search_by_name_async(self, name_pattern: str) -> list[ToolGroupDto]:
        """Search tool groups by name pattern (case-insensitive)."""
        pass
