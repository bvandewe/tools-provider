"""Domain repositories package.

Contains abstract repository interfaces for the read model.
Implementations are in src/integration/repositories/.

This follows CQRS where:
- Write model: Repository[Aggregate, str] (EventSourcingRepository) persists to KurrentDB
- Read model: *DtoRepository queries from MongoDB
"""

from .access_policy_dto_repository import AccessPolicyDtoRepository
from .source_dto_repository import SourceDtoRepository
from .source_tool_dto_repository import SourceToolDtoRepository
from .task_dto_repository import TaskDtoRepository
from .tool_group_dto_repository import ToolGroupDtoRepository

__all__: list[str] = [
    "TaskDtoRepository",
    "SourceDtoRepository",
    "SourceToolDtoRepository",
    "ToolGroupDtoRepository",
    "AccessPolicyDtoRepository",
]
