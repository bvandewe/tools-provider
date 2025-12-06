"""Conversation DTO for read model projections."""

import datetime
from dataclasses import dataclass, field
from typing import Any, Optional

from neuroglia.data.abstractions import Identifiable, queryable


@queryable
@dataclass
class ConversationDto(Identifiable[str]):
    """Read model DTO for Conversation aggregate."""

    id: str
    user_id: str
    title: Optional[str] = None
    system_prompt: Optional[str] = None
    messages: list[dict[str, Any]] = field(default_factory=list)
    created_at: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None
