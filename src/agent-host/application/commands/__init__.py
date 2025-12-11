"""Application commands for Agent Host."""

from application.commands.command_handler_base import CommandHandlerBase
from application.commands.complete_message_command import CompleteMessageCommand, CompleteMessageCommandHandler, ToolCallData, ToolResultData
from application.commands.create_conversation_command import CreateConversationCommand, CreateConversationCommandHandler
from application.commands.create_session_command import CreateSessionCommand, CreateSessionCommandHandler
from application.commands.delete_conversation_command import DeleteConversationCommand, DeleteConversationCommandHandler
from application.commands.send_message_command import MessageResponseDto, SendMessageCommand, SendMessageCommandHandler
from application.commands.set_pending_action_command import SetPendingActionCommand, SetPendingActionCommandHandler
from application.commands.submit_client_response_command import SubmitClientResponseCommand, SubmitClientResponseCommandHandler
from application.commands.terminate_session_command import TerminateSessionCommand, TerminateSessionCommandHandler

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
    # Session commands
    "CreateSessionCommand",
    "CreateSessionCommandHandler",
    "SetPendingActionCommand",
    "SetPendingActionCommandHandler",
    "SubmitClientResponseCommand",
    "SubmitClientResponseCommandHandler",
    "TerminateSessionCommand",
    "TerminateSessionCommandHandler",
]
