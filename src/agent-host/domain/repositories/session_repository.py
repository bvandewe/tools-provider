"""Abstract repository for Session read model queries.

This follows CQRS where:
- Write model: Repository[Session, str] persists to MongoDB (state-based)
- Read model: SessionRepository queries from MongoDB
"""

from abc import ABC, abstractmethod

from neuroglia.data.infrastructure.abstractions import Repository

from domain.entities.session import Session


class SessionRepository(Repository[Session, str], ABC):
    """Abstract repository for Session.

    This repository provides optimized query methods for the Session Entity (MongoDB).
    It centralizes query logic that would otherwise be repeated across application handlers.
    """

    @abstractmethod
    async def get_all_async(self) -> list[Session]:
        """Retrieve all sessions from the read model."""
        pass

    @abstractmethod
    async def get_by_user_async(self, user_id: str) -> list[Session]:
        """Retrieve sessions for a specific user."""
        pass

    @abstractmethod
    async def get_active_by_user_async(self, user_id: str) -> list[Session]:
        """Retrieve active sessions for a user.

        Active sessions are those with status in:
        - pending
        - active
        - awaiting_client_action
        """
        pass

    @abstractmethod
    async def get_by_conversation_async(self, conversation_id: str) -> Session | None:
        """Retrieve a session by its linked conversation ID."""
        pass

    @abstractmethod
    async def get_by_type_async(self, user_id: str, session_type: str) -> list[Session]:
        """Retrieve sessions of a specific type for a user."""
        pass
