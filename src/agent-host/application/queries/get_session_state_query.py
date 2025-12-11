"""Get session state query with handler.

Returns the current UI state for session restoration on reconnect/refresh.
"""

from dataclasses import dataclass
from typing import Any

from neuroglia.core import OperationResult
from neuroglia.mediation import Query, QueryHandler
from pydantic import BaseModel

from domain.entities.session import Session
from domain.repositories.session_repository import SessionRepository


class SessionStateResponse(BaseModel):
    """Response containing current session state for UI restoration.

    This is a lightweight response containing only what the frontend
    needs to restore UI state after a reconnection.
    """

    session_id: str
    status: str
    ui_state: dict[str, Any]
    pending_action: dict[str, Any] | None
    items_completed: int
    time_remaining_seconds: int | None

    class Config:
        """Pydantic configuration."""

        from_attributes = True


@dataclass
class GetSessionStateQuery(Query[OperationResult[SessionStateResponse]]):
    """Query to retrieve current session state for UI restoration.

    Attributes:
        session_id: The session ID to get state for
        user_info: User information from authentication
    """

    session_id: str
    user_info: dict[str, Any]


class GetSessionStateQueryHandler(QueryHandler[GetSessionStateQuery, OperationResult[SessionStateResponse]]):
    """Handle session state retrieval for UI restoration.

    This returns a lightweight response optimized for frontend state restoration
    after a page refresh or network reconnection.
    """

    def __init__(self, session_repository: SessionRepository):
        super().__init__()
        self.session_repository = session_repository

    async def handle_async(self, request: GetSessionStateQuery) -> OperationResult[SessionStateResponse]:
        """Handle get session state query."""
        query = request

        # Get the session
        session = await self.session_repository.get_async(query.session_id)
        if session is None:
            return self.not_found(Session, query.session_id)

        # Verify user owns the session
        user_id = query.user_info.get("sub") or query.user_info.get("user_id") or query.user_info.get("preferred_username")
        if user_id and session.state.user_id != user_id:
            return self.forbidden("You don't have access to this session")

        # Build the state response
        pending_action = session.get_pending_action()
        ui_state = session.get_ui_state()

        response = SessionStateResponse(
            session_id=session.id(),
            status=session.state.status.value,
            ui_state=ui_state.to_dict(),
            pending_action=pending_action.to_dict() if pending_action else None,
            items_completed=session.get_completed_items_count(),
            time_remaining_seconds=session.get_time_remaining_seconds(),
        )

        return self.ok(response)
