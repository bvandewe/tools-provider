"""Agent Definition model.

AgentDefinition is a state-based entity (stored in MongoDB, not event-sourced)
that defines agent behavior. It includes:
- System prompt for the LLM
- Available tools
- Optional conversation template (which controls conversation flow)
- Access control settings

AgentDefinitions are referenced by Conversations via definition_id.
Proactive/reactive behavior is determined by the linked ConversationTemplate,
not by the AgentDefinition itself.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from neuroglia.data.abstractions import Identifiable, queryable
from neuroglia.mapping.mapper import map_to

from integration.models.definition_dto import AgentDefinitionDto


@map_to(AgentDefinitionDto)
@queryable
@dataclass
class AgentDefinition(Identifiable[str]):
    """Template that defines agent behavior.

    This is a configuration entity, not an aggregate. It's stored in MongoDB
    and referenced by Conversations. Changes to a definition affect new
    conversations, not existing ones (immutable reference pattern).

    Proactive vs reactive behavior is determined by the linked ConversationTemplate.
    Agents without a template are always reactive (user speaks first).
    Agents with a template use the template's agent_starts_first setting.

    Attributes:
        id: Unique identifier (slug like "evaluator" or UUID). Immutable after creation.
        owner_user_id: User who created it (None = system-defined)
        name: Display name
        description: Longer description for UI
        icon: Bootstrap icon class (e.g., "bi-chat-dots")
        system_prompt: LLM system prompt (required)
        tools: List of available MCP tool IDs
        model: LLM model override (None = use default)
        conversation_template_id: Optional template for structured conversations
        is_public: Available to all authenticated users
        required_roles: JWT roles required for access
        required_scopes: OAuth scopes required for access
        allowed_users: Explicit allow list (None = use roles)
        created_by: User who created it
        created_at: Creation timestamp
        updated_at: Last update timestamp
        version: Version number for optimistic concurrency
    """

    # Identity (immutable after creation)
    id: str
    owner_user_id: str | None = None

    # Display
    name: str = ""
    description: str = ""
    icon: str | None = None

    # Behavior
    system_prompt: str = ""
    tools: list[str] = field(default_factory=list)
    model: str | None = None  # LLM model override (None = use default)

    # Template reference (for proactive/structured conversations)
    conversation_template_id: str | None = None

    # Access Control
    is_public: bool = True
    required_roles: list[str] = field(default_factory=list)
    required_scopes: list[str] = field(default_factory=list)
    allowed_users: list[str] | None = None

    # Audit
    created_by: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Versioning (for optimistic concurrency - incremented on update)
    version: int = 1

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for MongoDB storage."""
        return {
            "id": self.id,
            "owner_user_id": self.owner_user_id,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "system_prompt": self.system_prompt,
            "tools": self.tools,
            "model": self.model,
            "conversation_template_id": self.conversation_template_id,
            "is_public": self.is_public,
            "required_roles": self.required_roles,
            "required_scopes": self.required_scopes,
            "allowed_users": self.allowed_users,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentDefinition":
        """Create from dictionary (MongoDB document)."""
        created_at = data.get("created_at")
        updated_at = data.get("updated_at")

        # Handle datetime parsing
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))

        return cls(
            id=data.get("id", ""),
            owner_user_id=data.get("owner_user_id"),
            name=data.get("name", ""),
            description=data.get("description", ""),
            icon=data.get("icon"),
            system_prompt=data.get("system_prompt", ""),
            tools=data.get("tools", []),
            model=data.get("model"),
            conversation_template_id=data.get("conversation_template_id"),
            is_public=data.get("is_public", True),
            required_roles=data.get("required_roles", []),
            required_scopes=data.get("required_scopes", []),
            allowed_users=data.get("allowed_users"),
            created_by=data.get("created_by", ""),
            created_at=created_at or datetime.now(UTC),
            updated_at=updated_at or datetime.now(UTC),
            version=data.get("version", 1),
        )

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
        if self.owner_user_id == user_id:
            return True

        # Check explicit allow list
        if self.allowed_users is not None:
            return user_id in self.allowed_users

        # Public definitions available to all
        if self.is_public:
            # Check role requirements
            if self.required_roles and not any(r in user_roles for r in self.required_roles):
                return False

            # Check scope requirements
            if self.required_scopes and not any(s in user_scopes for s in self.required_scopes):
                return False

            return True

        return False

    @property
    def has_template(self) -> bool:
        """Check if this agent has a conversation template.

        Agents with templates may be proactive (depending on template settings).
        Agents without templates are always reactive (user speaks first).
        """
        return self.conversation_template_id is not None


# =============================================================================
# DEFAULT AGENT DEFINITIONS
# =============================================================================

DEFAULT_REACTIVE_AGENT = AgentDefinition(
    id="default-chat",
    name="Chat Assistant",
    description="A helpful AI assistant for general conversations",
    icon="bi-chat-dots",
    system_prompt="You are a helpful AI assistant. Be concise but thorough in your responses.",
    is_public=True,
)

# Note: Proactive agents require a ConversationTemplate with agent_starts_first=True.
# There is no DEFAULT_PROACTIVE_AGENT because proactive behavior is template-driven.
