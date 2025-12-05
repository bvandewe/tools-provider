"""Domain value objects for MCP Tools Provider.

These are immutable value objects that encapsulate domain concepts.
They are used within aggregates and events.

All value objects use @dataclass(frozen=True) for immutability.
"""

from .auth_config import AuthConfig
from .claim_matcher import ClaimMatcher
from .execution_profile import ExecutionProfile
from .poll_config import PollConfig
from .tool_definition import ToolDefinition
from .tool_group_membership import ToolGroupMembership
from .tool_selector import ToolSelector

__all__ = [
    "AuthConfig",
    "ClaimMatcher",
    "ExecutionProfile",
    "PollConfig",
    "ToolDefinition",
    "ToolGroupMembership",
    "ToolSelector",
]
