import datetime
from dataclasses import dataclass
from typing import Optional

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
    assignee_id: Optional[str] = None
    department: Optional[str] = None
    created_at: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None
    created_by: Optional[str] = None
