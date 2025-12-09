"""Check tool sync status query with handler.

Detects tools that exist in the read model (MongoDB) but not in the
write model (EventStoreDB), indicating a data sync issue.
"""

import logging
import random
from dataclasses import dataclass, field
from typing import Any

from kurrentdbclient.exceptions import NotFoundError as StreamNotFound
from neuroglia.core import OperationResult
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.mediation import Query, QueryHandler

from domain.entities.source_tool import SourceTool
from domain.repositories import SourceToolDtoRepository

log = logging.getLogger(__name__)


@dataclass
class ToolSyncStatus:
    """Result of tool sync status check."""

    total_tools_in_read_model: int = 0
    """Total number of tools in MongoDB."""

    orphaned_tool_count: int = 0
    """Number of tools in MongoDB but not in EventStoreDB."""

    orphaned_tool_ids: list[str] = field(default_factory=list)
    """List of tool IDs that are orphaned (limited to first 100)."""

    is_healthy: bool = True
    """True if all tools in read model exist in write model."""

    message: str = ""
    """Human-readable status message."""


@dataclass
class CheckToolSyncStatusQuery(Query[OperationResult[ToolSyncStatus]]):
    """Query to check if tools in read model exist in write model.

    This detects situations where EventStoreDB was cleared but MongoDB
    wasn't, leaving "ghost" tools that can't be modified.
    """

    sample_size: int = 50
    """Number of tools to sample for checking (0 = check all)."""

    user_info: dict[str, Any] | None = None
    """User information from authentication context."""


class CheckToolSyncStatusQueryHandler(QueryHandler[CheckToolSyncStatusQuery, OperationResult[ToolSyncStatus]]):
    """Handler for checking tool sync status between read and write models."""

    def __init__(
        self,
        tool_dto_repository: SourceToolDtoRepository,
        tool_write_repository: Repository[SourceTool, str],
    ):
        super().__init__()
        self._tool_dto_repository = tool_dto_repository
        self._tool_write_repository = tool_write_repository

    async def handle_async(self, request: CheckToolSyncStatusQuery) -> OperationResult[ToolSyncStatus]:
        """Check if tools in MongoDB exist in EventStoreDB."""
        query = request

        # Get tool summaries from read model (includes all tools, including disabled)
        all_tool_summaries = await self._tool_dto_repository.get_summaries_async(
            source_id=None,  # All sources
            include_disabled=True,  # Include disabled tools too
        )
        total_count = len(all_tool_summaries)

        if total_count == 0:
            return self.ok(
                ToolSyncStatus(
                    total_tools_in_read_model=0,
                    orphaned_tool_count=0,
                    orphaned_tool_ids=[],
                    is_healthy=True,
                    message="No tools in database.",
                )
            )

        # Sample tools to check (or check all if sample_size is 0)
        if query.sample_size > 0 and total_count > query.sample_size:
            tools_to_check = random.sample(all_tool_summaries, query.sample_size)  # nosec B311 - not security-sensitive
        else:
            tools_to_check = all_tool_summaries

        orphaned_ids: list[str] = []
        for tool_summary in tools_to_check:
            try:
                # Try to load from write model (EventStoreDB)
                aggregate = await self._tool_write_repository.get_async(tool_summary.id)
                if aggregate is None:
                    orphaned_ids.append(tool_summary.id)
            except StreamNotFound:
                # Stream doesn't exist in EventStoreDB
                orphaned_ids.append(tool_summary.id)
            except Exception as e:
                log.warning(f"Error checking tool {tool_summary.id}: {e}")
                # Assume orphaned if we can't verify
                orphaned_ids.append(tool_summary.id)

        # Calculate results
        orphaned_count = len(orphaned_ids)
        is_healthy = orphaned_count == 0

        # Estimate total orphaned if we only sampled
        if query.sample_size > 0 and len(tools_to_check) > 0:
            orphan_ratio = orphaned_count / len(tools_to_check)
            estimated_total_orphaned = int(total_count * orphan_ratio)
            if orphaned_count > 0:
                message = (
                    f"Found {orphaned_count} orphaned tools in sample of {len(tools_to_check)}. "
                    f"Estimated ~{estimated_total_orphaned} total orphaned out of {total_count} tools. "
                    "These tools exist in the read model but not in EventStoreDB. "
                    "Refresh the source inventory to recreate them."
                )
            else:
                message = f"All {len(tools_to_check)} sampled tools are synced correctly."
        else:
            if orphaned_count > 0:
                message = f"Found {orphaned_count} orphaned tools out of {total_count}. These tools exist in the read model but not in EventStoreDB. Refresh the source inventory to recreate them."
            else:
                message = f"All {total_count} tools are synced correctly."

        return self.ok(
            ToolSyncStatus(
                total_tools_in_read_model=total_count,
                orphaned_tool_count=orphaned_count,
                orphaned_tool_ids=orphaned_ids[:100],  # Limit to 100
                is_healthy=is_healthy,
                message=message,
            )
        )
