"""AgentDefinition DTO for read model projections.

AgentDefinitionDto is the queryable read model representation of AgentDefinition.
Used by MotorRepository for LINQ-style queries via query_async().

The DTO mirrors the domain model but is decorated with @queryable to enable
MongoDB query capabilities through Neuroglia's data infrastructure.

Note: Proactive/reactive behavior is determined by the linked ConversationTemplate,
not by the AgentDefinition itself. Agents without templates are always reactive.
"""

import datetime
from dataclasses import dataclass, field

from neuroglia.data.abstractions import Identifiable, queryable


@queryable
@dataclass
class AgentDefinitionDto(Identifiable[str]):
    """Read model DTO for AgentDefinition entity.

    This DTO is used for:
    - MongoDB read operations via MotorRepository
    - API responses (list/detail views)
    - Query projections in CQRS queries

    Proactive vs reactive behavior is determined by the linked ConversationTemplate.
    Agents without a template are always reactive (user speaks first).

    Attributes:
        id: Unique identifier (slug like "evaluator" or UUID). Immutable after creation.
        owner_user_id: User who created it (None = system-defined)
        name: Display name
        description: Longer description for UI
        icon: Bootstrap icon class (e.g., "bi-chat-dots")
        system_prompt: LLM system prompt (required)
        tools: List of available MCP tool IDs
        model: LLM model override (None = use default)
        allow_model_selection: Allow users to change model during conversation
        conversation_template_id: Optional template for structured conversations
        is_public: Available to all authenticated users
        required_roles: JWT roles required for access
        required_scopes: OAuth scopes required for access
        allowed_users: Explicit allow list (None = use roles)
        created_by: User who created it
        created_at: Creation timestamp
        updated_at: Last update timestamp
        version: Version number for optimistic concurrency (incremented on update)
    """

    # Identity (immutable after creation)
    id: str

    # Ownership
    owner_user_id: str | None = None

    # Display
    name: str = ""
    description: str = ""
    icon: str | None = None

    # Behavior
    system_prompt: str = ""
    tools: list[str] = field(default_factory=list)
    model: str | None = None
    allow_model_selection: bool = True

    # Template reference
    conversation_template_id: str | None = None

    # Access Control
    is_public: bool = True
    required_roles: list[str] = field(default_factory=list)
    required_scopes: list[str] = field(default_factory=list)
    allowed_users: list[str] | None = None

    # Audit
    created_by: str = ""
    created_at: datetime.datetime | None = None
    updated_at: datetime.datetime | None = None

    # Versioning (for optimistic concurrency)
    version: int = 1

    @property
    def has_template(self) -> bool:
        """Check if this agent has a conversation template.

        Agents with templates may be proactive (depending on template settings).
        Agents without templates are always reactive (user speaks first).
        """
        return self.conversation_template_id is not None

    @property
    def is_system_owned(self) -> bool:
        """Check if this is a system-owned definition."""
        return self.owner_user_id is None

    def to_dict(self) -> dict:
        """Convert to dictionary for MongoDB storage."""
        from typing import Any

        result: dict[str, Any] = {
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
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "AgentDefinitionDto":
        """Create from dictionary (MongoDB document or YAML).

        Args:
            data: Dictionary containing AgentDefinition fields

        Returns:
            AgentDefinitionDto instance
        """
        created_at = data.get("created_at")
        updated_at = data.get("updated_at")

        # Handle datetime parsing
        if isinstance(created_at, str):
            created_at = datetime.datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        if isinstance(updated_at, str):
            updated_at = datetime.datetime.fromisoformat(updated_at.replace("Z", "+00:00"))

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
            created_at=created_at,
            updated_at=updated_at,
            version=data.get("version", 1),
        )
