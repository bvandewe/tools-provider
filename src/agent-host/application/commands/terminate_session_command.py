"""Terminate session command with handler.

Manually terminates a session before completion.
"""

import logging
from dataclasses import dataclass
from typing import Any

from neuroglia.core import OperationResult
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_bus import CloudEventBus
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import CloudEventPublishingOptions
from neuroglia.mapping import Mapper
from neuroglia.mediation import Command, CommandHandler, Mediator

from application.commands.command_handler_base import CommandHandlerBase
from domain.entities.session import DomainError, Session
from integration.models.session_dto import SessionDto

log = logging.getLogger(__name__)


@dataclass
class TerminateSessionCommand(Command[OperationResult[SessionDto]]):
    """Command to terminate a session.

    Attributes:
        session_id: The session to terminate
        reason: The termination reason
        user_info: User information from authentication
    """

    session_id: str
    reason: str = "User terminated"
    user_info: dict[str, Any] | None = None


class TerminateSessionCommandHandler(
    CommandHandlerBase,
    CommandHandler[TerminateSessionCommand, OperationResult[SessionDto]],
):
    """Handle session termination.

    This handler:
    1. Validates the session exists and belongs to the user
    2. Terminates the session aggregate
    3. Persists the updated session state
    """

    def __init__(
        self,
        mediator: Mediator,
        mapper: Mapper,
        cloud_event_bus: CloudEventBus,
        cloud_event_publishing_options: CloudEventPublishingOptions,
        session_repository: Repository[Session, str],
    ):
        super().__init__(
            mediator,
            mapper,
            cloud_event_bus,
            cloud_event_publishing_options,
        )
        self.session_repository = session_repository

    async def handle_async(self, request: TerminateSessionCommand) -> OperationResult[SessionDto]:
        """Handle terminate session command."""
        command = request
        user_info = command.user_info or {}

        # Get user ID
        user_id = user_info.get("sub") or user_info.get("user_id") or user_info.get("preferred_username")

        log.debug(f"Terminating session {command.session_id}, reason: {command.reason}")

        # 1. Get the session
        session = await self.session_repository.get_async(command.session_id)
        if session is None:
            return self.not_found(Session, command.session_id)

        # 2. Verify user owns the session
        if user_id and session.state.user_id != user_id:
            return self.forbidden("You don't have access to this session")

        # 3. Terminate the session
        try:
            session.terminate(command.reason)
        except DomainError as e:
            log.warning(f"Domain error terminating session: {e}")
            return self.invalid(str(e))

        # 4. Update the session
        await self.session_repository.update_async(session)
        log.info(f"Session {session.id()} terminated, reason: {command.reason}")

        # Map to DTO
        dto = SessionDto(
            id=session.id(),
            user_id=session.state.user_id,
            conversation_id=session.state.conversation_id,
            session_type=session.state.session_type.value,
            control_mode=session.state.control_mode.value,
            system_prompt=session.state.system_prompt,
            config=session.state.config,
            status=session.state.status.value,
            current_item_id=session.state.current_item_id,
            items=session.state.items,
            ui_state=session.state.ui_state,
            pending_action=session.state.pending_action,
            created_at=session.state.created_at,
            started_at=session.state.started_at,
            completed_at=session.state.completed_at,
            terminated_reason=session.state.terminated_reason,
        )

        return self.ok(dto)
