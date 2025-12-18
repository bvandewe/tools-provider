"""Application events module.

This package organizes event handlers:
- domain/: Domain event handlers for Read Model projections

All handlers are re-exported here for backward compatibility and
Neuroglia framework auto-discovery.
"""

# Re-export all domain event handlers
from .domain import (
    # Conversation projection handlers
    ConversationClearedProjectionHandler,
    ConversationCreatedProjectionHandler,
    ConversationDeletedProjectionHandler,
    ConversationTitleUpdatedProjectionHandler,
    MessageAddedProjectionHandler,
    ToolCallAddedProjectionHandler,
    ToolResultAddedProjectionHandler,
    # AgentDefinition projection handlers
    AgentDefinitionAccessUpdatedProjectionHandler,
    AgentDefinitionCreatedProjectionHandler,
    AgentDefinitionDeletedProjectionHandler,
    AgentDefinitionNameUpdatedProjectionHandler,
    AgentDefinitionSystemPromptUpdatedProjectionHandler,
    AgentDefinitionTemplateLinkUpdatedProjectionHandler,
    AgentDefinitionToolsUpdatedProjectionHandler,
    AgentDefinitionUpdatedProjectionHandler,
    # ConversationTemplate projection handlers
    ConversationTemplateCreatedProjectionHandler,
    ConversationTemplateDeletedProjectionHandler,
    ConversationTemplateDisplayUpdatedProjectionHandler,
    ConversationTemplateFlowUpdatedProjectionHandler,
    ConversationTemplateItemAddedProjectionHandler,
    ConversationTemplateItemRemovedProjectionHandler,
    ConversationTemplateItemsReorderedProjectionHandler,
    ConversationTemplateItemUpdatedProjectionHandler,
    ConversationTemplateMessagesUpdatedProjectionHandler,
    ConversationTemplateScoringUpdatedProjectionHandler,
    ConversationTemplateTimingUpdatedProjectionHandler,
    ConversationTemplateUpdatedProjectionHandler,
)

__all__ = [
    # Conversation projection handlers
    "ConversationCreatedProjectionHandler",
    "ConversationTitleUpdatedProjectionHandler",
    "ConversationDeletedProjectionHandler",
    "ConversationClearedProjectionHandler",
    "MessageAddedProjectionHandler",
    "ToolCallAddedProjectionHandler",
    "ToolResultAddedProjectionHandler",
    # AgentDefinition projection handlers
    "AgentDefinitionCreatedProjectionHandler",
    "AgentDefinitionUpdatedProjectionHandler",
    "AgentDefinitionNameUpdatedProjectionHandler",
    "AgentDefinitionSystemPromptUpdatedProjectionHandler",
    "AgentDefinitionToolsUpdatedProjectionHandler",
    "AgentDefinitionTemplateLinkUpdatedProjectionHandler",
    "AgentDefinitionAccessUpdatedProjectionHandler",
    "AgentDefinitionDeletedProjectionHandler",
    # ConversationTemplate projection handlers
    "ConversationTemplateCreatedProjectionHandler",
    "ConversationTemplateUpdatedProjectionHandler",
    "ConversationTemplateDeletedProjectionHandler",
    "ConversationTemplateItemAddedProjectionHandler",
    "ConversationTemplateItemUpdatedProjectionHandler",
    "ConversationTemplateItemRemovedProjectionHandler",
    "ConversationTemplateItemsReorderedProjectionHandler",
    "ConversationTemplateFlowUpdatedProjectionHandler",
    "ConversationTemplateTimingUpdatedProjectionHandler",
    "ConversationTemplateDisplayUpdatedProjectionHandler",
    "ConversationTemplateMessagesUpdatedProjectionHandler",
    "ConversationTemplateScoringUpdatedProjectionHandler",
]
