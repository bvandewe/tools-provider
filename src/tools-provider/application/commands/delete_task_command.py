"""Delete task command with handler."""

import time
from dataclasses import dataclass

from domain.entities import Task
from neuroglia.core import OperationResult
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.mediation import Command, CommandHandler
from neuroglia.observability.tracing import add_span_attributes
from observability import task_processing_time, tasks_failed
from opentelemetry import trace

tracer = trace.get_tracer(__name__)


@dataclass
class DeleteTaskCommand(Command[OperationResult]):
    """Command to delete an existing task."""

    task_id: str
    user_info: dict | None = None


class DeleteTaskCommandHandler(CommandHandler[DeleteTaskCommand, OperationResult]):
    """Handle task deletion with authorization checks."""

    def __init__(self, task_repository: Repository[Task, str]):
        super().__init__()
        self.task_repository = task_repository

    async def handle_async(self, request: DeleteTaskCommand) -> OperationResult:
        """Handle delete task command with custom instrumentation."""
        command = request
        start_time = time.time()

        # Add business context to automatic span
        add_span_attributes(
            {
                "task.id": command.task_id,
                "task.has_user_info": command.user_info is not None,
            }
        )

        # Retrieve existing task (auto-traced)
        task = await self.task_repository.get_async(command.task_id)

        if not task:
            tasks_failed.add(1, {"reason": "not_found", "operation": "delete"})
            return self.not_found(Task, command.task_id)

        # Create custom span for task deletion logic
        with tracer.start_as_current_span("delete_task_entity") as span:
            span.set_attribute("task.found", True)
            span.set_attribute("task.title", task.state.title)
            span.set_attribute("task.status", task.state.status)

            # Add user context for tracing (authorization already checked at API layer)
            deleted_by = None
            if command.user_info:
                user_id = command.user_info.get("sub")
                user_roles = command.user_info.get("roles", [])

                span.set_attribute("task.user_roles", str(user_roles))
                if user_id:
                    span.set_attribute("task.deleted_by", user_id)
                    deleted_by = user_id

            # Emit TaskDeletedDomainEvent before hard delete
            # This triggers the projection handler to remove the task from the read model (MongoDB)
            task.mark_as_deleted(deleted_by=deleted_by)
            span.set_attribute("task.delete_mode", "hard")

        # Save the deletion event to EventStoreDB first
        # This publishes the TaskDeletedDomainEvent via Mediator, triggering read model sync
        await self.task_repository.update_async(task)

        # Hard delete: physically remove the event stream from EventStoreDB
        # This is irreversible and removes all history for this aggregate
        await self.task_repository.remove_async(command.task_id)
        deletion_successful = True

        # Record metrics
        processing_time_ms = (time.time() - start_time) * 1000

        if deletion_successful:
            task_processing_time.record(
                processing_time_ms,
                {
                    "operation": "delete",
                    "priority": task.state.priority,
                    "status": "success",
                },
            )

            return self.ok(
                {
                    "id": command.task_id,
                    "title": task.state.title,
                    "message": "Task deleted successfully",
                }
            )
        else:
            tasks_failed.add(1, {"operation": "delete", "reason": "deletion_failed"})
            task_processing_time.record(
                processing_time_ms,
                {
                    "operation": "delete",
                    "priority": task.state.priority,
                    "status": "failed",
                },
            )

            return self.bad_request("Failed to delete task")
