"""Create namespace command with handler."""

import logging
import re
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
class CreateNamespaceCommand(Command[OperationResult[KnowledgeNamespaceDto]]):
    """Command to create a new knowledge namespace.

    The command will:
    1. Validate the namespace ID is a valid slug
    2. Create the KnowledgeNamespace aggregate
    3. Return the created namespace DTO
    """

    namespace_id: str
    """Unique identifier for the namespace (slug format)."""

    name: str
    """Human-readable name for the namespace."""

    description: str = ""
    """Description of the namespace (Markdown-supported)."""

    icon: str | None = None
    """Bootstrap icon class (e.g., 'bi-book')."""

    access_level: str = "private"
    """Visibility level: 'private', 'tenant', 'public'."""

    # Context
    user_info: dict[str, Any] | None = None
    """User information from authentication context."""


class CreateNamespaceCommandHandler(CommandHandlerBase, CommandHandler[CreateNamespaceCommand, OperationResult[KnowledgeNamespaceDto]]):
    """Handler for CreateNamespaceCommand."""

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

    async def handle_async(self, command: CreateNamespaceCommand) -> OperationResult[KnowledgeNamespaceDto]:
        """Handle the create namespace command.

        Args:
            command: The command to handle

        Returns:
            OperationResult containing the created namespace DTO or error
        """
        log.info(f"Creating namespace: {command.namespace_id}")

        # Validate namespace ID format (slug)
        if not self._is_valid_slug(command.namespace_id):
            return self.bad_request("Namespace ID must be a valid slug (lowercase letters, numbers, hyphens)")

        # Check if namespace already exists
        existing = await self._repository.get_async(command.namespace_id)
        if existing is not None:
            return self.bad_request(f"A namespace with ID '{command.namespace_id}' already exists")

        # Extract user info
        owner_user_id = self._get_username(command.user_info)
        owner_tenant_id = self._get_tenant_id(command.user_info)

        # Parse access level
        try:
            access_level = AccessLevel(command.access_level)
        except ValueError:
            access_level = AccessLevel.PRIVATE

        # Create the aggregate
        namespace = KnowledgeNamespace(
            namespace_id=command.namespace_id,
            name=command.name,
            description=command.description,
            owner_user_id=owner_user_id,
            owner_tenant_id=owner_tenant_id,
            icon=command.icon,
            access_level=access_level,
        )

        # Persist the aggregate (repository handles event publishing)
        saved_namespace = await self._repository.add_async(namespace)

        # Map to DTO using inline mapping function
        dto = _map_namespace_to_dto(saved_namespace)

        log.info(f"Created namespace: {command.namespace_id}")
        return self.ok(dto)

    def _is_valid_slug(self, slug: str) -> bool:
        """Validate slug format.

        Args:
            slug: The slug to validate

        Returns:
            True if valid slug format
        """
        if not slug:
            return False
        # Slug: lowercase letters, numbers, hyphens, 3-50 chars
        pattern = r"^[a-z0-9][a-z0-9-]{1,48}[a-z0-9]$"
        return bool(re.match(pattern, slug))
