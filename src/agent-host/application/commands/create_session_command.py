"""Create session command with handler.

Creates a new Session aggregate and its linked Conversation.
This is an atomic operation that ensures both are created together.
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
from domain.entities.conversation import Conversation
from domain.entities.session import Session
from domain.models.session_models import SessionConfig, SessionType
from integration.models.session_dto import SessionDto

log = logging.getLogger(__name__)


@dataclass
class CreateSessionCommand(Command[OperationResult[SessionDto]]):
    """Command to create a new session with its linked conversation.

    Attributes:
        session_type: Type of session to create
        system_prompt: Optional custom system prompt (uses default if None)
        config: Optional custom configuration (uses default if None)
        user_info: User information from authentication
    """

    session_type: SessionType
    system_prompt: str | None = None
    config: SessionConfig | None = None
    user_info: dict[str, Any] | None = None


class CreateSessionCommandHandler(
    CommandHandlerBase,
    CommandHandler[CreateSessionCommand, OperationResult[SessionDto]],
):
    """Handle session creation with linked conversation.

    This handler:
    1. Creates a new Conversation aggregate
    2. Creates a new Session aggregate linked to the conversation
    3. Optionally starts the session immediately (for proactive sessions)
    """

    def __init__(
        self,
        mediator: Mediator,
        mapper: Mapper,
        cloud_event_bus: CloudEventBus,
        cloud_event_publishing_options: CloudEventPublishingOptions,
        conversation_repository: Repository[Conversation, str],
        session_repository: Repository[Session, str],
    ):
        super().__init__(
            mediator,
            mapper,
            cloud_event_bus,
            cloud_event_publishing_options,
        )
        self.conversation_repository = conversation_repository
        self.session_repository = session_repository

    async def handle_async(self, request: CreateSessionCommand) -> OperationResult[SessionDto]:
        """Handle create session command."""
        command = request
        user_info = command.user_info or {}

        # Get user ID from various possible fields in user_info
        user_id = user_info.get("sub") or user_info.get("user_id") or user_info.get("preferred_username") or "anonymous"

        log.debug(f"Creating session for user {user_id}, type: {command.session_type.value}")

        # 1. Create the Conversation first
        conversation = Conversation(
            user_id=user_id,
            title=f"{command.session_type.value.title()} Session",
            system_prompt=command.system_prompt,
        )
        saved_conversation = await self.conversation_repository.add_async(conversation)
        log.debug(f"Created conversation {saved_conversation.id()}")

        # 2. Create the Session linked to the conversation
        session = Session(
            user_id=user_id,
            conversation_id=saved_conversation.id(),
            session_type=command.session_type,
            system_prompt=command.system_prompt,
            config=command.config,
        )

        # 3. Start the session immediately
        session.start()

        # 4. Save the session
        saved_session = await self.session_repository.add_async(session)
        log.info(f"Created and started session {saved_session.id()} of type {command.session_type.value}")

        # Map to DTO
        dto = SessionDto(
            id=saved_session.id(),
            user_id=saved_session.state.user_id,
            conversation_id=saved_session.state.conversation_id,
            session_type=saved_session.state.session_type.value,
            control_mode=saved_session.state.control_mode.value,
            system_prompt=saved_session.state.system_prompt,
            config=saved_session.state.config,
            status=saved_session.state.status.value,
            current_item_id=saved_session.state.current_item_id,
            items=saved_session.state.items,
            ui_state=saved_session.state.ui_state,
            pending_action=saved_session.state.pending_action,
            created_at=saved_session.state.created_at,
            started_at=saved_session.state.started_at,
            completed_at=saved_session.state.completed_at,
            terminated_reason=saved_session.state.terminated_reason,
        )

        return self.ok(dto)
