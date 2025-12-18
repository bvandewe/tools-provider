"""Assignment role enumeration.

Defines the roles for multi-user agent access.
"""

from enum import Enum


class AssignmentRole(str, Enum):
    """Role assigned to a user for an Agent.

    Used in AgentAssignment value objects to define what actions
    a user can perform on an agent they don't own.

    Roles:
    - PRIMARY: Owner of the agent - full control (create, archive, configure)
    - SHARED: Team member - can interact with the agent normally
    - MENTEE: Being mentored - limited write access, guided interactions
    - OBSERVER: Read-only access - can view sessions but not interact

    Note: This is designed for Phase 2+ multi-user support.
    """

    PRIMARY = "primary"
    SHARED = "shared"
    MENTEE = "mentee"
    OBSERVER = "observer"
