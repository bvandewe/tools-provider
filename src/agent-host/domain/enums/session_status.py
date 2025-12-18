"""Session status enumeration.

Defines the lifecycle states for Session value objects.
Moved from domain/models/session_models.py for consistency.
"""

from enum import Enum


class SessionStatus(str, Enum):
    """Session lifecycle states.

    State machine transitions:
    - PENDING -> ACTIVE (on start)
    - ACTIVE -> AWAITING_CLIENT_ACTION (on client tool call)
    - AWAITING_CLIENT_ACTION -> ACTIVE (on response received)
    - ACTIVE -> COMPLETED (on completion criteria met)
    - ACTIVE -> EXPIRED (on timeout)
    - ANY -> TERMINATED (on manual termination)

    Note: When Session becomes a value object owned by Agent,
    these transitions will be enforced via Agent domain events.
    """

    PENDING = "pending"
    ACTIVE = "active"
    AWAITING_CLIENT_ACTION = "awaiting_client_action"
    COMPLETED = "completed"
    EXPIRED = "expired"
    TERMINATED = "terminated"
