"""Application commands package.

This package organizes commands into semantic submodules by entity:
- task/: Task CRUD commands
- source/: Source registration and inventory management
- tool/: Tool enable/disable, update, labeling
- tool_group/: ToolGroup management and selectors
- access_policy/: Access policy definition and lifecycle
- label/: Label CRUD commands
- execution/: Tool execution commands

All commands are re-exported here for backward compatibility and
Neuroglia framework auto-discovery.
"""

# Shared base class (stays in root)
# AccessPolicy commands
from .access_policy import (
    ActivateAccessPolicyCommand,
    ActivateAccessPolicyCommandHandler,
    ClaimMatcherInput,
    DeactivateAccessPolicyCommand,
    DeactivateAccessPolicyCommandHandler,
    DefineAccessPolicyCommand,
    DefineAccessPolicyCommandHandler,
    DeleteAccessPolicyCommand,
    DeleteAccessPolicyCommandHandler,
    UpdateAccessPolicyCommand,
    UpdateAccessPolicyCommandHandler,
)
from .command_handler_base import CommandHandlerBase

# Execution commands
from .execution import (
    ExecuteToolCommand,
    ExecuteToolCommandHandler,
)

# Label commands
from .label import (
    CreateLabelCommand,
    CreateLabelCommandHandler,
    DeleteLabelCommand,
    DeleteLabelCommandHandler,
    UpdateLabelCommand,
    UpdateLabelCommandHandler,
)

# Source commands
from .source import (
    CleanupOrphanedToolsCommand,
    CleanupOrphanedToolsCommandHandler,
    DeleteSourceCommand,
    DeleteSourceCommandHandler,
    RefreshInventoryCommand,
    RefreshInventoryCommandHandler,
    RefreshInventoryResult,
    RegisterSourceCommand,
    RegisterSourceCommandHandler,
    UpdateSourceCommand,
    UpdateSourceCommandHandler,
)

# Task commands
from .task import (
    CreateTaskCommand,
    CreateTaskCommandHandler,
    DeleteTaskCommand,
    DeleteTaskCommandHandler,
    UpdateTaskCommand,
    UpdateTaskCommandHandler,
)

# Tool commands
from .tool import (
    AddLabelToToolCommand,
    AddLabelToToolCommandHandler,
    DeleteToolCommand,
    DeleteToolCommandHandler,
    DisableToolCommand,
    DisableToolCommandHandler,
    EnableToolCommand,
    EnableToolCommandHandler,
    ExcludeToolCommand,
    ExcludeToolCommandHandler,
    IncludeToolCommand,
    IncludeToolCommandHandler,
    RemoveLabelFromToolCommand,
    RemoveLabelFromToolCommandHandler,
    UpdateToolCommand,
    UpdateToolCommandHandler,
)

# ToolGroup commands
from .tool_group import (
    ActivateToolGroupCommand,
    ActivateToolGroupCommandHandler,
    AddExplicitToolCommand,
    AddExplicitToolCommandHandler,
    AddSelectorCommand,
    AddSelectorCommandHandler,
    CreateToolGroupCommand,
    CreateToolGroupCommandHandler,
    DeactivateToolGroupCommand,
    DeactivateToolGroupCommandHandler,
    DeleteToolGroupCommand,
    DeleteToolGroupCommandHandler,
    RemoveExplicitToolCommand,
    RemoveExplicitToolCommandHandler,
    RemoveSelectorCommand,
    RemoveSelectorCommandHandler,
    SelectorInput,
    SyncToolGroupSelectorsCommand,
    SyncToolGroupSelectorsCommandHandler,
    SyncToolGroupToolsCommand,
    SyncToolGroupToolsCommandHandler,
    UpdateToolGroupCommand,
    UpdateToolGroupCommandHandler,
)

__all__ = [
    # Shared
    "CommandHandlerBase",
    # Task commands
    "CreateTaskCommand",
    "CreateTaskCommandHandler",
    "DeleteTaskCommand",
    "DeleteTaskCommandHandler",
    "UpdateTaskCommand",
    "UpdateTaskCommandHandler",
    # Source commands
    "RegisterSourceCommand",
    "RegisterSourceCommandHandler",
    "UpdateSourceCommand",
    "UpdateSourceCommandHandler",
    "RefreshInventoryCommand",
    "RefreshInventoryCommandHandler",
    "RefreshInventoryResult",
    "DeleteSourceCommand",
    "DeleteSourceCommandHandler",
    "CleanupOrphanedToolsCommand",
    "CleanupOrphanedToolsCommandHandler",
    # Tool commands
    "DeleteToolCommand",
    "DeleteToolCommandHandler",
    "EnableToolCommand",
    "EnableToolCommandHandler",
    "DisableToolCommand",
    "DisableToolCommandHandler",
    "UpdateToolCommand",
    "UpdateToolCommandHandler",
    "AddLabelToToolCommand",
    "AddLabelToToolCommandHandler",
    "RemoveLabelFromToolCommand",
    "RemoveLabelFromToolCommandHandler",
    "ExcludeToolCommand",
    "ExcludeToolCommandHandler",
    "IncludeToolCommand",
    "IncludeToolCommandHandler",
    # ToolGroup commands
    "CreateToolGroupCommand",
    "CreateToolGroupCommandHandler",
    "SelectorInput",
    "UpdateToolGroupCommand",
    "UpdateToolGroupCommandHandler",
    "DeleteToolGroupCommand",
    "DeleteToolGroupCommandHandler",
    "ActivateToolGroupCommand",
    "ActivateToolGroupCommandHandler",
    "DeactivateToolGroupCommand",
    "DeactivateToolGroupCommandHandler",
    "AddSelectorCommand",
    "AddSelectorCommandHandler",
    "RemoveSelectorCommand",
    "RemoveSelectorCommandHandler",
    "SyncToolGroupSelectorsCommand",
    "SyncToolGroupSelectorsCommandHandler",
    "SyncToolGroupToolsCommand",
    "SyncToolGroupToolsCommandHandler",
    "AddExplicitToolCommand",
    "AddExplicitToolCommandHandler",
    "RemoveExplicitToolCommand",
    "RemoveExplicitToolCommandHandler",
    # Label commands
    "CreateLabelCommand",
    "CreateLabelCommandHandler",
    "DeleteLabelCommand",
    "DeleteLabelCommandHandler",
    "UpdateLabelCommand",
    "UpdateLabelCommandHandler",
    # AccessPolicy commands
    "ClaimMatcherInput",
    "DefineAccessPolicyCommand",
    "DefineAccessPolicyCommandHandler",
    "UpdateAccessPolicyCommand",
    "UpdateAccessPolicyCommandHandler",
    "ActivateAccessPolicyCommand",
    "ActivateAccessPolicyCommandHandler",
    "DeactivateAccessPolicyCommand",
    "DeactivateAccessPolicyCommandHandler",
    "DeleteAccessPolicyCommand",
    "DeleteAccessPolicyCommandHandler",
    # Execution commands
    "ExecuteToolCommand",
    "ExecuteToolCommandHandler",
]
