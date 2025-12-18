"""Application commands for Agent Host."""

# Agent commands
from application.commands.command_handler_base import CommandHandlerBase
from application.commands.complete_message_command import CompleteMessageCommand, CompleteMessageCommandHandler, ToolCallData, ToolResultData
from application.commands.create_conversation_command import CreateConversationCommand, CreateConversationCommandHandler
from application.commands.create_definition_command import CreateDefinitionCommand, CreateDefinitionCommandHandler
from application.commands.create_template_command import CreateTemplateCommand, CreateTemplateCommandHandler
from application.commands.delete_conversation_command import DeleteConversationCommand, DeleteConversationCommandHandler
from application.commands.delete_conversations_command import DeleteConversationsCommand, DeleteConversationsCommandHandler, DeleteConversationsResult
from application.commands.delete_definition_command import DeleteDefinitionCommand, DeleteDefinitionCommandHandler
from application.commands.delete_template_command import DeleteTemplateCommand, DeleteTemplateCommandHandler
from application.commands.send_message_command import MessageResponseDto, SendMessageCommand, SendMessageCommandHandler
from application.commands.update_definition_command import UpdateDefinitionCommand, UpdateDefinitionCommandHandler
from application.commands.update_template_command import UpdateTemplateCommand, UpdateTemplateCommandHandler

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
]
