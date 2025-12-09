import datetime
from dataclasses import dataclass

from neuroglia.data.abstractions import Identifiable, queryable

from domain.enums import TaskPriority, TaskStatus


@queryable
@dataclass
class TaskDto(Identifiable[str]):
    id: str
    title: str
    description: str
    status: TaskStatus
    priority: TaskPriority
    assignee_id: str | None = None
    department: str | None = None
    created_at: datetime.datetime | None = None
    updated_at: datetime.datetime | None = None
    created_by: str | None = None
