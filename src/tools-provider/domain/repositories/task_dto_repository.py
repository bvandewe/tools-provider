"""Abstract repository for TaskDto read model queries."""

from abc import ABC, abstractmethod

from neuroglia.data.infrastructure.abstractions import Repository

from integration.models.task_dto import TaskDto


class TaskDtoRepository(Repository[TaskDto, str], ABC):
    """Abstract repository for TaskDto read model queries.

    This repository provides optimized query methods for the read model (MongoDB).
    It centralizes query logic that would otherwise be repeated across query handlers.

    For write operations (create, update, delete), use Repository[Task, str]
    which handles the write model (EventStoreDB) with automatic event publishing.
    """

    @abstractmethod
    async def get_all_async(self) -> list[TaskDto]:
        """Retrieve all tasks from the read model."""
        pass

    @abstractmethod
    async def get_by_assignee_async(self, assignee_id: str) -> list[TaskDto]:
        """Retrieve tasks assigned to a specific user."""
        pass

    @abstractmethod
    async def get_by_department_async(self, department: str) -> list[TaskDto]:
        """Retrieve tasks for a specific department."""
        pass
