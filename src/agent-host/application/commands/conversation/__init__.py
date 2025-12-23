"""Conversation commands submodule.

Contains commands for managing conversations:
- CreateConversationCommand: Start a new conversation
- SendMessageCommand: Send a user message
- CompleteMessageCommand: Complete an LLM response
- DeleteConversationCommand: Delete a single conversation
- DeleteConversationsCommand: Bulk delete conversations
- RecordItemResponseCommand: Record user response to a template item
- AdvanceTemplateCommand: Advance to the next template item
- AddVirtualMessageCommand: Add a system-generated message
- AddContentMessageCommand: Add an item content message with widget structure
- CompleteConversationCommand: Mark a conversation as completed
"""

from .add_content_message_command import AddContentMessageCommand, AddContentMessageCommandHandler, WidgetConfig
from .add_virtual_message_command import AddVirtualMessageCommand, AddVirtualMessageCommandHandler
from .advance_template_command import AdvanceTemplateCommand, AdvanceTemplateCommandHandler
from .complete_conversation_command import CompleteConversationCommand, CompleteConversationCommandHandler
from .complete_message_command import CompleteMessageCommand, CompleteMessageCommandHandler, ToolCallData, ToolResultData
from .create_conversation_command import CreateConversationCommand, CreateConversationCommandHandler
from .delete_conversation_command import DeleteConversationCommand, DeleteConversationCommandHandler
from .delete_conversations_command import DeleteConversationsCommand, DeleteConversationsCommandHandler, DeleteConversationsResult
from .record_item_response_command import RecordItemResponseCommand, RecordItemResponseCommandHandler, WidgetResponse
from .send_message_command import MessageResponseDto, SendMessageCommand, SendMessageCommandHandler

__all__ = [
    # Create conversation
    "CreateConversationCommand",
    "CreateConversationCommandHandler",
    # Send message
    "SendMessageCommand",
    "SendMessageCommandHandler",
    "MessageResponseDto",
    # Complete message
    "CompleteMessageCommand",
    "CompleteMessageCommandHandler",
    "ToolCallData",
    "ToolResultData",
    # Delete conversation
    "DeleteConversationCommand",
    "DeleteConversationCommandHandler",
    # Bulk delete
    "DeleteConversationsCommand",
    "DeleteConversationsCommandHandler",
    "DeleteConversationsResult",
    # Record item response
    "RecordItemResponseCommand",
    "RecordItemResponseCommandHandler",
    "WidgetResponse",
    # Advance template
    "AdvanceTemplateCommand",
    "AdvanceTemplateCommandHandler",
    # Virtual messages
    "AddVirtualMessageCommand",
    "AddVirtualMessageCommandHandler",
    # Content messages
    "AddContentMessageCommand",
    "AddContentMessageCommandHandler",
    "WidgetConfig",
    # Complete conversation
    "CompleteConversationCommand",
    "CompleteConversationCommandHandler",
]
