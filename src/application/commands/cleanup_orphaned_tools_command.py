"""Cleanup orphaned tools command with handler.

Provides admin functionality to find and delete tools whose upstream source
no longer exists in the system.
"""

import logging
import time
from dataclasses import dataclass
from typing import List, Optional

from kurrentdbclient.exceptions import NotFoundError as StreamNotFound
from neuroglia.core import OperationResult
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.mediation import Command, CommandHandler
from neuroglia.observability.tracing import add_span_attributes
from opentelemetry import trace

from domain.entities import SourceTool
from domain.repositories.source_dto_repository import SourceDtoRepository
from domain.repositories.source_tool_dto_repository import SourceToolDtoRepository

log = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


@dataclass
class OrphanedToolInfo:
    """Information about an orphaned tool."""

    tool_id: str
    tool_name: str
    source_id: str
    source_name: str


@dataclass
class CleanupOrphanedToolsCommand(Command[OperationResult]):
    """Command to find and optionally delete orphaned tools.

    Orphaned tools are tools whose upstream source no longer exists.
    This can happen if a source was deleted before cascading deletion
    was implemented.
    """

    dry_run: bool = True  # If True, only report orphans; if False, delete them
    reason: Optional[str] = None
    user_info: dict | None = None


@dataclass
class CleanupOrphanedToolsResult:
    """Result of orphaned tools cleanup operation."""

    orphaned_tools: List[OrphanedToolInfo]
    tools_deleted: int
    dry_run: bool
    processing_time_ms: float


class CleanupOrphanedToolsCommandHandler(CommandHandler[CleanupOrphanedToolsCommand, OperationResult]):
    """Handle cleanup of orphaned tools.

    Admin-only operation that finds tools whose source no longer exists
    and optionally deletes them.
    """

    def __init__(
        self,
        source_dto_repository: SourceDtoRepository,
        tool_repository: Repository[SourceTool, str],
        tool_dto_repository: SourceToolDtoRepository,
    ):
        super().__init__()
        self.source_dto_repository = source_dto_repository
        self.tool_repository = tool_repository
        self.tool_dto_repository = tool_dto_repository

    async def handle_async(self, request: CleanupOrphanedToolsCommand) -> OperationResult:
        """Handle cleanup orphaned tools command."""
        command = request
        start_time = time.time()

        # Add business context to automatic span
        add_span_attributes(
            {
                "cleanup.dry_run": command.dry_run,
                "cleanup.has_user_info": command.user_info is not None,
            }
        )

        # Determine deleted_by from user context
        deleted_by = None
        if command.user_info:
            deleted_by = command.user_info.get("sub")

        orphaned_tools: List[OrphanedToolInfo] = []
        tools_deleted = 0

        with tracer.start_as_current_span("find_orphaned_tools") as span:
            # Get all valid source IDs from the read model
            all_sources = await self.source_dto_repository.get_all_async()
            valid_source_ids = [source.id for source in all_sources]
            span.set_attribute("sources.valid_count", len(valid_source_ids))

            # Find orphaned tools
            orphaned_tool_dtos = await self.tool_dto_repository.get_orphaned_tools_async(valid_source_ids)
            span.set_attribute("tools.orphaned_count", len(orphaned_tool_dtos))

            for dto in orphaned_tool_dtos:
                orphaned_tools.append(
                    OrphanedToolInfo(
                        tool_id=dto.id,
                        tool_name=dto.tool_name,
                        source_id=dto.source_id,
                        source_name=dto.source_name,
                    )
                )

            log.info(f"Found {len(orphaned_tools)} orphaned tools from {len(set(t.source_id for t in orphaned_tools))} deleted sources")

        # If not dry run, delete the orphaned tools
        if not command.dry_run and orphaned_tools:
            with tracer.start_as_current_span("delete_orphaned_tools") as span:
                for orphan in orphaned_tools:
                    try:
                        # Try to get from write model and mark as deleted
                        try:
                            tool = await self.tool_repository.get_async(orphan.tool_id)
                            if tool:
                                tool.mark_as_deleted(
                                    deleted_by=deleted_by,
                                    reason=command.reason or "Orphaned tool cleanup: source no longer exists",
                                )
                                await self.tool_repository.update_async(tool)
                                await self.tool_repository.remove_async(orphan.tool_id)
                                tools_deleted += 1
                                log.debug(f"Deleted orphaned tool {orphan.tool_id} ({orphan.tool_name})")
                        except StreamNotFound:
                            # Tool not in write model (event stream), delete from read model only
                            await self.tool_dto_repository.remove_async(orphan.tool_id)
                            tools_deleted += 1
                            log.debug(f"Removed orphaned tool {orphan.tool_id} from read model only")
                    except Exception as e:
                        log.warning(f"Failed to delete orphaned tool {orphan.tool_id}: {e}")
                        span.record_exception(e)

                span.set_attribute("tools.deleted", tools_deleted)
                log.info(f"Deleted {tools_deleted} orphaned tools")

        # Record metrics
        processing_time_ms = (time.time() - start_time) * 1000

        return self.ok(
            {
                "orphaned_tools": [
                    {
                        "tool_id": t.tool_id,
                        "tool_name": t.tool_name,
                        "source_id": t.source_id,
                        "source_name": t.source_name,
                    }
                    for t in orphaned_tools
                ],
                "orphaned_count": len(orphaned_tools),
                "tools_deleted": tools_deleted,
                "dry_run": command.dry_run,
                "message": (f"Found {len(orphaned_tools)} orphaned tools" if command.dry_run else f"Deleted {tools_deleted} orphaned tools"),
                "processing_time_ms": processing_time_ms,
            }
        )
