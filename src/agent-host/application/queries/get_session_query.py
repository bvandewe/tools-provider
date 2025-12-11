"""Get session query with handler."""

from dataclasses import dataclass
from typing import Any

from neuroglia.core import OperationResult
from neuroglia.mediation import Query, QueryHandler

from domain.entities.session import Session
from domain.repositories.session_repository import SessionRepository


@dataclass
class GetSessionQuery(Query[OperationResult[Session | None]]):
    """Query to retrieve a specific session.

    Attributes:
        session_id: The session ID to retrieve
        user_info: User information from authentication
    """

    session_id: str
    user_info: dict[str, Any]


class GetSessionQueryHandler(QueryHandler[GetSessionQuery, OperationResult[Session | None]]):
    """Handle session retrieval with ownership validation.

    Uses SessionRepository for MongoDB queries.
    """

    def __init__(self, session_repository: SessionRepository):
        super().__init__()
        self.session_repository = session_repository

    async def handle_async(self, request: GetSessionQuery) -> OperationResult[Session | None]:
        """Handle get session query."""
        query = request

        # Get the session
        session = await self.session_repository.get_async(query.session_id)
        if session is None:
            return self.not_found(Session, query.session_id)

        # Verify user owns the session
        user_id = query.user_info.get("sub") or query.user_info.get("user_id") or query.user_info.get("preferred_username")
        if user_id and session.state.user_id != user_id:
            return self.forbidden("You don't have access to this session")

        return self.ok(session)
