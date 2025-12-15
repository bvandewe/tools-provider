"""Domain value objects for MCP Tools Provider.

These are immutable value objects that encapsulate domain concepts.
They are used within aggregates and events.

All value objects use @dataclass(frozen=True) for immutability.
"""

from .auth_config import AuthConfig
from .claim_matcher import ClaimMatcher
from .execution_profile import ExecutionProfile
from .mcp_config import McpEnvironmentVariable, McpSourceConfig
from .mcp_manifest import McpEnvVarDefinition, McpManifest, McpManifestError, McpPackage
from .poll_config import PollConfig
from .tool_definition import ToolDefinition
from .tool_group_membership import ToolGroupMembership
from .tool_selector import ToolSelector

__all__ = [
    "AuthConfig",
    "ClaimMatcher",
    "ExecutionProfile",
    "McpEnvironmentVariable",
    "McpEnvVarDefinition",
    "McpManifest",
    "McpManifestError",
    "McpPackage",
    "McpSourceConfig",
    "PollConfig",
    "ToolDefinition",
    "ToolGroupMembership",
    "ToolSelector",
]
