"""AgentDefinition domain events.

Events emitted by the AgentDefinition aggregate to capture state changes.
These are persisted to EventStoreDB and can be used for:
- Event sourcing (rebuilding state)
- Projections (updating read models)
- Integration events (notifying other services)

AgentDefinition is a first-class aggregate that defines agent behavior:
- System prompt and LLM configuration
- Available tools
- Reference to ConversationTemplate (for proactive agents)
- Access control settings
"""

from dataclasses import dataclass
from datetime import UTC, datetime

from neuroglia.data.abstractions import DomainEvent
from neuroglia.eventing.cloud_events.decorators import cloudevent

# =============================================================================
# LIFECYCLE EVENTS
# =============================================================================


@cloudevent("agent.definition.created.v1")
@dataclass
class AgentDefinitionCreatedDomainEvent(DomainEvent):
    """Emitted when a new agent definition is created."""

    aggregate_id: str
    owner_user_id: str | None
    name: str
    description: str
    icon: str | None
    system_prompt: str
    tools: list[str]
    model: str | None
    allow_model_selection: bool
    conversation_template_id: str | None
    is_public: bool
    required_roles: list[str]
    required_scopes: list[str]
    allowed_users: list[str] | None
    created_by: str
    created_at: datetime
    updated_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        name: str,
        system_prompt: str,
        owner_user_id: str | None = None,
        description: str = "",
        icon: str | None = None,
        tools: list[str] | None = None,
        model: str | None = None,
        allow_model_selection: bool = True,
        conversation_template_id: str | None = None,
        is_public: bool = True,
        required_roles: list[str] | None = None,
        required_scopes: list[str] | None = None,
        allowed_users: list[str] | None = None,
        created_by: str = "",
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.owner_user_id = owner_user_id
        self.name = name
        self.description = description
        self.icon = icon
        self.system_prompt = system_prompt
        self.tools = tools or []
        self.model = model
        self.allow_model_selection = allow_model_selection
        self.conversation_template_id = conversation_template_id
        self.is_public = is_public
        self.required_roles = required_roles or []
        self.required_scopes = required_scopes or []
        self.allowed_users = allowed_users
        self.created_by = created_by
        self.created_at = created_at or datetime.now(UTC)
        self.updated_at = updated_at or datetime.now(UTC)


@cloudevent("agent.definition.updated.v1")
@dataclass
class AgentDefinitionUpdatedDomainEvent(DomainEvent):
    """Emitted when an agent definition is updated (general update)."""

    aggregate_id: str
    name: str | None
    description: str | None
    icon: str | None
    system_prompt: str | None
    tools: list[str] | None
    model: str | None
    allow_model_selection: bool | None
    conversation_template_id: str | None
    is_public: bool | None
    required_roles: list[str] | None
    required_scopes: list[str] | None
    allowed_users: list[str] | None
    updated_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        name: str | None = None,
        description: str | None = None,
        icon: str | None = None,
        system_prompt: str | None = None,
        tools: list[str] | None = None,
        model: str | None = None,
        allow_model_selection: bool | None = None,
        conversation_template_id: str | None = None,
        is_public: bool | None = None,
        required_roles: list[str] | None = None,
        required_scopes: list[str] | None = None,
        allowed_users: list[str] | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.name = name
        self.description = description
        self.icon = icon
        self.system_prompt = system_prompt
        self.tools = tools
        self.model = model
        self.allow_model_selection = allow_model_selection
        self.conversation_template_id = conversation_template_id
        self.is_public = is_public
        self.required_roles = required_roles
        self.required_scopes = required_scopes
        self.allowed_users = allowed_users
        self.updated_at = updated_at or datetime.now(UTC)


@cloudevent("agent.definition.deleted.v1")
@dataclass
class AgentDefinitionDeletedDomainEvent(DomainEvent):
    """Emitted when an agent definition is deleted."""

    aggregate_id: str
    deleted_at: datetime
    deleted_by: str | None

    def __init__(
        self,
        aggregate_id: str,
        deleted_by: str | None = None,
        deleted_at: datetime | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.deleted_by = deleted_by
        self.deleted_at = deleted_at or datetime.now(UTC)


# =============================================================================
# SPECIFIC UPDATE EVENTS
# =============================================================================


@cloudevent("agent.definition.name.updated.v1")
@dataclass
class AgentDefinitionNameUpdatedDomainEvent(DomainEvent):
    """Emitted when an agent definition's name is updated."""

    aggregate_id: str
    new_name: str
    updated_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        new_name: str,
        updated_at: datetime | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.new_name = new_name
        self.updated_at = updated_at or datetime.now(UTC)


@cloudevent("agent.definition.system_prompt.updated.v1")
@dataclass
class AgentDefinitionSystemPromptUpdatedDomainEvent(DomainEvent):
    """Emitted when an agent definition's system prompt is updated."""

    aggregate_id: str
    new_system_prompt: str
    updated_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        new_system_prompt: str,
        updated_at: datetime | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.new_system_prompt = new_system_prompt
        self.updated_at = updated_at or datetime.now(UTC)


@cloudevent("agent.definition.tools.updated.v1")
@dataclass
class AgentDefinitionToolsUpdatedDomainEvent(DomainEvent):
    """Emitted when an agent definition's tools list is updated."""

    aggregate_id: str
    new_tools: list[str]
    updated_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        new_tools: list[str],
        updated_at: datetime | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.new_tools = new_tools
        self.updated_at = updated_at or datetime.now(UTC)


@cloudevent("agent.definition.template.linked.v1")
@dataclass
class AgentDefinitionTemplateLinkUpdatedDomainEvent(DomainEvent):
    """Emitted when an agent definition's conversation template link is updated."""

    aggregate_id: str
    old_template_id: str | None
    new_template_id: str | None
    updated_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        new_template_id: str | None,
        old_template_id: str | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.old_template_id = old_template_id
        self.new_template_id = new_template_id
        self.updated_at = updated_at or datetime.now(UTC)


@cloudevent("agent.definition.access.updated.v1")
@dataclass
class AgentDefinitionAccessUpdatedDomainEvent(DomainEvent):
    """Emitted when an agent definition's access control settings are updated."""

    aggregate_id: str
    is_public: bool | None
    required_roles: list[str] | None
    required_scopes: list[str] | None
    allowed_users: list[str] | None
    updated_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        is_public: bool | None = None,
        required_roles: list[str] | None = None,
        required_scopes: list[str] | None = None,
        allowed_users: list[str] | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.is_public = is_public
        self.required_roles = required_roles
        self.required_scopes = required_scopes
        self.allowed_users = allowed_users
        self.updated_at = updated_at or datetime.now(UTC)
