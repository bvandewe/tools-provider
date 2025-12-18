"""Conversation queries submodule.

Contains queries for retrieving conversations:
- GetConversationQuery: Get a specific conversation by ID
- GetConversationsQuery: Get all conversations for a user
"""

from .get_conversation_query import GetConversationQuery, GetConversationQueryHandler
from .get_conversations_query import GetConversationsQuery, GetConversationsQueryHandler

__all__ = [
    # Get single conversation
    "GetConversationQuery",
    "GetConversationQueryHandler",
    # Get user's conversations
    "GetConversationsQuery",
    "GetConversationsQueryHandler",
]
