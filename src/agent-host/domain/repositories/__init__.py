"""Domain repositories package.

Contains abstract repository interfaces for aggregates.
Implementations are in src/integration/repositories/.

Repository Architecture (MongoDB-only via MotorRepository):
- Each aggregate has a single repository for both reads and writes
- Query handlers read from aggregates and map to response models
- No separate DTOs or projections needed

All repositories are configured via MotorRepository.configure() in main.py.
Domain events are published via CloudEventPublisher.
"""

from domain.repositories.conversation_repository import ConversationRepository
from domain.repositories.definition_repository import AgentDefinitionRepository
from domain.repositories.template_repository import ConversationTemplateRepository

__all__: list[str] = [
    "ConversationRepository",
    "AgentDefinitionRepository",
    "ConversationTemplateRepository",
]
