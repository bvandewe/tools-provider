"""Session DTO for read model projections."""

import datetime
from dataclasses import dataclass, field
from typing import Any

from neuroglia.data.abstractions import Identifiable, queryable


@queryable
@dataclass
class SessionDto(Identifiable[str]):
    """Read model DTO for Session aggregate.

    This DTO represents the Session for read operations and
    is stored in MongoDB as the read model projection.
    """

    # Identity
    id: str
    user_id: str
    conversation_id: str

    # Configuration
    session_type: str  # SessionType value
    control_mode: str  # ControlMode value
    system_prompt: str | None = None
    config: dict[str, Any] = field(default_factory=dict)

    # Status
    status: str = "pending"  # SessionStatus value

    # Items
    current_item_id: str | None = None
    items: list[dict[str, Any]] = field(default_factory=list)

    # UI State
    ui_state: dict[str, Any] = field(default_factory=dict)
    pending_action: dict[str, Any] | None = None

    # Audit
    created_at: datetime.datetime | None = None
    started_at: datetime.datetime | None = None
    completed_at: datetime.datetime | None = None
    terminated_reason: str | None = None
