"""Domain repositories package.

Contains abstract repository interfaces for the read model.
Implementations are in src/integration/repositories/.

This follows CQRS where:
- Write model: Repository[Entity, str] persists to MongoDB (state-based)
- Read model: Custom repository methods for optimized queries
"""

from domain.repositories.conversation_repository import ConversationRepository
from domain.repositories.session_repository import SessionRepository

__all__: list[str] = [
    "ConversationRepository",
    "SessionRepository",
]
