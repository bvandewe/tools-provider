"""AgentDefinition aggregate definition using the AggregateState pattern.

DomainEvents are appended/aggregated in the AgentDefinition and the
repository publishes them via Mediator after the AgentDefinition was persisted.

AgentDefinition is a first-class AggregateRoot that defines agent behavior:
- System prompt and LLM configuration
- Available tools
- Reference to ConversationTemplate (for proactive agents)
- Access control settings

This replaces the previous state-based dataclass in domain/models/.
"""

from datetime import UTC, datetime
from typing import Any, cast
from uuid import uuid4

from multipledispatch import dispatch
from neuroglia.data.abstractions import AggregateRoot, AggregateState
from neuroglia.mapping.mapper import map_to

from domain.events.agent_definition import (
    AgentDefinitionAccessUpdatedDomainEvent,
    AgentDefinitionCreatedDomainEvent,
    AgentDefinitionDeletedDomainEvent,
    AgentDefinitionNameUpdatedDomainEvent,
    AgentDefinitionSystemPromptUpdatedDomainEvent,
    AgentDefinitionTemplateLinkUpdatedDomainEvent,
    AgentDefinitionToolsUpdatedDomainEvent,
    AgentDefinitionUpdatedDomainEvent,
)
from integration.models.definition_dto import AgentDefinitionDto


@map_to(AgentDefinitionDto)
class AgentDefinitionState(AggregateState[str]):
    """Encapsulates the persisted state for the AgentDefinition aggregate.

    This state is rebuilt from events (event sourcing).
    """

    # Identity
    id: str
    owner_user_id: str | None

    # Display
    name: str
    description: str
    icon: str | None

    # Behavior
    system_prompt: str
    tools: list[str]
    model: str | None

    # Template reference (for proactive/structured conversations)
    conversation_template_id: str | None

    # Access Control
    is_public: bool
    required_roles: list[str]
    required_scopes: list[str]
    allowed_users: list[str] | None

    # Audit
    created_by: str
    created_at: datetime
    updated_at: datetime

    # Versioning (for optimistic concurrency)
    version: int

    def __init__(self) -> None:
        super().__init__()
        self.id = ""
        self.owner_user_id = None
        self.name = ""
        self.description = ""
        self.icon = None
        self.system_prompt = ""
        self.tools = []
        self.model = None
        self.conversation_template_id = None
        self.is_public = True
        self.required_roles = []
        self.required_scopes = []
        self.allowed_users = None
        self.created_by = ""
        now = datetime.now(UTC)
        self.created_at = now
        self.updated_at = now
        self.version = 1

    @dispatch(AgentDefinitionCreatedDomainEvent)
    def on(self, event: AgentDefinitionCreatedDomainEvent) -> None:  # type: ignore[override]
        """Apply the creation event to the state."""
        self.id = event.aggregate_id
        self.owner_user_id = event.owner_user_id
        self.name = event.name
        self.description = event.description
        self.icon = event.icon
        self.system_prompt = event.system_prompt
        self.tools = event.tools.copy() if event.tools else []
        self.model = event.model
        self.conversation_template_id = event.conversation_template_id
        self.is_public = event.is_public
        self.required_roles = event.required_roles.copy() if event.required_roles else []
        self.required_scopes = event.required_scopes.copy() if event.required_scopes else []
        self.allowed_users = event.allowed_users.copy() if event.allowed_users else None
        self.created_by = event.created_by
        self.created_at = event.created_at
        self.updated_at = event.updated_at

    @dispatch(AgentDefinitionUpdatedDomainEvent)
    def on(self, event: AgentDefinitionUpdatedDomainEvent) -> None:  # type: ignore[override]
        """Apply a general update event to the state."""
        if event.name is not None:
            self.name = event.name
        if event.description is not None:
            self.description = event.description
        if event.icon is not None:
            self.icon = event.icon
        if event.system_prompt is not None:
            self.system_prompt = event.system_prompt
        if event.tools is not None:
            self.tools = event.tools.copy()
        if event.model is not None:
            self.model = event.model
        if event.conversation_template_id is not None:
            self.conversation_template_id = event.conversation_template_id
        if event.is_public is not None:
            self.is_public = event.is_public
        if event.required_roles is not None:
            self.required_roles = event.required_roles.copy()
        if event.required_scopes is not None:
            self.required_scopes = event.required_scopes.copy()
        if event.allowed_users is not None:
            self.allowed_users = event.allowed_users.copy() if event.allowed_users else None
        self.updated_at = event.updated_at
        self.version += 1

    @dispatch(AgentDefinitionNameUpdatedDomainEvent)
    def on(self, event: AgentDefinitionNameUpdatedDomainEvent) -> None:  # type: ignore[override]
        """Apply the name updated event to the state."""
        self.name = event.new_name
        self.updated_at = event.updated_at
        self.version += 1

    @dispatch(AgentDefinitionSystemPromptUpdatedDomainEvent)
    def on(self, event: AgentDefinitionSystemPromptUpdatedDomainEvent) -> None:  # type: ignore[override]
        """Apply the system prompt updated event to the state."""
        self.system_prompt = event.new_system_prompt
        self.updated_at = event.updated_at
        self.version += 1

    @dispatch(AgentDefinitionToolsUpdatedDomainEvent)
    def on(self, event: AgentDefinitionToolsUpdatedDomainEvent) -> None:  # type: ignore[override]
        """Apply the tools updated event to the state."""
        self.tools = event.new_tools.copy() if event.new_tools else []
        self.updated_at = event.updated_at
        self.version += 1

    @dispatch(AgentDefinitionTemplateLinkUpdatedDomainEvent)
    def on(self, event: AgentDefinitionTemplateLinkUpdatedDomainEvent) -> None:  # type: ignore[override]
        """Apply the template link updated event to the state."""
        self.conversation_template_id = event.new_template_id
        self.updated_at = event.updated_at
        self.version += 1

    @dispatch(AgentDefinitionAccessUpdatedDomainEvent)
    def on(self, event: AgentDefinitionAccessUpdatedDomainEvent) -> None:  # type: ignore[override]
        """Apply the access updated event to the state."""
        if event.is_public is not None:
            self.is_public = event.is_public
        if event.required_roles is not None:
            self.required_roles = event.required_roles.copy()
        if event.required_scopes is not None:
            self.required_scopes = event.required_scopes.copy()
        if event.allowed_users is not None:
            self.allowed_users = event.allowed_users.copy() if event.allowed_users else None
        self.updated_at = event.updated_at
        self.version += 1

    @dispatch(AgentDefinitionDeletedDomainEvent)
    def on(self, event: AgentDefinitionDeletedDomainEvent) -> None:  # type: ignore[override]
        """Apply the deleted event to the state."""
        self.updated_at = event.deleted_at
        # Note: Actual deletion handled by repository


class AgentDefinition(AggregateRoot[AgentDefinitionState, str]):
    """AgentDefinition aggregate root following the AggregateState pattern.

    Represents the configuration that defines agent behavior.
    All state changes are captured as domain events.
    """

    def __init__(
        self,
        name: str,
        system_prompt: str,
        definition_id: str | None = None,
        owner_user_id: str | None = None,
        description: str = "",
        icon: str | None = None,
        tools: list[str] | None = None,
        model: str | None = None,
        conversation_template_id: str | None = None,
        is_public: bool = True,
        required_roles: list[str] | None = None,
        required_scopes: list[str] | None = None,
        allowed_users: list[str] | None = None,
        created_by: str = "",
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        super().__init__()
        aggregate_id = definition_id or str(uuid4())
        created_time = created_at or datetime.now(UTC)
        updated_time = updated_at or created_time

        self.state.on(
            self.register_event(  # type: ignore
                AgentDefinitionCreatedDomainEvent(
                    aggregate_id=aggregate_id,
                    owner_user_id=owner_user_id,
                    name=name,
                    description=description,
                    icon=icon,
                    system_prompt=system_prompt,
                    tools=tools or [],
                    model=model,
                    conversation_template_id=conversation_template_id,
                    is_public=is_public,
                    required_roles=required_roles or [],
                    required_scopes=required_scopes or [],
                    allowed_users=allowed_users,
                    created_by=created_by,
                    created_at=created_time,
                    updated_at=updated_time,
                )
            )
        )

    def id(self) -> str:
        """Return the aggregate identifier with a precise type."""
        aggregate_id = super().id()
        if aggregate_id is None:
            raise ValueError("AgentDefinition aggregate identifier has not been initialized")
        return cast(str, aggregate_id)

    # =========================================================================
    # UPDATE METHODS
    # =========================================================================

    def update(
        self,
        name: str | None = None,
        description: str | None = None,
        icon: str | None = None,
        system_prompt: str | None = None,
        tools: list[str] | None = None,
        model: str | None = None,
        conversation_template_id: str | None = None,
        is_public: bool | None = None,
        required_roles: list[str] | None = None,
        required_scopes: list[str] | None = None,
        allowed_users: list[str] | None = None,
    ) -> bool:
        """Apply a general update to the agent definition."""
        # Only emit event if at least one field is provided
        if all(v is None for v in [name, description, icon, system_prompt, tools, model, conversation_template_id, is_public, required_roles, required_scopes, allowed_users]):
            return False

        self.state.on(
            self.register_event(  # type: ignore
                AgentDefinitionUpdatedDomainEvent(
                    aggregate_id=self.id(),
                    name=name,
                    description=description,
                    icon=icon,
                    system_prompt=system_prompt,
                    tools=tools,
                    model=model,
                    conversation_template_id=conversation_template_id,
                    is_public=is_public,
                    required_roles=required_roles,
                    required_scopes=required_scopes,
                    allowed_users=allowed_users,
                )
            )
        )
        return True

    def update_name(self, new_name: str) -> bool:
        """Update the agent definition name."""
        if self.state.name == new_name:
            return False
        self.state.on(
            self.register_event(  # type: ignore
                AgentDefinitionNameUpdatedDomainEvent(
                    aggregate_id=self.id(),
                    new_name=new_name,
                )
            )
        )
        return True

    def update_system_prompt(self, new_system_prompt: str) -> bool:
        """Update the system prompt."""
        if self.state.system_prompt == new_system_prompt:
            return False
        self.state.on(
            self.register_event(  # type: ignore
                AgentDefinitionSystemPromptUpdatedDomainEvent(
                    aggregate_id=self.id(),
                    new_system_prompt=new_system_prompt,
                )
            )
        )
        return True

    def update_tools(self, new_tools: list[str]) -> bool:
        """Update the available tools list."""
        if self.state.tools == new_tools:
            return False
        self.state.on(
            self.register_event(  # type: ignore
                AgentDefinitionToolsUpdatedDomainEvent(
                    aggregate_id=self.id(),
                    new_tools=new_tools,
                )
            )
        )
        return True

    def link_template(self, template_id: str | None) -> bool:
        """Link or unlink a conversation template."""
        if self.state.conversation_template_id == template_id:
            return False
        old_template_id = self.state.conversation_template_id
        self.state.on(
            self.register_event(  # type: ignore
                AgentDefinitionTemplateLinkUpdatedDomainEvent(
                    aggregate_id=self.id(),
                    old_template_id=old_template_id,
                    new_template_id=template_id,
                )
            )
        )
        return True

    def update_access(
        self,
        is_public: bool | None = None,
        required_roles: list[str] | None = None,
        required_scopes: list[str] | None = None,
        allowed_users: list[str] | None = None,
    ) -> bool:
        """Update access control settings."""
        if all(v is None for v in [is_public, required_roles, required_scopes, allowed_users]):
            return False
        self.state.on(
            self.register_event(  # type: ignore
                AgentDefinitionAccessUpdatedDomainEvent(
                    aggregate_id=self.id(),
                    is_public=is_public,
                    required_roles=required_roles,
                    required_scopes=required_scopes,
                    allowed_users=allowed_users,
                )
            )
        )
        return True

    def delete(self, deleted_by: str | None = None) -> None:
        """Mark the agent definition as deleted."""
        self.state.on(
            self.register_event(  # type: ignore
                AgentDefinitionDeletedDomainEvent(
                    aggregate_id=self.id(),
                    deleted_by=deleted_by,
                )
            )
        )

    # =========================================================================
    # QUERY METHODS (delegating to state)
    # =========================================================================

    def can_access(self, user_id: str, user_roles: list[str], user_scopes: list[str]) -> bool:
        """Check if a user can access this agent definition.

        Args:
            user_id: The user's ID
            user_roles: The user's JWT roles
            user_scopes: The user's OAuth scopes

        Returns:
            True if the user can access this definition
        """
        # Owner can always access
        if self.state.owner_user_id == user_id:
            return True

        # Check explicit allow list
        if self.state.allowed_users is not None:
            return user_id in self.state.allowed_users

        # Public definitions available to all
        if self.state.is_public:
            # Check role requirements
            if self.state.required_roles and not any(r in user_roles for r in self.state.required_roles):
                return False

            # Check scope requirements
            if self.state.required_scopes and not any(s in user_scopes for s in self.state.required_scopes):
                return False

            return True

        return False

    @property
    def has_template(self) -> bool:
        """Check if this agent has a conversation template.

        Agents with templates may be proactive (depending on template settings).
        Agents without templates are always reactive (user speaks first).
        """
        return self.state.conversation_template_id is not None

    @property
    def name(self) -> str:
        """Get the agent definition name."""
        return self.state.name

    @property
    def system_prompt(self) -> str:
        """Get the system prompt."""
        return self.state.system_prompt

    @property
    def tools(self) -> list[str]:
        """Get the available tools list."""
        return self.state.tools.copy()

    @property
    def model(self) -> str | None:
        """Get the LLM model override."""
        return self.state.model

    @property
    def conversation_template_id(self) -> str | None:
        """Get the linked conversation template ID."""
        return self.state.conversation_template_id

    @property
    def icon(self) -> str | None:
        """Get the icon."""
        return self.state.icon

    @property
    def description(self) -> str:
        """Get the description."""
        return self.state.description

    @property
    def is_public(self) -> bool:
        """Check if this definition is public."""
        return self.state.is_public

    @property
    def owner_user_id(self) -> str | None:
        """Get the owner user ID."""
        return self.state.owner_user_id

    # =========================================================================
    # SERIALIZATION (for compatibility with existing code paths)
    # =========================================================================

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id(),
            "owner_user_id": self.state.owner_user_id,
            "name": self.state.name,
            "description": self.state.description,
            "icon": self.state.icon,
            "system_prompt": self.state.system_prompt,
            "tools": self.state.tools,
            "model": self.state.model,
            "conversation_template_id": self.state.conversation_template_id,
            "is_public": self.state.is_public,
            "required_roles": self.state.required_roles,
            "required_scopes": self.state.required_scopes,
            "allowed_users": self.state.allowed_users,
            "created_by": self.state.created_by,
            "created_at": self.state.created_at.isoformat() if self.state.created_at else None,
            "updated_at": self.state.updated_at.isoformat() if self.state.updated_at else None,
            "version": self.state.version,
        }


# Default reactive agent ID - used for fallback when no agent definition is found
DEFAULT_REACTIVE_AGENT_ID = "default-reactive"


def create_default_reactive_agent() -> "AgentDefinition":
    """Factory function to create the default reactive agent.

    This is used as a fallback when no specific agent definition is found.
    The default agent has no tools and a simple system prompt.
    """
    return AgentDefinition(
        definition_id=DEFAULT_REACTIVE_AGENT_ID,
        name="Default Reactive Agent",
        system_prompt="You are a helpful assistant.",
        description="The default reactive agent used when no specific agent is configured.",
        is_public=True,
        created_by="system",
    )
