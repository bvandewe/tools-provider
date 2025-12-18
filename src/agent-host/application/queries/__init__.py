"""Application queries for Agent Host."""

# Conversation queries
from application.queries.get_conversation_query import GetConversationQuery, GetConversationQueryHandler
from application.queries.get_conversations_query import GetConversationsQuery, GetConversationsQueryHandler

# Definition queries
from application.queries.get_definitions_query import (
    GetAllDefinitionsQuery,
    GetAllDefinitionsQueryHandler,
    GetDefinitionQuery,
    GetDefinitionQueryHandler,
    GetDefinitionsQuery,
    GetDefinitionsQueryHandler,
)

# Template queries
from application.queries.get_templates_query import (
    GetTemplateQuery,
    GetTemplateQueryHandler,
    GetTemplatesQuery,
    GetTemplatesQueryHandler,
)

__all__ = [
    # Conversation queries
    "GetConversationQuery",
    "GetConversationQueryHandler",
    "GetConversationsQuery",
    "GetConversationsQueryHandler",
    # Definition queries (User)
    "GetDefinitionsQuery",
    "GetDefinitionsQueryHandler",
    "GetDefinitionQuery",
    "GetDefinitionQueryHandler",
    # Definition queries (Admin)
    "GetAllDefinitionsQuery",
    "GetAllDefinitionsQueryHandler",
    # Template queries
    "GetTemplatesQuery",
    "GetTemplatesQueryHandler",
    "GetTemplateQuery",
    "GetTemplateQueryHandler",
]
