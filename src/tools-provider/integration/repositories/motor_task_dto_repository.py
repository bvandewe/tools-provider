"""MongoDB repository implementation for TaskDto read model."""

from domain.repositories.task_dto_repository import TaskDtoRepository
from integration.models.task_dto import TaskDto
from neuroglia.data.infrastructure.mongo import MotorRepository


class MotorTaskDtoRepository(MotorRepository[TaskDto, str], TaskDtoRepository):
    """
    MongoDB-based repository for TaskDto read model queries.

    Extends Neuroglia's MotorRepository to inherit standard CRUD operations
    and implements TaskDtoRepository for custom query methods.

    This follows CQRS: Query handlers use this repository to query the read model,
    while command handlers use EventSourcingRepository for the write model.
    """

    async def get_all_async(self) -> list[TaskDto]:
        """Retrieve all tasks from MongoDB.

        Delegates to MotorRepository's built-in get_all_async method.
        """
        # MotorRepository has get_all_async built-in
        return await super().get_all_async()

    async def get_by_assignee_async(self, assignee_id: str) -> list[TaskDto]:
        """Retrieve tasks assigned to a specific user.

        Uses MongoDB query via find_async.
        """
        # return await self.find_async({"assignee_id": assignee_id})
        queryable = await self.query_async()
        return (
            await queryable.where(lambda task: task.assignee_id == assignee_id).order_by(lambda task: task.created_at).to_list_async()
        )  # type: ignore[attr-defined]  # MotorQuery has this, but Queryable base doesn't

    async def get_by_department_async(self, department: str) -> list[TaskDto]:
        """Retrieve tasks for a specific department.

        Uses MongoDB query via find_async.
        """
        # return await self.find_async({"department": department})
        queryable = await self.query_async()
        return (
            await queryable.where(lambda task: task.department == department).order_by(lambda task: task.created_at).to_list_async()
        )  # type: ignore[attr-defined]  # MotorQuery has this, but Queryable base doesn't
