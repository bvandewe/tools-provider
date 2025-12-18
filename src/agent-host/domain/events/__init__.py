"""Domain events for Agent Host."""

from domain.events.agent_definition import (
    AgentDefinitionAccessUpdatedDomainEvent,
    AgentDefinitionCreatedDomainEvent,
    AgentDefinitionDeletedDomainEvent,
    AgentDefinitionNameUpdatedDomainEvent,
    AgentDefinitionSystemPromptUpdatedDomainEvent,
    AgentDefinitionTemplateLinkUpdatedDomainEvent,
    AgentDefinitionToolsUpdatedDomainEvent,
    AgentDefinitionUpdatedDomainEvent,
)
from domain.events.conversation import (
    ConversationClearedDomainEvent,
    ConversationCreatedDomainEvent,
    ConversationDeletedDomainEvent,
    ConversationTitleUpdatedDomainEvent,
    MessageAddedDomainEvent,
    MessageStatusUpdatedDomainEvent,
    ToolCallAddedDomainEvent,
    ToolResultAddedDomainEvent,
)
from domain.events.conversation_template import (
    ConversationTemplateCreatedDomainEvent,
    ConversationTemplateDeletedDomainEvent,
    ConversationTemplateDisplayUpdatedDomainEvent,
    ConversationTemplateFlowUpdatedDomainEvent,
    ConversationTemplateItemAddedDomainEvent,
    ConversationTemplateItemRemovedDomainEvent,
    ConversationTemplateItemsReorderedDomainEvent,
    ConversationTemplateItemUpdatedDomainEvent,
    ConversationTemplateMessagesUpdatedDomainEvent,
    ConversationTemplateScoringUpdatedDomainEvent,
    ConversationTemplateTimingUpdatedDomainEvent,
    ConversationTemplateUpdatedDomainEvent,
)
from domain.events.user import UserLoggedInDomainEvent, UserLoggedOutDomainEvent

__all__ = [
    # AgentDefinition events
    "AgentDefinitionCreatedDomainEvent",
    "AgentDefinitionUpdatedDomainEvent",
    "AgentDefinitionDeletedDomainEvent",
    "AgentDefinitionNameUpdatedDomainEvent",
    "AgentDefinitionSystemPromptUpdatedDomainEvent",
    "AgentDefinitionToolsUpdatedDomainEvent",
    "AgentDefinitionTemplateLinkUpdatedDomainEvent",
    "AgentDefinitionAccessUpdatedDomainEvent",
    # Conversation events
    "ConversationCreatedDomainEvent",
    "ConversationTitleUpdatedDomainEvent",
    "MessageAddedDomainEvent",
    "ToolCallAddedDomainEvent",
    "ToolResultAddedDomainEvent",
    "MessageStatusUpdatedDomainEvent",
    "ConversationClearedDomainEvent",
    "ConversationDeletedDomainEvent",
    # ConversationTemplate events
    "ConversationTemplateCreatedDomainEvent",
    "ConversationTemplateUpdatedDomainEvent",
    "ConversationTemplateDeletedDomainEvent",
    "ConversationTemplateItemAddedDomainEvent",
    "ConversationTemplateItemUpdatedDomainEvent",
    "ConversationTemplateItemRemovedDomainEvent",
    "ConversationTemplateItemsReorderedDomainEvent",
    "ConversationTemplateFlowUpdatedDomainEvent",
    "ConversationTemplateTimingUpdatedDomainEvent",
    "ConversationTemplateDisplayUpdatedDomainEvent",
    "ConversationTemplateMessagesUpdatedDomainEvent",
    "ConversationTemplateScoringUpdatedDomainEvent",
    # User events
    "UserLoggedInDomainEvent",
    "UserLoggedOutDomainEvent",
]
