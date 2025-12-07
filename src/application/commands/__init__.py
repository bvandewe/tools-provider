"""Application commands package."""

from .activate_access_policy_command import ActivateAccessPolicyCommand, ActivateAccessPolicyCommandHandler
from .activate_tool_group_command import ActivateToolGroupCommand, ActivateToolGroupCommandHandler
from .add_explicit_tool_command import AddExplicitToolCommand, AddExplicitToolCommandHandler
from .add_label_to_tool_command import AddLabelToToolCommand, AddLabelToToolCommandHandler
from .add_selector_command import AddSelectorCommand, AddSelectorCommandHandler
from .cleanup_orphaned_tools_command import CleanupOrphanedToolsCommand, CleanupOrphanedToolsCommandHandler
from .command_handler_base import CommandHandlerBase
from .create_task_command import CreateTaskCommand, CreateTaskCommandHandler

# ToolGroup commands (Phase 3) - individual files
from .create_tool_group_command import CreateToolGroupCommand, CreateToolGroupCommandHandler, SelectorInput
from .deactivate_access_policy_command import DeactivateAccessPolicyCommand, DeactivateAccessPolicyCommandHandler
from .deactivate_tool_group_command import DeactivateToolGroupCommand, DeactivateToolGroupCommandHandler

# AccessPolicy commands (Phase 4)
from .define_access_policy_command import DefineAccessPolicyCommand, DefineAccessPolicyCommandHandler
from .delete_access_policy_command import DeleteAccessPolicyCommand, DeleteAccessPolicyCommandHandler
from .delete_source_command import DeleteSourceCommand, DeleteSourceCommandHandler
from .delete_task_command import DeleteTaskCommand, DeleteTaskCommandHandler
from .delete_tool_command import DeleteToolCommand, DeleteToolCommandHandler
from .delete_tool_group_command import DeleteToolGroupCommand, DeleteToolGroupCommandHandler
from .disable_tool_command import DisableToolCommand, DisableToolCommandHandler
from .enable_tool_command import EnableToolCommand, EnableToolCommandHandler
from .exclude_tool_command import ExcludeToolCommand, ExcludeToolCommandHandler

# Tool execution command (Phase 5)
from .execute_tool_command import ExecuteToolCommand, ExecuteToolCommandHandler
from .include_tool_command import IncludeToolCommand, IncludeToolCommandHandler
from .refresh_inventory_command import RefreshInventoryCommand, RefreshInventoryCommandHandler, RefreshInventoryResult
from .register_source_command import RegisterSourceCommand, RegisterSourceCommandHandler
from .remove_explicit_tool_command import RemoveExplicitToolCommand, RemoveExplicitToolCommandHandler
from .remove_label_from_tool_command import RemoveLabelFromToolCommand, RemoveLabelFromToolCommandHandler
from .remove_selector_command import RemoveSelectorCommand, RemoveSelectorCommandHandler
from .sync_tool_group_selectors_command import SyncToolGroupSelectorsCommand, SyncToolGroupSelectorsCommandHandler
from .sync_tool_group_tools_command import SyncToolGroupToolsCommand, SyncToolGroupToolsCommandHandler
from .update_access_policy_command import UpdateAccessPolicyCommand, UpdateAccessPolicyCommandHandler
from .update_task_command import UpdateTaskCommand, UpdateTaskCommandHandler
from .update_tool_group_command import UpdateToolGroupCommand, UpdateToolGroupCommandHandler

__all__ = [
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
    "RefreshInventoryCommand",
    "RefreshInventoryCommandHandler",
    "RefreshInventoryResult",
    "DeleteSourceCommand",
    "DeleteSourceCommandHandler",
    # Tool commands
    "DeleteToolCommand",
    "DeleteToolCommandHandler",
    "EnableToolCommand",
    "EnableToolCommandHandler",
    "DisableToolCommand",
    "DisableToolCommandHandler",
    "CleanupOrphanedToolsCommand",
    "CleanupOrphanedToolsCommandHandler",
    # ToolGroup commands (Phase 3)
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
    "ExcludeToolCommand",
    "ExcludeToolCommandHandler",
    "IncludeToolCommand",
    "IncludeToolCommandHandler",
    # Tool label commands
    "AddLabelToToolCommand",
    "AddLabelToToolCommandHandler",
    "RemoveLabelFromToolCommand",
    "RemoveLabelFromToolCommandHandler",
    # AccessPolicy commands (Phase 4)
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
    # Tool execution command (Phase 5)
    "ExecuteToolCommand",
    "ExecuteToolCommandHandler",
]
