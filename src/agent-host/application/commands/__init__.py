"""Application commands package.

This package organizes commands into semantic submodules by entity:
- conversation/: Conversation lifecycle commands
- definition/: AgentDefinition CRUD commands
- template/: ConversationTemplate CRUD commands
- admin/: Administrative commands (reset database, etc.)

All commands are re-exported here for backward compatibility and
Neuroglia framework auto-discovery.
"""

# Shared base class (stays in root)
# Admin commands
from .admin import (
    ResetDatabaseCommand,
    ResetDatabaseCommandHandler,
    ResetDatabaseResult,
)
from .command_handler_base import CommandHandlerBase

# Conversation commands
from .conversation import (
    CompleteMessageCommand,
    CompleteMessageCommandHandler,
    CreateConversationCommand,
    CreateConversationCommandHandler,
    DeleteConversationCommand,
    DeleteConversationCommandHandler,
    DeleteConversationsCommand,
    DeleteConversationsCommandHandler,
    DeleteConversationsResult,
    MessageResponseDto,
    SendMessageCommand,
    SendMessageCommandHandler,
    ToolCallData,
    ToolResultData,
)

# Definition commands
from .definition import (
    CreateDefinitionCommand,
    CreateDefinitionCommandHandler,
    DeleteDefinitionCommand,
    DeleteDefinitionCommandHandler,
    UpdateDefinitionCommand,
    UpdateDefinitionCommandHandler,
)

# Template commands
from .template import (
    CreateTemplateCommand,
    CreateTemplateCommandHandler,
    DeleteTemplateCommand,
    DeleteTemplateCommandHandler,
    UpdateTemplateCommand,
    UpdateTemplateCommandHandler,
)

__all__ = [
    "CommandHandlerBase",
    # Conversation commands
    "CreateConversationCommand",
    "CreateConversationCommandHandler",
    "SendMessageCommand",
    "SendMessageCommandHandler",
    "MessageResponseDto",
    "CompleteMessageCommand",
    "CompleteMessageCommandHandler",
    "ToolCallData",
    "ToolResultData",
    "DeleteConversationCommand",
    "DeleteConversationCommandHandler",
    "DeleteConversationsCommand",
    "DeleteConversationsCommandHandler",
    "DeleteConversationsResult",
    # Definition commands (Admin)
    "CreateDefinitionCommand",
    "CreateDefinitionCommandHandler",
    "UpdateDefinitionCommand",
    "UpdateDefinitionCommandHandler",
    "DeleteDefinitionCommand",
    "DeleteDefinitionCommandHandler",
    # Template commands (Admin)
    "CreateTemplateCommand",
    "CreateTemplateCommandHandler",
    "UpdateTemplateCommand",
    "UpdateTemplateCommandHandler",
    "DeleteTemplateCommand",
    "DeleteTemplateCommandHandler",
    # Data management commands (Admin)
    "ResetDatabaseCommand",
    "ResetDatabaseCommandHandler",
    "ResetDatabaseResult",
]
