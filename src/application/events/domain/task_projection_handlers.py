"""
Read Model Projection Handlers for Task Aggregate.

These handlers listen to domain events streamed by the ReadModelReconciliator
and update the MongoDB read model accordingly.

The ReadModelReconciliator subscribes to EventStoreDB's category stream ($ce-tools_provider)
and publishes each event through the Mediator. These handlers receive those events
and project them to MongoDB, keeping the Read Model in sync with the Write Model.
"""

import logging
from datetime import datetime, timezone

from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.mediation import DomainEventHandler

from domain.events import (
    TaskAssigneeUpdatedDomainEvent,
    TaskCreatedDomainEvent,
    TaskDeletedDomainEvent,
    TaskDepartmentUpdatedDomainEvent,
    TaskDescriptionUpdatedDomainEvent,
    TaskPriorityUpdatedDomainEvent,
    TaskStatusUpdatedDomainEvent,
    TaskTitleUpdatedDomainEvent,
    TaskUpdatedDomainEvent,
)
from integration.models.task_dto import TaskDto

logger = logging.getLogger(__name__)


class TaskCreatedProjectionHandler(DomainEventHandler[TaskCreatedDomainEvent]):
    """Projects TaskCreatedDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[TaskDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: TaskCreatedDomainEvent) -> None:
        """Create TaskDto in Read Model."""
        logger.info(f"📥 Projecting TaskCreated: {event.aggregate_id}")

        # Idempotency check - skip if already exists
        existing = await self._repository.get_async(event.aggregate_id)
        if existing:
            logger.info(f"⏭️ Task already exists in Read Model, skipping: {event.aggregate_id}")
            return

        # Map domain event to DTO
        task_dto = TaskDto(
            id=event.aggregate_id,
            title=event.title,
            description=event.description,
            status=event.status,
            priority=event.priority,
            assignee_id=event.assignee_id,
            department=event.department,
            created_at=event.created_at,
            updated_at=event.updated_at,
            created_by=event.created_by,
        )

        await self._repository.add_async(task_dto)
        logger.info(f"✅ Projected TaskCreated to Read Model: {event.aggregate_id}")


class TaskTitleUpdatedProjectionHandler(DomainEventHandler[TaskTitleUpdatedDomainEvent]):
    """Projects TaskTitleUpdatedDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[TaskDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: TaskTitleUpdatedDomainEvent) -> None:
        """Update task title in Read Model."""
        logger.info(f"📥 Projecting TaskTitleUpdated: {event.aggregate_id}")

        task = await self._repository.get_async(event.aggregate_id)
        if task:
            task.title = event.new_title
            task.updated_at = datetime.now(timezone.utc)
            await self._repository.update_async(task)
            logger.info(f"✅ Projected TaskTitleUpdated to Read Model: {event.aggregate_id}")
        else:
            logger.warning(f"⚠️ Task not found in Read Model for title update: {event.aggregate_id}")


class TaskDescriptionUpdatedProjectionHandler(DomainEventHandler[TaskDescriptionUpdatedDomainEvent]):
    """Projects TaskDescriptionUpdatedDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[TaskDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: TaskDescriptionUpdatedDomainEvent) -> None:
        """Update task description in Read Model."""
        logger.info(f"📥 Projecting TaskDescriptionUpdated: {event.aggregate_id}")

        task = await self._repository.get_async(event.aggregate_id)
        if task:
            task.description = event.new_description
            task.updated_at = datetime.now(timezone.utc)
            await self._repository.update_async(task)
            logger.info(f"✅ Projected TaskDescriptionUpdated to Read Model: {event.aggregate_id}")
        else:
            logger.warning(f"⚠️ Task not found in Read Model for description update: {event.aggregate_id}")


class TaskStatusUpdatedProjectionHandler(DomainEventHandler[TaskStatusUpdatedDomainEvent]):
    """Projects TaskStatusUpdatedDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[TaskDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: TaskStatusUpdatedDomainEvent) -> None:
        """Update task status in Read Model."""
        logger.info(f"📥 Projecting TaskStatusUpdated: {event.aggregate_id}")

        task = await self._repository.get_async(event.aggregate_id)
        if task:
            task.status = event.new_status
            task.updated_at = datetime.now(timezone.utc)
            await self._repository.update_async(task)
            logger.info(f"✅ Projected TaskStatusUpdated to Read Model: {event.aggregate_id}")
        else:
            logger.warning(f"⚠️ Task not found in Read Model for status update: {event.aggregate_id}")


class TaskPriorityUpdatedProjectionHandler(DomainEventHandler[TaskPriorityUpdatedDomainEvent]):
    """Projects TaskPriorityUpdatedDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[TaskDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: TaskPriorityUpdatedDomainEvent) -> None:
        """Update task priority in Read Model."""
        logger.info(f"📥 Projecting TaskPriorityUpdated: {event.aggregate_id}")

        task = await self._repository.get_async(event.aggregate_id)
        if task:
            task.priority = event.new_priority
            task.updated_at = datetime.now(timezone.utc)
            await self._repository.update_async(task)
            logger.info(f"✅ Projected TaskPriorityUpdated to Read Model: {event.aggregate_id}")
        else:
            logger.warning(f"⚠️ Task not found in Read Model for priority update: {event.aggregate_id}")


class TaskAssigneeUpdatedProjectionHandler(DomainEventHandler[TaskAssigneeUpdatedDomainEvent]):
    """Projects TaskAssigneeUpdatedDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[TaskDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: TaskAssigneeUpdatedDomainEvent) -> None:
        """Update task assignee in Read Model."""
        logger.info(f"📥 Projecting TaskAssigneeUpdated: {event.aggregate_id}")

        task = await self._repository.get_async(event.aggregate_id)
        if task:
            task.assignee_id = event.new_assignee_id
            task.updated_at = datetime.now(timezone.utc)
            await self._repository.update_async(task)
            logger.info(f"✅ Projected TaskAssigneeUpdated to Read Model: {event.aggregate_id}")
        else:
            logger.warning(f"⚠️ Task not found in Read Model for assignee update: {event.aggregate_id}")


class TaskDepartmentUpdatedProjectionHandler(DomainEventHandler[TaskDepartmentUpdatedDomainEvent]):
    """Projects TaskDepartmentUpdatedDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[TaskDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: TaskDepartmentUpdatedDomainEvent) -> None:
        """Update task department in Read Model."""
        logger.info(f"📥 Projecting TaskDepartmentUpdated: {event.aggregate_id}")

        task = await self._repository.get_async(event.aggregate_id)
        if task:
            task.department = event.new_department
            task.updated_at = datetime.now(timezone.utc)
            await self._repository.update_async(task)
            logger.info(f"✅ Projected TaskDepartmentUpdated to Read Model: {event.aggregate_id}")
        else:
            logger.warning(f"⚠️ Task not found in Read Model for department update: {event.aggregate_id}")


class TaskUpdatedProjectionHandler(DomainEventHandler[TaskUpdatedDomainEvent]):
    """Projects TaskUpdatedDomainEvent to MongoDB Read Model.

    This is a catch-all handler for bulk updates that may update multiple fields.
    """

    def __init__(self, repository: Repository[TaskDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: TaskUpdatedDomainEvent) -> None:
        """Update multiple task fields in Read Model."""
        logger.info(f"📥 Projecting TaskUpdated: {event.aggregate_id}")

        task = await self._repository.get_async(event.aggregate_id)
        if task:
            # Only update fields that were provided (not None)
            if event.title is not None:
                task.title = event.title
            if event.description is not None:
                task.description = event.description
            if event.status is not None:
                task.status = event.status
            if event.priority is not None:
                task.priority = event.priority
            if event.assignee_id is not None:
                task.assignee_id = event.assignee_id
            if hasattr(event, "department") and event.department is not None:
                task.department = event.department

            task.updated_at = getattr(event, "updated_at", datetime.now(timezone.utc))
            await self._repository.update_async(task)
            logger.info(f"✅ Projected TaskUpdated to Read Model: {event.aggregate_id}")
        else:
            logger.warning(f"⚠️ Task not found in Read Model for bulk update: {event.aggregate_id}")


class TaskDeletedProjectionHandler(DomainEventHandler[TaskDeletedDomainEvent]):
    """Projects TaskDeletedDomainEvent to MongoDB Read Model by removing the TaskDto."""

    def __init__(self, repository: Repository[TaskDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: TaskDeletedDomainEvent) -> None:
        """Remove TaskDto from Read Model."""
        logger.info(f"📥 Projecting TaskDeleted: {event.aggregate_id} (deleted by: {event.deleted_by})")

        # Check if task exists before trying to remove
        existing = await self._repository.get_async(event.aggregate_id)
        if existing:
            await self._repository.remove_async(event.aggregate_id)
            logger.info(f"✅ Removed Task from Read Model: {event.aggregate_id}")
        else:
            logger.warning(f"⚠️ Task not found in Read Model for deletion: {event.aggregate_id}")
