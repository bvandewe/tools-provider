"""Get task by ID query with handler."""

from dataclasses import dataclass
from typing import Any

from neuroglia.core import OperationResult
from neuroglia.mediation import Query, QueryHandler

from domain.repositories import TaskDtoRepository
from integration.models.task_dto import TaskDto


@dataclass
class GetTaskByIdQuery(Query[OperationResult[dict[str, Any]]]):
    """Query to retrieve a single task by ID."""

    task_id: str
    user_info: dict[str, Any]


class GetTaskByIdQueryHandler(QueryHandler[GetTaskByIdQuery, OperationResult[dict[str, Any]]]):
    """Handle task retrieval by ID with authorization checks.

    Uses TaskDtoRepository (read model) for efficient MongoDB queries.
    This follows CQRS: Commands use EventSourcingRepository, Queries use TaskDtoRepository.
    """

    def __init__(self, task_repository: TaskDtoRepository):
        super().__init__()
        self.task_repository = task_repository

    async def handle_async(self, request: GetTaskByIdQuery) -> OperationResult[dict[str, Any]]:
        """Handle get task by ID query with RBAC logic."""
        # Retrieve task from read model (MongoDB)
        task = await self.task_repository.get_async(request.task_id)

        if not task:
            return self.not_found(TaskDto, request.task_id)

        # RBAC: Check if user can view this task
        user_roles = request.user_info.get("roles", [])
        user_id = request.user_info.get("sub") or request.user_info.get("user_id")
        department = request.user_info.get("department")

        can_view = False

        if "admin" in user_roles:
            # Admins can view all tasks
            can_view = True
        elif "manager" in user_roles:
            # Managers can view tasks in their department
            if department and task.department == department:
                can_view = True
        else:
            # Regular users can only view their assigned tasks
            if user_id and task.assignee_id == user_id:
                can_view = True

        if not can_view:
            return self.bad_request("You do not have permission to view this task")

        # TaskDto already has the right shape, convert to dict for API response
        task_dto = {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "status": task.status,
            "priority": task.priority,
            "assignee_id": task.assignee_id,
            "department": task.department,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        }

        return self.ok(task_dto)
