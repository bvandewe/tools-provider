"""Application queries package.

This package organizes queries into semantic submodules by entity:
- conversation/: Conversation retrieval queries
- definition/: AgentDefinition retrieval queries
- template/: ConversationTemplate retrieval queries

All queries are re-exported here for backward compatibility and
Neuroglia framework auto-discovery.
"""

# Conversation queries
from .conversation import (
    GetConversationQuery,
    GetConversationQueryHandler,
    GetConversationsQuery,
    GetConversationsQueryHandler,
)

# Definition queries
from .definition import (
    GetAllDefinitionsQuery,
    GetAllDefinitionsQueryHandler,
    GetDefinitionQuery,
    GetDefinitionQueryHandler,
    GetDefinitionsQuery,
    GetDefinitionsQueryHandler,
)

# Template queries
from .template import (
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
