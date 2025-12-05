"""Task-related enumerations.

These enums are used by the Task aggregate for status and priority tracking.
"""

from enum import Enum


class TaskStatus(str, Enum):
    """Status values for Task aggregate."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """Priority levels for Task aggregate."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"
