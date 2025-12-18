"""Domain models for Agent Host.

Value objects and domain models.
"""

from domain.models.agent_definition import DEFAULT_REACTIVE_AGENT, AgentDefinition
from domain.models.blueprint_models import (
    DifficultyConfig,
    DifficultyLevel,
    DistractorStrategy,
    EvaluationMethod,
    ExamBlueprint,
    ExamDomain,
    ExamDomainSkillRef,
    ItemType,
    Skill,
)
from domain.models.client_action import ClientAction
from domain.models.client_response import ClientResponse
from domain.models.conversation_item import ConversationItem
from domain.models.conversation_template import ConversationTemplate
from domain.models.execution_state import ExecutionState, LlmMessageSnapshot, PendingToolCall
from domain.models.generated_item import GeneratedItem
from domain.models.item_content import ItemContent
from domain.models.message import Message, MessageRole, MessageStatus, ToolCall, ToolResult
from domain.models.skill_template import SkillTemplate
from domain.models.tool import Tool

__all__ = [
    # Message models
    "Message",
    "MessageRole",
    "MessageStatus",
    "ToolCall",
    "ToolResult",
    "Tool",
    # Agent Definition
    "AgentDefinition",
    "DEFAULT_REACTIVE_AGENT",
    # Conversation Template (new hierarchy)
    "ConversationTemplate",
    "ConversationItem",
    "ItemContent",
    # Skill Template (for templated content generation)
    "SkillTemplate",
    # Client Action/Response
    "ClientAction",
    "ClientResponse",
    # Execution state
    "ExecutionState",
    "LlmMessageSnapshot",
    "PendingToolCall",
    # Blueprint models
    "Skill",
    "ExamDomainSkillRef",
    "ExamDomain",
    "ExamBlueprint",
    "DifficultyLevel",
    "DifficultyConfig",
    "DistractorStrategy",
    "EvaluationMethod",
    "ItemType",
    # Generated item
    "GeneratedItem",
]
