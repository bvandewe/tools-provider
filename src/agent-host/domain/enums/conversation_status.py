"""Conversation status enumeration.

Defines the lifecycle states for Conversation aggregates.
"""

from enum import Enum


class ConversationStatus(str, Enum):
    """Lifecycle status of a conversation.

    States:
    - PENDING: Created but not started (no messages yet)
    - ACTIVE: In progress, agent is processing
    - AWAITING_USER: Waiting for user text input
    - AWAITING_WIDGET: Waiting for widget response
    - PAUSED: User paused the conversation
    - COMPLETED: Successfully finished
    - TERMINATED: Ended early by user
    - ARCHIVED: Soft-deleted
    """

    PENDING = "pending"
    ACTIVE = "active"
    AWAITING_USER = "awaiting_user"
    AWAITING_WIDGET = "awaiting_widget"
    PAUSED = "paused"
    COMPLETED = "completed"
    TERMINATED = "terminated"
    ARCHIVED = "archived"
