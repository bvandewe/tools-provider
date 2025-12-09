"""Abstract repository for LabelDto read model queries."""

from abc import ABC, abstractmethod
from typing import List

from integration.models.label_dto import LabelDto
from neuroglia.data.infrastructure.abstractions import Repository


class LabelDtoRepository(Repository[LabelDto, str], ABC):
    """Abstract repository for LabelDto read model queries.

    This repository provides optimized query methods for the read model (MongoDB).
    It centralizes query logic that would otherwise be repeated across query handlers.

    For write operations (create, update, delete), use Repository[Label, str]
    which handles the write model (KurrentDB) with automatic event publishing.
    """

    @abstractmethod
    async def get_all_async(self, include_deleted: bool = False) -> List[LabelDto]:
        """Retrieve all labels from the read model.

        Args:
            include_deleted: Whether to include soft-deleted labels
        """
        pass

    @abstractmethod
    async def get_by_name_async(self, name: str) -> LabelDto | None:
        """Retrieve a label by its name (case-insensitive)."""
        pass

    @abstractmethod
    async def get_active_async(self) -> List[LabelDto]:
        """Retrieve all non-deleted labels from the read model."""
        pass

    @abstractmethod
    async def search_by_name_async(self, name_filter: str) -> List[LabelDto]:
        """Search labels by name (case-insensitive partial match)."""
        pass
