"""Domain enumerations package for Agent Host.

This package contains all enumerations used across the domain layer,
organized into logical modules for maintainability.

Modules:
- conversation_status: Conversation lifecycle states
- share_role: Sharing access roles
- agent_status: Agent lifecycle states (ACTIVE, ARCHIVED) - legacy, keep for now
- assignment_role: Multi-user access roles - legacy, keep for now
"""

from .agent_status import AgentStatus
from .assignment_role import AssignmentRole
from .conversation_status import ConversationStatus
from .share_role import ShareRole

__all__ = [
    # Conversation enums
    "ConversationStatus",
    "ShareRole",
    # Legacy (to be removed)
    "AgentStatus",
    "AssignmentRole",
]
