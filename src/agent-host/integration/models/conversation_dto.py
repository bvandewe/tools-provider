"""Conversation DTO for read model projections."""

import datetime
from dataclasses import dataclass, field
from typing import Any

from neuroglia.data.abstractions import Identifiable, queryable


@queryable
@dataclass
class ConversationDto(Identifiable[str]):
    """Read model DTO for Conversation aggregate."""

    id: str
    user_id: str
    definition_id: str = ""
    definition_name: str = "Agent"
    definition_icon: str = "bi-robot"
    title: str | None = None
    system_prompt: str | None = None
    messages: list[dict[str, Any]] = field(default_factory=list)
    message_count: int = 0
    created_at: datetime.datetime | None = None
    updated_at: datetime.datetime | None = None
