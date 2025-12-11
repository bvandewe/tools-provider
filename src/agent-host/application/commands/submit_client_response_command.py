"""Submit client response command with handler.

Handles user responses to pending client actions (widgets).
This resumes the session after a widget interaction.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from neuroglia.core import OperationResult
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_bus import CloudEventBus
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import CloudEventPublishingOptions
from neuroglia.mapping import Mapper
from neuroglia.mediation import Command, CommandHandler, Mediator

from application.commands.command_handler_base import CommandHandlerBase
from domain.entities.session import DomainError, Session
from domain.models.session_models import ClientResponse, ValidationStatus
from integration.models.session_dto import SessionDto

log = logging.getLogger(__name__)


@dataclass
class SubmitClientResponseCommand(Command[OperationResult[SessionDto]]):
    """Command to submit a user's response to a pending client action.

    Attributes:
        session_id: The session to submit the response to
        tool_call_id: The tool call ID being responded to
        response: The user's response data (schema depends on widget type)
        user_info: User information from authentication
    """

    session_id: str
    tool_call_id: str
    response: Any
    user_info: dict[str, Any] | None = None


class SubmitClientResponseCommandHandler(
    CommandHandlerBase,
    CommandHandler[SubmitClientResponseCommand, OperationResult[SessionDto]],
):
    """Handle client response submission.

    This handler:
    1. Validates the session exists and belongs to the user
    2. Validates the session has a matching pending action
    3. Submits the response to the session aggregate
    4. Persists the updated session state
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

    async def handle_async(self, request: SubmitClientResponseCommand) -> OperationResult[SessionDto]:
        """Handle submit client response command."""
        command = request
        user_info = command.user_info or {}

        # Get user ID
        user_id = user_info.get("sub") or user_info.get("user_id") or user_info.get("preferred_username")

        log.debug(f"Submitting response for session {command.session_id}, tool_call_id: {command.tool_call_id}")

        # 1. Get the session
        session = await self.session_repository.get_async(command.session_id)
        if session is None:
            return self.not_found(Session, command.session_id)

        # 2. Verify user owns the session
        if user_id and session.state.user_id != user_id:
            return self.forbidden("You don't have access to this session")

        # 3. Check session can accept response
        if not session.can_accept_response():
            return self.bad_request(f"Session cannot accept response in status {session.state.status.value}")

        # 4. Verify tool_call_id matches pending action
        pending_action = session.get_pending_action()
        if pending_action is None:
            return self.bad_request("No pending action to respond to")

        if pending_action.tool_call_id != command.tool_call_id:
            return self.bad_request(f"Response tool_call_id {command.tool_call_id} does not match pending action {pending_action.tool_call_id}")

        # 5. Create the client response
        client_response = ClientResponse(
            tool_call_id=command.tool_call_id,
            response=command.response,
            timestamp=datetime.now(UTC),
            validation_status=ValidationStatus.VALID,  # TODO: Add validation logic
            validation_errors=None,
        )

        # 6. Submit the response to the session
        try:
            session.submit_response(client_response)
        except DomainError as e:
            log.warning(f"Domain error submitting response: {e}")
            return self.bad_request(str(e))

        # 7. Update the session
        await self.session_repository.update_async(session)
        log.info(f"Response submitted for session {session.id()}, tool_call_id: {command.tool_call_id}")

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
