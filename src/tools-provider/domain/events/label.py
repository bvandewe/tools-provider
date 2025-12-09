"""Domain events for Label aggregate.

Labels are user-defined tags that can be applied to tools for organization
and filtering purposes. Unlike OpenAPI tags which come from source definitions,
labels are assigned by administrators and persist across tool refreshes.

Events:
- LabelCreatedDomainEvent: A new label is defined
- LabelUpdatedDomainEvent: Label name/description/color changed
- LabelDeletedDomainEvent: Label removed (triggers cascading removal from tools)
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from neuroglia.data.abstractions import DomainEvent
from neuroglia.eventing.cloud_events.decorators import cloudevent


@cloudevent("label.created.v1")
@dataclass
class LabelCreatedDomainEvent(DomainEvent):
    """Event raised when a new label is created."""

    aggregate_id: str
    name: str
    description: str
    color: str
    created_at: datetime
    created_by: Optional[str]

    def __init__(
        self,
        aggregate_id: str,
        name: str,
        description: str,
        color: str,
        created_at: datetime,
        created_by: Optional[str] = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.name = name
        self.description = description
        self.color = color
        self.created_at = created_at
        self.created_by = created_by


@cloudevent("label.updated.v1")
@dataclass
class LabelUpdatedDomainEvent(DomainEvent):
    """Event raised when a label is updated."""

    aggregate_id: str
    name: Optional[str]
    description: Optional[str]
    color: Optional[str]
    updated_at: datetime
    updated_by: Optional[str]

    def __init__(
        self,
        aggregate_id: str,
        updated_at: datetime,
        name: Optional[str] = None,
        description: Optional[str] = None,
        color: Optional[str] = None,
        updated_by: Optional[str] = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.name = name
        self.description = description
        self.color = color
        self.updated_at = updated_at
        self.updated_by = updated_by


@cloudevent("label.deleted.v1")
@dataclass
class LabelDeletedDomainEvent(DomainEvent):
    """Event raised when a label is deleted.

    This triggers cascading removal of this label from all tools.
    """

    aggregate_id: str
    deleted_at: datetime
    deleted_by: Optional[str]

    def __init__(
        self,
        aggregate_id: str,
        deleted_at: datetime,
        deleted_by: Optional[str] = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.deleted_at = deleted_at
        self.deleted_by = deleted_by
