"""Add term command with handler."""

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
from domain.entities import KnowledgeNamespace
from integration.models import KnowledgeTermDto

log = logging.getLogger(__name__)


@dataclass
class AddTermCommand(Command[OperationResult[KnowledgeTermDto]]):
    """Command to add a term to a namespace."""

    namespace_id: str
    """The namespace to add the term to."""

    term: str
    """The canonical term name."""

    definition: str
    """The definition of the term (Markdown-supported)."""

    aliases: list[str] = field(default_factory=list)
    """Alternative names for matching."""

    examples: list[str] = field(default_factory=list)
    """Usage examples."""

    context_hint: str | None = None
    """When to inject this term."""

    # Context
    user_info: dict[str, Any] | None = None
    """User information from authentication context."""


class AddTermCommandHandler(CommandHandlerBase, CommandHandler[AddTermCommand, OperationResult[KnowledgeTermDto]]):
    """Handler for AddTermCommand."""

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

    async def handle_async(self, command: AddTermCommand) -> OperationResult[KnowledgeTermDto]:
        """Handle the add term command.

        Args:
            command: The command to handle

        Returns:
            OperationResult containing the created term DTO or error
        """
        log.info(f"Adding term '{command.term}' to namespace: {command.namespace_id}")

        # Load the aggregate
        namespace = await self._repository.get_async(command.namespace_id)
        if namespace is None:
            return self.not_found(KnowledgeNamespace, command.namespace_id)

        # Validate term is not empty
        if not command.term or not command.term.strip():
            return self.bad_request("Term name cannot be empty")

        # Validate definition is not empty
        if not command.definition or not command.definition.strip():
            return self.bad_request("Definition cannot be empty")

        # Add the term
        term_id = namespace.add_term(
            term=command.term.strip(),
            definition=command.definition.strip(),
            aliases=command.aliases,
            examples=command.examples,
            context_hint=command.context_hint,
        )

        # Persist the changes
        await self._repository.update_async(namespace)

        # Get the created term
        term = namespace.get_term(term_id)
        if term is None:
            return self.bad_request("Term creation failed")

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

        log.info(f"Added term '{command.term}' with ID: {term_id}")
        return self.ok(dto)
