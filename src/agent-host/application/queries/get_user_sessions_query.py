"""Get user sessions query with handler."""

from dataclasses import dataclass
from typing import Any

from neuroglia.core import OperationResult
from neuroglia.mediation import Query, QueryHandler

from domain.entities.session import Session
from domain.repositories.session_repository import SessionRepository


@dataclass
class GetUserSessionsQuery(Query[OperationResult[list[Session]]]):
    """Query to retrieve sessions for a user.

    Attributes:
        user_info: User information from authentication
        active_only: If True, only return active sessions
        session_type: Optional filter by session type
        limit: Maximum number of sessions to return
    """

    user_info: dict[str, Any]
    active_only: bool = False
    session_type: str | None = None
    limit: int = 50


class GetUserSessionsQueryHandler(QueryHandler[GetUserSessionsQuery, OperationResult[list[Session]]]):
    """Handle user sessions retrieval.

    Uses SessionRepository for MongoDB queries.
    """

    def __init__(self, session_repository: SessionRepository):
        super().__init__()
        self.session_repository = session_repository

    async def handle_async(self, request: GetUserSessionsQuery) -> OperationResult[list[Session]]:
        """Handle get user sessions query."""
        query = request

        # Get user ID
        user_id = query.user_info.get("sub") or query.user_info.get("user_id") or query.user_info.get("preferred_username")
        if not user_id:
            return self.forbidden("User ID is required")

        # Retrieve sessions based on filters
        if query.active_only:
            sessions = await self.session_repository.get_active_by_user_async(user_id)
        elif query.session_type:
            sessions = await self.session_repository.get_by_type_async(user_id, query.session_type)
        else:
            sessions = await self.session_repository.get_by_user_async(user_id)

        # Apply limit
        if len(sessions) > query.limit:
            sessions = sessions[: query.limit]

        return self.ok(sessions)
