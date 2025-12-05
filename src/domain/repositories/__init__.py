"""Domain repositories package.

Contains abstract repository interfaces for the read model.
Implementations are in src/integration/repositories/.

This follows CQRS where:
- Write model: Repository[Aggregate, str] (EventSourcingRepository) persists to KurrentDB
- Read model: *DtoRepository queries from MongoDB
"""

from .source_dto_repository import SourceDtoRepository
from .source_tool_dto_repository import SourceToolDtoRepository
from .task_dto_repository import TaskDtoRepository

__all__: list[str] = [
    "TaskDtoRepository",
    "SourceDtoRepository",
    "SourceToolDtoRepository",
]
