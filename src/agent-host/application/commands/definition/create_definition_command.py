"""Create AgentDefinition command with handler.

This command creates a new AgentDefinition in the repository.
Only admins should have access to this command (enforced at controller level).
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from neuroglia.core import OperationResult
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_bus import CloudEventBus
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import CloudEventPublishingOptions
from neuroglia.mapping import Mapper
from neuroglia.mediation import Command, CommandHandler, Mediator

from application.commands.command_handler_base import CommandHandlerBase
from domain.entities import AgentDefinition
from integration.models.definition_dto import AgentDefinitionDto

log = logging.getLogger(__name__)


# Regex for valid slug IDs: lowercase letters, numbers, hyphens
SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$")


@dataclass
class CreateDefinitionCommand(Command[OperationResult[AgentDefinitionDto]]):
    """Command to create a new AgentDefinition.

    Attributes:
        id: Unique slug identifier (immutable after creation)
        name: Display name for the definition
        description: Longer description for UI
        icon: Bootstrap icon class (optional)
        system_prompt: LLM system prompt (required)
        tools: List of MCP tool IDs
        model: LLM model override (optional)
        conversation_template_id: Template reference for structured conversations
        is_public: Available to all authenticated users
        required_roles: JWT roles required for access
        required_scopes: OAuth scopes required for access
        allowed_users: Explicit allow list (optional)
        user_info: Authenticated user performing the action

    Note:
        Proactive behavior (agent starts first) is now controlled by the
        ConversationTemplate's agent_starts_first field, not by the definition.
        Agents without templates are always reactive.
    """

    # Required fields
    id: str
    name: str
    system_prompt: str

    # Optional fields with defaults
    description: str = ""
    icon: str | None = None
    tools: list[str] = field(default_factory=list)
    model: str | None = None
    conversation_template_id: str | None = None
    is_public: bool = True
    required_roles: list[str] = field(default_factory=list)
    required_scopes: list[str] = field(default_factory=list)
    allowed_users: list[str] | None = None

    # User context
    user_info: dict[str, Any] | None = None


class CreateDefinitionCommandHandler(
    CommandHandlerBase,
    CommandHandler[CreateDefinitionCommand, OperationResult[AgentDefinitionDto]],
):
    """Handler for CreateDefinitionCommand."""

    def __init__(
        self,
        mediator: Mediator,
        mapper: Mapper,
        cloud_event_bus: CloudEventBus,
        cloud_event_publishing_options: CloudEventPublishingOptions,
        agent_definition_repository: Repository[AgentDefinition, str],
    ):
        super().__init__(
            mediator,
            mapper,
            cloud_event_bus,
            cloud_event_publishing_options,
        )
        self._repository = agent_definition_repository

    async def handle_async(self, command: CreateDefinitionCommand) -> OperationResult[AgentDefinitionDto]:
        """Handle the create definition command.

        Validates the input and creates a new AgentDefinition in the repository.
        """
        user_info = command.user_info or {}
        user_id = user_info.get("sub") or user_info.get("user_id") or "unknown"

        # Validate ID format (must be a valid slug)
        if not command.id or not command.id.strip():
            return self.bad_request("ID is required")

        slug_id = command.id.strip().lower()
        if len(slug_id) < 2:
            return self.bad_request("ID must be at least 2 characters")

        if not SLUG_PATTERN.match(slug_id):
            return self.bad_request("ID must be a valid slug: lowercase letters, numbers, and hyphens only. Cannot start or end with a hyphen.")

        # Validate required fields
        if not command.name or not command.name.strip():
            return self.bad_request("Name is required")

        if not command.system_prompt or not command.system_prompt.strip():
            return self.bad_request("System prompt is required")

        # Check for existing definition with same ID
        existing = await self._repository.get_async(slug_id)
        if existing is not None:
            return self.conflict(f"AgentDefinition with ID '{slug_id}' already exists")

        # Create the new definition aggregate
        # Note: The aggregate constructor emits AgentDefinitionCreatedDomainEvent
        definition = AgentDefinition(
            definition_id=slug_id,
            name=command.name.strip(),
            system_prompt=command.system_prompt.strip(),
            owner_user_id=user_id,  # Admin becomes owner
            description=command.description.strip() if command.description else "",
            icon=command.icon,
            tools=command.tools or [],
            model=command.model,
            conversation_template_id=command.conversation_template_id,
            is_public=command.is_public,
            required_roles=command.required_roles or [],
            required_scopes=command.required_scopes or [],
            allowed_users=command.allowed_users,
            created_by=user_id,
        )

        try:
            # Save to repository (EventSourcingRepository publishes domain events)
            saved = await self._repository.add_async(definition)

            # Map aggregate state to DTO for response
            dto = self.mapper.map(saved.state, AgentDefinitionDto)
            log.info(f"Created AgentDefinition: {slug_id} by user {user_id}")

            return self.ok(dto)

        except Exception as e:
            log.error(f"Failed to create AgentDefinition {slug_id}: {e}")
            return self.internal_server_error(str(e))
