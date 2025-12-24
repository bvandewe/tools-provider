"""Update namespace command with handler."""

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
from application.queries.namespace.get_namespaces_query import _map_namespace_to_dto
from domain.entities import KnowledgeNamespace
from domain.enums import AccessLevel
from integration.models import KnowledgeNamespaceDto

log = logging.getLogger(__name__)


@dataclass
class UpdateNamespaceCommand(Command[OperationResult[KnowledgeNamespaceDto]]):
    """Command to update a knowledge namespace."""

    namespace_id: str
    """The namespace to update."""

    name: str | None = None
    """New name (optional)."""

    description: str | None = None
    """New description (optional)."""

    icon: str | None = None
    """New icon class (optional)."""

    access_level: str | None = None
    """New access level (optional)."""

    allowed_tenant_ids: list[str] | None = None
    """New tenant allow list (optional)."""

    # Context
    user_info: dict[str, Any] | None = None
    """User information from authentication context."""


class UpdateNamespaceCommandHandler(CommandHandlerBase, CommandHandler[UpdateNamespaceCommand, OperationResult[KnowledgeNamespaceDto]]):
    """Handler for UpdateNamespaceCommand."""

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

    async def handle_async(self, command: UpdateNamespaceCommand) -> OperationResult[KnowledgeNamespaceDto]:
        """Handle the update namespace command.

        Args:
            command: The command to handle

        Returns:
            OperationResult containing the updated namespace DTO or error
        """
        log.info(f"Updating namespace: {command.namespace_id}")

        # Load the aggregate
        namespace = await self._repository.get_async(command.namespace_id)
        if namespace is None:
            return self.not_found(KnowledgeNamespace, command.namespace_id)

        # Parse access level if provided
        access_level = None
        if command.access_level is not None:
            try:
                access_level = AccessLevel(command.access_level)
            except ValueError:
                return self.bad_request("Access level must be one of: private, tenant, public")

        # Update the aggregate
        namespace.update(
            name=command.name,
            description=command.description,
            icon=command.icon,
            access_level=access_level,
            allowed_tenant_ids=command.allowed_tenant_ids,
        )

        # Persist the changes
        await self._repository.update_async(namespace)

        # Map to DTO using inline mapping function
        dto = _map_namespace_to_dto(namespace)

        log.info(f"Updated namespace: {command.namespace_id}")
        return self.ok(dto)
