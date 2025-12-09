"""Get tasks query with handler and role-based filtering."""

from dataclasses import dataclass
from typing import Any

from domain.repositories import TaskDtoRepository
from integration.models.task_dto import TaskDto
from neuroglia.core import OperationResult
from neuroglia.mediation import Query, QueryHandler


@dataclass
class GetTasksQuery(Query[OperationResult[list[Any]]]):
    """Query to retrieve tasks with role-based filtering."""

    user_info: dict[str, Any]


class GetTasksQueryHandler(QueryHandler[GetTasksQuery, OperationResult[list[Any]]]):
    """Handle task retrieval with role-based filtering.

    Uses TaskDtoRepository (read model) for efficient MongoDB queries.
    This follows CQRS: Commands use EventSourcingRepository, Queries use TaskDtoRepository.
    """

    def __init__(self, task_repository: TaskDtoRepository):
        super().__init__()
        self.task_repository = task_repository

    async def handle_async(self, request: GetTasksQuery) -> OperationResult[list[TaskDto]]:
        """Handle get tasks query with RBAC logic."""
        query = request
        user_roles = query.user_info.get("roles", [])

        # RBAC Logic: Filter tasks based on user role using TaskDtoRepository methods
        if "admin" in user_roles:
            # Admins see ALL tasks
            tasks = await self.task_repository.get_all_async()
        elif "manager" in user_roles:
            # Managers see their department tasks
            department = query.user_info.get("department")
            if department:
                tasks = await self.task_repository.get_by_department_async(department)
            else:
                tasks = []
        else:
            # Regular users see only their assigned tasks
            user_id_str = query.user_info.get("sub") or query.user_info.get("user_id")
            if user_id_str:
                tasks = await self.task_repository.get_by_assignee_async(user_id_str)
            else:
                tasks = []

        return self.ok(tasks)
