"""Delete upstream source command with handler.

Provides admin functionality to permanently remove an upstream source
and all its associated tools from the system.
"""

import logging
import time
from dataclasses import dataclass

from kurrentdbclient.exceptions import NotFoundError as StreamNotFound
from neuroglia.core import OperationResult
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.mediation import Command, CommandHandler
from neuroglia.observability.tracing import add_span_attributes
from opentelemetry import trace

from domain.entities import SourceTool, UpstreamSource
from domain.repositories.source_dto_repository import SourceDtoRepository
from domain.repositories.source_tool_dto_repository import SourceToolDtoRepository

log = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


@dataclass
class DeleteSourceCommand(Command[OperationResult]):
    """Command to permanently delete an upstream source and all its tools.

    This is a hard delete operation that removes the source and all associated
    tools from both the event store and read model.
    """

    source_id: str
    reason: str | None = None
    user_info: dict | None = None


class DeleteSourceCommandHandler(CommandHandler[DeleteSourceCommand, OperationResult]):
    """Handle source deletion with cascading tool deletion.

    Admin-only operation that permanently removes an upstream source
    and all its associated tools.
    """

    def __init__(
        self,
        source_repository: Repository[UpstreamSource, str],
        source_dto_repository: SourceDtoRepository,
        tool_repository: Repository[SourceTool, str],
        tool_dto_repository: SourceToolDtoRepository,
    ):
        super().__init__()
        self.source_repository = source_repository
        self.source_dto_repository = source_dto_repository
        self.tool_repository = tool_repository
        self.tool_dto_repository = tool_dto_repository

    async def handle_async(self, request: DeleteSourceCommand) -> OperationResult:
        """Handle delete source command with cascading tool deletion."""
        command = request
        start_time = time.time()

        # Add business context to automatic span
        add_span_attributes(
            {
                "source.id": command.source_id,
                "source.has_user_info": command.user_info is not None,
            }
        )

        source = await self.source_repository.get_async(command.source_id)
        if not source:
            return self.not_found(UpstreamSource, command.source_id)

        # Determine deleted_by from user context
        deleted_by = None
        if command.user_info:
            deleted_by = command.user_info.get("sub")

        tools_deleted = 0

        # Delete all tools associated with this source first
        with tracer.start_as_current_span("delete_source_tools") as tools_span:
            # Query tools from read model to get their IDs
            tool_dtos = await self.tool_dto_repository.get_by_source_id_async(
                source_id=command.source_id,
                include_disabled=True,
                include_deprecated=True,
            )
            tools_span.set_attribute("tools.count", len(tool_dtos))

            for tool_dto in tool_dtos:
                try:
                    # Get tool from write model and mark as deleted
                    try:
                        tool = await self.tool_repository.get_async(tool_dto.id)
                        if tool:
                            # Mark as deleted and persist the event
                            tool.mark_as_deleted(
                                deleted_by=deleted_by,
                                reason=f"Cascade delete: source {command.source_id} deleted",
                            )
                            await self.tool_repository.update_async(tool)

                            # Hard delete the tool's event stream from write model
                            await self.tool_repository.remove_async(tool_dto.id)
                    except StreamNotFound:
                        # Tool already deleted from write model, continue to delete from read model
                        log.debug(f"Tool {tool_dto.id} not found in write model")

                    # Always delete from read model (MongoDB)
                    await self.tool_dto_repository.remove_async(tool_dto.id)
                    tools_deleted += 1
                    log.debug(f"Deleted tool {tool_dto.id} ({tool_dto.tool_name})")
                except Exception as e:
                    log.warning(f"Failed to delete tool {tool_dto.id}: {e}")
                    tools_span.record_exception(e)

            tools_span.set_attribute("tools.deleted", tools_deleted)
            log.info(f"Deleted {tools_deleted} tools for source {command.source_id}")

        # Now delete the source itself
        with tracer.start_as_current_span("delete_source_entity") as span:
            span.set_attribute("source.found", True)
            span.set_attribute("source.name", source.state.name)
            span.set_attribute("source.health_status", str(source.state.health_status))

            if command.user_info:
                user_roles = command.user_info.get("roles", [])
                span.set_attribute("source.user_roles", str(user_roles))
                if deleted_by:
                    span.set_attribute("source.deleted_by", deleted_by)

            # Emit SourceDeregisteredDomainEvent before hard delete
            source.mark_as_deleted(deleted_by=deleted_by)
            span.set_attribute("source.delete_mode", "hard")

            # Save the deletion event to EventStoreDB first (write model)
            await self.source_repository.update_async(source)

            # Hard delete from write model (EventStoreDB)
            await self.source_repository.remove_async(command.source_id)

            # Hard delete from read model (MongoDB)
            await self.source_dto_repository.remove_async(command.source_id)
            log.info(f"Deleted source {command.source_id} from both write and read models")

        # Record metrics
        processing_time_ms = (time.time() - start_time) * 1000

        return self.ok(
            {
                "id": command.source_id,
                "name": source.state.name,
                "tools_deleted": tools_deleted,
                "message": "Source and all associated tools deleted successfully",
                "processing_time_ms": processing_time_ms,
            }
        )
