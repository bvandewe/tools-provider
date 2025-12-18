"""Domain repositories package.

Contains abstract repository interfaces for the read model.
Implementations are in src/integration/repositories/.

This follows CQRS where:
- Write model: Repository[Entity, str] persists to EventStoreDB (event-sourced)
- Read model: *DtoRepository queries from MongoDB
"""

from domain.repositories.conversation_dto_repository import ConversationDtoRepository
from domain.repositories.conversation_repository import ConversationRepository
from domain.repositories.definition_repository import DefinitionRepository
from domain.repositories.template_repository import TemplateRepository

__all__: list[str] = [
    "ConversationRepository",
    "ConversationDtoRepository",
    "DefinitionRepository",
    "TemplateRepository",
]
