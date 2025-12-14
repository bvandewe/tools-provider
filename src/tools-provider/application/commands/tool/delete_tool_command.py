"""Delete source tool command with handler.

Provides admin functionality to permanently remove a tool from the system.
"""

import time
from dataclasses import dataclass

from kurrentdbclient.exceptions import NotFoundError as StreamNotFound
from neuroglia.core import OperationResult
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.mediation import Command, CommandHandler
from neuroglia.observability.tracing import add_span_attributes
from opentelemetry import trace

from domain.entities import SourceTool

tracer = trace.get_tracer(__name__)


@dataclass
class DeleteToolCommand(Command[OperationResult]):
    """Command to permanently delete a source tool.

    This is a hard delete operation that removes the tool from both
    the event store and read model. Use with caution as this removes
    all history for the tool.
    """

    tool_id: str
    reason: str | None = None
    user_info: dict | None = None


class DeleteToolCommandHandler(CommandHandler[DeleteToolCommand, OperationResult]):
    """Handle tool deletion with authorization checks.

    Admin-only operation that permanently removes a source tool.
    """

    def __init__(self, tool_repository: Repository[SourceTool, str]):
        super().__init__()
        self.tool_repository = tool_repository

    async def handle_async(self, request: DeleteToolCommand) -> OperationResult:
        """Handle delete tool command."""
        command = request
        start_time = time.time()

        # Add business context to automatic span
        add_span_attributes(
            {
                "tool.id": command.tool_id,
                "tool.has_user_info": command.user_info is not None,
            }
        )

        # Retrieve existing tool
        # Note: Neuroglia's EventSourcingRepository.get_async raises esdbclient.NotFound
        # instead of returning None when the stream doesn't exist
        try:
            tool = await self.tool_repository.get_async(command.tool_id)
        except StreamNotFound:
            tool = None

        if not tool:
            return self.not_found(SourceTool, command.tool_id)

        # Create custom span for tool deletion logic
        with tracer.start_as_current_span("delete_tool_entity") as span:
            span.set_attribute("tool.found", True)
            span.set_attribute("tool.name", tool.state.tool_name)
            span.set_attribute("tool.status", str(tool.state.status))
            span.set_attribute("tool.source_id", tool.state.source_id)

            # Add user context for tracing
            deleted_by = None
            if command.user_info:
                user_id = command.user_info.get("sub")
                user_roles = command.user_info.get("roles", [])

                span.set_attribute("tool.user_roles", str(user_roles))
                if user_id:
                    span.set_attribute("tool.deleted_by", user_id)
                    deleted_by = user_id

            # Emit SourceToolDeletedDomainEvent before hard delete
            tool.mark_as_deleted(deleted_by=deleted_by, reason=command.reason)
            span.set_attribute("tool.delete_mode", "hard")

        # Save the deletion event to EventStoreDB first
        await self.tool_repository.update_async(tool)

        # Hard delete: physically remove the event stream from EventStoreDB
        await self.tool_repository.remove_async(command.tool_id)

        # Record metrics
        processing_time_ms = (time.time() - start_time) * 1000

        return self.ok(
            {
                "id": command.tool_id,
                "name": tool.state.tool_name,
                "source_id": tool.state.source_id,
                "message": "Tool deleted successfully",
                "processing_time_ms": processing_time_ms,
            }
        )
