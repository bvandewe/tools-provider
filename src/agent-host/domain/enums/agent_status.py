"""Agent status enumeration.

Defines the lifecycle states for Agent aggregates.
"""

from enum import Enum


class AgentStatus(str, Enum):
    """Lifecycle status of an Agent aggregate.

    State transitions:
    - ACTIVE: Normal operating state, can start sessions
    - ARCHIVED: Soft-deleted, preserved for audit, cannot start new sessions

    An archived agent's event stream is preserved in EventStoreDB.
    Users can create a new agent (new UUID) to "reset" their agent.
    """

    ACTIVE = "active"
    ARCHIVED = "archived"
