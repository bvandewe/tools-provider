"""Domain entities for Agent Host.

Aggregate roots following the AggregateRoot[TState, TKey] pattern.

The architecture uses:
- Conversation: Primary aggregate for chat sessions
- AgentDefinition: Configuration aggregate defining agent behavior
- ConversationTemplate: Configuration aggregate for structured conversations (proactive agents)
"""

from domain.entities.agent_definition import (
    DEFAULT_REACTIVE_AGENT_ID,
    AgentDefinition,
    AgentDefinitionState,
    create_default_reactive_agent,
)
from domain.entities.conversation import Conversation, ConversationState
from domain.entities.conversation_template import (
    ConversationTemplate,
    ConversationTemplateState,
)

__all__ = [
    # Conversation aggregate
    "Conversation",
    "ConversationState",
    # AgentDefinition aggregate
    "AgentDefinition",
    "AgentDefinitionState",
    "DEFAULT_REACTIVE_AGENT_ID",
    "create_default_reactive_agent",
    # ConversationTemplate aggregate
    "ConversationTemplate",
    "ConversationTemplateState",
]
