"""Integration repositories for Agent Host.

These are the MongoDB (Motor) implementations of the repository interfaces.

Repository Architecture (MongoDB-only):
- Single repository per aggregate for both reads and writes
- Configured via MotorRepository.configure() in main.py
- Query handlers read from aggregates and map to response models
"""

from integration.repositories.motor_agent_definition_repository import MotorAgentDefinitionRepository
from integration.repositories.motor_conversation_repository import MotorConversationRepository
from integration.repositories.motor_conversation_template_repository import MotorConversationTemplateRepository

__all__ = [
    "MotorConversationRepository",
    "MotorAgentDefinitionRepository",
    "MotorConversationTemplateRepository",
]
