"""Set pending action command for updating session state.

This command sets a pending client action on a session, transitioning it
to AWAITING_CLIENT_ACTION status so it can accept client responses.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from neuroglia.core import OperationResult
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_bus import CloudEventBus
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import CloudEventPublishingOptions
from neuroglia.mapping import Mapper
from neuroglia.mediation import Command, CommandHandler, Mediator

from application.commands.command_handler_base import CommandHandlerBase
from domain.entities.session import Session
from domain.models.session_models import ClientAction

log = logging.getLogger(__name__)


@dataclass
class SetPendingActionCommand(Command[OperationResult[bool]]):
    """Command to set a pending client action on a session.

    This transitions the session to AWAITING_CLIENT_ACTION status.
    """

    session_id: str
    tool_call_id: str
    tool_name: str
    widget_type: str
    props: dict[str, Any] = field(default_factory=dict)
    lock_input: bool = True


class SetPendingActionCommandHandler(CommandHandlerBase, CommandHandler[SetPendingActionCommand, OperationResult[bool]]):
    """Handler for SetPendingActionCommand.

    Sets a pending action on a session, enabling it to accept client responses.
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

    async def handle_async(self, request: SetPendingActionCommand) -> OperationResult[bool]:
        """Handle set pending action command."""
        command = request

        log.debug(f"Setting pending action for session {command.session_id}, tool_call_id: {command.tool_call_id}")

        # 1. Get the session
        session = await self.session_repository.get_async(command.session_id)
        if session is None:
            return self.not_found(Session, command.session_id)

        # 2. Create ClientAction
        client_action = ClientAction(
            tool_call_id=command.tool_call_id,
            tool_name=command.tool_name,
            widget_type=command.widget_type,
            props=command.props,
            lock_input=command.lock_input,
        )

        # 3. Start a new session item to track this interaction
        # The item captures the agent's prompt (widget props) and will store the user's response
        try:
            agent_prompt = command.props.get("prompt", f"Widget: {command.widget_type}")
            session.start_item(agent_prompt=agent_prompt, client_action=client_action)
        except Exception as e:
            log.warning(f"Failed to start session item: {e}")
            return self.bad_request(str(e))

        # 4. Set pending action on session
        try:
            session.set_pending_action(client_action)
        except Exception as e:
            log.warning(f"Failed to set pending action: {e}")
            return self.bad_request(str(e))

        # 5. Update the session
        await self.session_repository.update_async(session)
        log.info(f"✅ Session {session.id()} pending action set: {command.tool_call_id}")

        return self.ok(True)
