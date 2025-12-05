"""SourceToolDto Repository interface for the Read Model."""

from abc import ABC, abstractmethod
from typing import List, Optional

from neuroglia.data.infrastructure.abstractions import Repository

from integration.models.source_tool_dto import SourceToolDto, SourceToolSummaryDto


class SourceToolDtoRepository(Repository[SourceToolDto, str], ABC):
    """Repository interface for SourceTool read model.

    Extends the base Repository with tool-specific query methods.
    Implementation will use MongoDB via Motor async driver.
    """

    @abstractmethod
    async def get_by_source_id_async(
        self,
        source_id: str,
        include_disabled: bool = False,
        include_deprecated: bool = False,
    ) -> List[SourceToolDto]:
        """Get all tools for a specific source.

        Args:
            source_id: The upstream source ID
            include_disabled: Whether to include disabled tools
            include_deprecated: Whether to include deprecated tools

        Returns:
            List of tools for the source
        """
        ...

    @abstractmethod
    async def get_enabled_async(self) -> List[SourceToolDto]:
        """Get all enabled, active tools across all sources.

        Returns:
            List of enabled tools
        """
        ...

    @abstractmethod
    async def get_by_ids_async(self, tool_ids: List[str]) -> List[SourceToolDto]:
        """Get multiple tools by their IDs.

        Args:
            tool_ids: List of tool IDs to retrieve

        Returns:
            List of tools (may be less than requested if some not found)
        """
        ...

    @abstractmethod
    async def search_async(
        self,
        query: str,
        source_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        include_disabled: bool = False,
    ) -> List[SourceToolDto]:
        """Search tools by name, description, or tags.

        Args:
            query: Search query (matches name, description)
            source_id: Optional filter by source
            tags: Optional filter by tags (all must match)
            include_disabled: Whether to include disabled tools

        Returns:
            List of matching tools
        """
        ...

    @abstractmethod
    async def get_summaries_async(
        self,
        source_id: Optional[str] = None,
        include_disabled: bool = False,
    ) -> List[SourceToolSummaryDto]:
        """Get lightweight tool summaries for listing.

        Args:
            source_id: Optional filter by source
            include_disabled: Whether to include disabled tools

        Returns:
            List of tool summaries
        """
        ...

    @abstractmethod
    async def count_by_source_async(
        self,
        source_id: str,
        include_disabled: bool = False,
    ) -> int:
        """Count tools for a specific source.

        Args:
            source_id: The upstream source ID
            include_disabled: Whether to count disabled tools

        Returns:
            Number of tools
        """
        ...

    @abstractmethod
    async def bulk_update_source_name_async(
        self,
        source_id: str,
        source_name: str,
    ) -> int:
        """Update the source_name for all tools from a source.

        Called when the source name is updated to keep denormalized data in sync.

        Args:
            source_id: The source whose tools to update
            source_name: The new source name

        Returns:
            Number of tools updated
        """
        ...

    @abstractmethod
    async def get_orphaned_tools_async(
        self,
        valid_source_ids: List[str],
    ) -> List[SourceToolDto]:
        """Get tools whose source_id is not in the list of valid sources.

        Used to find orphaned tools after source deletion.

        Args:
            valid_source_ids: List of existing source IDs

        Returns:
            List of orphaned tools
        """
        ...
