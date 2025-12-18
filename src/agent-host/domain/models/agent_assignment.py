"""Agent assignment value object for multi-user access.

This module contains the AgentAssignment value object that tracks
user assignments to agents with role-based access control.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from domain.enums import AssignmentRole


@dataclass
class AgentAssignment:
    """Tracks a user's assignment to an agent.

    Enables multi-user sharing of agents with role-based access control.
    Each assignment links a user to an agent with a specific role that
    determines their permissions.

    Roles:
    - PRIMARY: Owner - full control (create, archive, configure)
    - SHARED: Team member - can interact with the agent normally
    - MENTEE: Being mentored - limited write access, guided interactions
    - OBSERVER: Read-only access - can view sessions but not interact

    Attributes:
        user_id: The assigned user's identifier
        role: The role determining access level
        assigned_at: When the assignment was created
        assigned_by: User ID who made the assignment
    """

    user_id: str
    role: AssignmentRole
    assigned_at: datetime
    assigned_by: str  # User ID who made the assignment

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for persistence."""
        return {
            "user_id": self.user_id,
            "role": self.role.value,
            "assigned_at": self.assigned_at.isoformat(),
            "assigned_by": self.assigned_by,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentAssignment":
        """Deserialize from dictionary."""
        return cls(
            user_id=data["user_id"],
            role=AssignmentRole(data["role"]),
            assigned_at=datetime.fromisoformat(data["assigned_at"]),
            assigned_by=data["assigned_by"],
        )
