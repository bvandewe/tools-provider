"""Update AgentDefinition command with handler.

This command updates an existing AgentDefinition in the repository.
Uses optimistic concurrency via version field.
Only admins should have access to this command (enforced at controller level).
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from neuroglia.core import OperationResult
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_bus import CloudEventBus
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import CloudEventPublishingOptions
from neuroglia.mapping import Mapper
from neuroglia.mediation import Command, CommandHandler, Mediator

from application.commands.command_handler_base import CommandHandlerBase
from domain.models.agent_definition import AgentDefinition
from domain.repositories import DefinitionRepository
from integration.models.definition_dto import AgentDefinitionDto

log = logging.getLogger(__name__)


@dataclass
class UpdateDefinitionCommand(Command[OperationResult[AgentDefinitionDto]]):
    """Command to update an existing AgentDefinition.

    The ID is immutable - to change an ID, delete and recreate.
    Uses optimistic concurrency: provide the current version to ensure
    no concurrent modifications occurred.

    Attributes:
        id: The ID of the definition to update (immutable, for lookup only)
        version: Current version for optimistic concurrency check
        name: Updated display name
        description: Updated description
        icon: Updated icon
        system_prompt: Updated system prompt (required)
        tools: Updated tool list
        model: Updated model override
        conversation_template_id: Updated template reference
        is_public: Updated visibility
        required_roles: Updated role requirements
        required_scopes: Updated scope requirements
        allowed_users: Updated allow list
        user_info: Authenticated user performing the action

    Note:
        Proactive behavior (agent starts first) is now controlled by the
        ConversationTemplate's agent_starts_first field, not by the definition.
    """

    # Identity (for lookup - not changed)
    id: str

    # Optimistic concurrency
    version: int

    # Fields that can be updated
    name: str | None = None
    description: str | None = None
    icon: str | None = None
    system_prompt: str | None = None
    tools: list[str] | None = None
    model: str | None = None
    conversation_template_id: str | None = None
    is_public: bool | None = None
    required_roles: list[str] | None = None
    required_scopes: list[str] | None = None
    allowed_users: list[str] | None = None

    # Sentinel for explicit null (to differentiate from "not provided")
    clear_model: bool = False
    clear_template: bool = False
    clear_allowed_users: bool = False

    # User context
    user_info: dict[str, Any] | None = None


class UpdateDefinitionCommandHandler(
    CommandHandlerBase,
    CommandHandler[UpdateDefinitionCommand, OperationResult[AgentDefinitionDto]],
):
    """Handler for UpdateDefinitionCommand."""

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

    async def handle_async(self, command: UpdateDefinitionCommand) -> OperationResult[AgentDefinitionDto]:
        """Handle the update definition command.

        Validates version for optimistic concurrency and applies updates.
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

        # Optimistic concurrency check
        if existing.version != command.version:
            return self.conflict(
                f"Version mismatch. Expected version {command.version}, but current version is {existing.version}. The definition was modified by another user. Please refresh and try again."
            )

        # Apply updates (only non-None fields)
        if command.name is not None:
            if not command.name.strip():
                return self.bad_request("Name cannot be empty")
            existing.name = command.name.strip()

        if command.description is not None:
            existing.description = command.description.strip()

        if command.icon is not None:
            existing.icon = command.icon if command.icon else None

        if command.system_prompt is not None:
            if not command.system_prompt.strip():
                return self.bad_request("System prompt cannot be empty")
            existing.system_prompt = command.system_prompt.strip()

        if command.tools is not None:
            existing.tools = command.tools

        if command.clear_model:
            existing.model = None
        elif command.model is not None:
            existing.model = command.model

        if command.clear_template:
            existing.conversation_template_id = None
        elif command.conversation_template_id is not None:
            existing.conversation_template_id = command.conversation_template_id

        if command.is_public is not None:
            existing.is_public = command.is_public

        if command.required_roles is not None:
            existing.required_roles = command.required_roles

        if command.required_scopes is not None:
            existing.required_scopes = command.required_scopes

        if command.clear_allowed_users:
            existing.allowed_users = None
        elif command.allowed_users is not None:
            existing.allowed_users = command.allowed_users

        # Update audit fields
        existing.updated_at = datetime.now(UTC)
        existing.version += 1

        try:
            # Save to repository
            saved = await self._repository.update_async(existing)

            # Map to DTO for response
            dto = self.mapper.map(saved, AgentDefinitionDto)
            log.info(f"Updated AgentDefinition: {definition_id} to version {saved.version} by user {user_id}")

            return self.ok(dto)

        except Exception as e:
            log.error(f"Failed to update AgentDefinition {definition_id}: {e}")
            return self.internal_server_error(str(e))
