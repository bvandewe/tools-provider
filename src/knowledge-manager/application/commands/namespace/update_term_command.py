"""Update term command with handler."""

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
from integration.models import KnowledgeTermDto

log = logging.getLogger(__name__)


@dataclass
class UpdateTermCommand(Command[OperationResult[KnowledgeTermDto]]):
    """Command to update a term in a namespace."""

    namespace_id: str
    """The namespace containing the term."""

    term_id: str
    """The term to update."""

    term: str | None = None
    """New term name (optional)."""

    definition: str | None = None
    """New definition (optional)."""

    aliases: list[str] | None = None
    """New aliases (optional)."""

    examples: list[str] | None = None
    """New examples (optional)."""

    context_hint: str | None = None
    """New context hint (optional)."""

    # Context
    user_info: dict[str, Any] | None = None
    """User information from authentication context."""


class UpdateTermCommandHandler(CommandHandlerBase, CommandHandler[UpdateTermCommand, OperationResult[KnowledgeTermDto]]):
    """Handler for UpdateTermCommand."""

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

    async def handle_async(self, command: UpdateTermCommand) -> OperationResult[KnowledgeTermDto]:
        """Handle the update term command.

        Args:
            command: The command to handle

        Returns:
            OperationResult containing the updated term DTO or error
        """
        log.info(f"Updating term '{command.term_id}' in namespace: {command.namespace_id}")

        # Load the aggregate
        namespace = await self._repository.get_async(command.namespace_id)
        if namespace is None:
            return self.not_found(KnowledgeNamespace, command.namespace_id)

        # Check if term exists
        existing_term = namespace.get_term(command.term_id)
        if existing_term is None:
            return self.not_found("Term", command.term_id)

        # Update the term
        success = namespace.update_term(
            term_id=command.term_id,
            term=command.term,
            definition=command.definition,
            aliases=command.aliases,
            examples=command.examples,
            context_hint=command.context_hint,
        )

        if not success:
            return self.bad_request("Term could not be updated")

        # Persist the changes
        await self._repository.update_async(namespace)

        # Get the updated term
        term = namespace.get_term(command.term_id)
        if term is None:
            return self.bad_request("Term was updated but could not be retrieved")

        # Map to DTO
        dto = KnowledgeTermDto(
            id=term.id,
            namespace_id=command.namespace_id,
            term=term.term,
            definition=term.definition,
            aliases=list(term.aliases),
            examples=list(term.examples),
            context_hint=term.context_hint,
            created_at=term.created_at,
            updated_at=term.updated_at,
            is_active=term.is_active,
        )

        log.info(f"Updated term '{command.term_id}'")
        return self.ok(dto)
