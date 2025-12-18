"""Sharing role enumeration.

Defines the roles for conversation sharing.
"""

from enum import Enum


class ShareRole(str, Enum):
    """Role types for conversation sharing.

    Roles control access levels:
    - VIEWER: Read-only access to conversation
    - EDITOR: Can add messages to conversation
    - OWNER: Full control (only the creator)
    """

    VIEWER = "viewer"
    EDITOR = "editor"
    OWNER = "owner"
