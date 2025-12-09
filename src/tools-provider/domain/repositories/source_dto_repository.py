"""Abstract repository for SourceDto read model queries."""

from abc import ABC, abstractmethod
from typing import List

from domain.enums import HealthStatus
from integration.models.source_dto import SourceDto
from neuroglia.data.infrastructure.abstractions import Repository


class SourceDtoRepository(Repository[SourceDto, str], ABC):
    """Abstract repository for SourceDto read model queries.

    This repository provides optimized query methods for the read model (MongoDB).
    It centralizes query logic that would otherwise be repeated across query handlers.

    For write operations (create, update, delete), use Repository[UpstreamSource, str]
    which handles the write model (KurrentDB) with automatic event publishing.
    """

    @abstractmethod
    async def get_all_async(self) -> List[SourceDto]:
        """Retrieve all sources from the read model."""
        pass

    @abstractmethod
    async def get_enabled_async(self) -> List[SourceDto]:
        """Retrieve all enabled sources."""
        pass

    @abstractmethod
    async def get_by_health_status_async(self, status: HealthStatus) -> List[SourceDto]:
        """Retrieve sources with a specific health status."""
        pass

    @abstractmethod
    async def get_by_source_type_async(self, source_type: str) -> List[SourceDto]:
        """Retrieve sources of a specific type."""
        pass
