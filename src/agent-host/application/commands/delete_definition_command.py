"""Delete AgentDefinition command with handler.

This command deletes an AgentDefinition from the repository.
Only admins should have access to this command (enforced at controller level).
"""

import logging
from dataclasses import dataclass
from typing import Any

from neuroglia.core import OperationResult
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_bus import CloudEventBus
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import CloudEventPublishingOptions
from neuroglia.mapping import Mapper
from neuroglia.mediation import Command, CommandHandler, Mediator

from application.commands.command_handler_base import CommandHandlerBase
from domain.models.agent_definition import AgentDefinition
from domain.repositories import DefinitionRepository

log = logging.getLogger(__name__)


@dataclass
class DeleteDefinitionCommand(Command[OperationResult[bool]]):
    """Command to delete an AgentDefinition.

    Attributes:
        id: The ID of the definition to delete
        version: Optional version for optimistic concurrency check
        force: If True, skip concurrency check and delete regardless
        user_info: Authenticated user performing the action
    """

    id: str
    version: int | None = None
    force: bool = False
    user_info: dict[str, Any] | None = None


class DeleteDefinitionCommandHandler(
    CommandHandlerBase,
    CommandHandler[DeleteDefinitionCommand, OperationResult[bool]],
):
    """Handler for DeleteDefinitionCommand."""

    def __init__(
        self,
        mediator: Mediator,
        mapper: Mapper,
        cloud_event_bus: CloudEventBus,
        cloud_event_publishing_options: CloudEventPublishingOptions,
        definition_repository: DefinitionRepository,
    ):
        super().__init__(
            mediator,
            mapper,
            cloud_event_bus,
            cloud_event_publishing_options,
        )
        self._repository = definition_repository

    async def handle_async(self, command: DeleteDefinitionCommand) -> OperationResult[bool]:
        """Handle the delete definition command.

        Validates the definition exists and optionally checks version.
        """
        user_info = command.user_info or {}
        user_id = user_info.get("sub") or user_info.get("user_id") or "unknown"

        # Validate ID
        if not command.id or not command.id.strip():
            return self.bad_request("ID is required")

        definition_id = command.id.strip()

        # Fetch existing definition
        existing = await self._repository.get_async(definition_id)
        if existing is None:
            return self.not_found(AgentDefinition, definition_id)

        # Optimistic concurrency check (if version provided and not forcing)
        if not command.force and command.version is not None:
            if existing.version != command.version:
                return self.conflict(
                    f"Version mismatch. Expected version {command.version}, but current version is {existing.version}. The definition was modified by another user. Please refresh and try again."
                )

        try:
            # Delete from repository
            await self._repository.remove_async(definition_id)

            log.info(f"Deleted AgentDefinition: {definition_id} by user {user_id}")
            return self.ok(True)

        except Exception as e:
            log.error(f"Failed to delete AgentDefinition {definition_id}: {e}")
            return self.internal_server_error(str(e))
