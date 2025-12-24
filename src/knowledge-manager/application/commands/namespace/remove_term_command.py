"""Remove term command with handler."""

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
from domain.entities import KnowledgeNamespace

log = logging.getLogger(__name__)


@dataclass
class RemoveTermCommand(Command[OperationResult[bool]]):
    """Command to remove a term from a namespace (soft delete)."""

    namespace_id: str
    """The namespace containing the term."""

    term_id: str
    """The term to remove."""

    # Context
    user_info: dict[str, Any] | None = None
    """User information from authentication context."""


class RemoveTermCommandHandler(CommandHandlerBase, CommandHandler[RemoveTermCommand, OperationResult[bool]]):
    """Handler for RemoveTermCommand."""

    def __init__(
        self,
        mediator: Mediator,
        mapper: Mapper,
        cloud_event_bus: CloudEventBus,
        cloud_event_publishing_options: CloudEventPublishingOptions,
        repository: Repository[KnowledgeNamespace, str],
    ):
        super().__init__(mediator, mapper, cloud_event_bus, cloud_event_publishing_options)
        self._repository = repository

    async def handle_async(self, command: RemoveTermCommand) -> OperationResult[bool]:
        """Handle the remove term command.

        Args:
            command: The command to handle

        Returns:
            OperationResult indicating success or error
        """
        log.info(f"Removing term '{command.term_id}' from namespace: {command.namespace_id}")

        # Load the aggregate
        namespace = await self._repository.get_async(command.namespace_id)
        if namespace is None:
            return self.not_found(KnowledgeNamespace, command.namespace_id)

        # Remove the term
        success = namespace.remove_term(command.term_id)
        if not success:
            return self.not_found("Term", command.term_id)

        # Persist the changes
        await self._repository.update_async(namespace)

        log.info(f"Removed term '{command.term_id}'")
        return self.ok(True)
