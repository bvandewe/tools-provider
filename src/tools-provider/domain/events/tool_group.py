"""Domain events for ToolGroup aggregate.

These events represent state changes in the ToolGroup lifecycle,
following the @cloudevent decorator pattern from existing aggregates.

ToolGroup supports both pattern-based tool selection (via selectors)
and explicit tool management (add/remove/exclude individual tools).
"""

from dataclasses import dataclass
from datetime import datetime

from neuroglia.data.abstractions import DomainEvent
from neuroglia.eventing.cloud_events.decorators import cloudevent


@cloudevent("group.created.v1")
@dataclass
class ToolGroupCreatedDomainEvent(DomainEvent):
    """Event raised when a new tool group is created."""

    aggregate_id: str
    name: str
    description: str
    created_at: datetime
    created_by: str | None

    def __init__(
        self,
        aggregate_id: str,
        name: str,
        description: str,
        created_at: datetime,
        created_by: str | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.name = name
        self.description = description
        self.created_at = created_at
        self.created_by = created_by


@cloudevent("group.updated.v1")
@dataclass
class ToolGroupUpdatedDomainEvent(DomainEvent):
    """Event raised when a tool group's name or description is updated."""

    aggregate_id: str
    name: str | None
    description: str | None
    updated_at: datetime
    updated_by: str | None

    def __init__(
        self,
        aggregate_id: str,
        updated_at: datetime,
        name: str | None = None,
        description: str | None = None,
        updated_by: str | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.name = name
        self.description = description
        self.updated_at = updated_at
        self.updated_by = updated_by


@cloudevent("group.selector.added.v1")
@dataclass
class SelectorAddedDomainEvent(DomainEvent):
    """Event raised when a pattern-based selector is added to a group."""

    aggregate_id: str
    selector: dict  # Serialized ToolSelector
    added_at: datetime
    added_by: str | None

    def __init__(
        self,
        aggregate_id: str,
        selector: dict,
        added_at: datetime,
        added_by: str | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.selector = selector
        self.added_at = added_at
        self.added_by = added_by


@cloudevent("group.selector.removed.v1")
@dataclass
class SelectorRemovedDomainEvent(DomainEvent):
    """Event raised when a selector is removed from a group."""

    aggregate_id: str
    selector_id: str
    removed_at: datetime
    removed_by: str | None

    def __init__(
        self,
        aggregate_id: str,
        selector_id: str,
        removed_at: datetime,
        removed_by: str | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.selector_id = selector_id
        self.removed_at = removed_at
        self.removed_by = removed_by


@cloudevent("group.tool.added.v1")
@dataclass
class ExplicitToolAddedDomainEvent(DomainEvent):
    """Event raised when an admin explicitly adds a specific tool to a group."""

    aggregate_id: str
    tool_id: str
    added_at: datetime
    added_by: str | None

    def __init__(
        self,
        aggregate_id: str,
        tool_id: str,
        added_at: datetime,
        added_by: str | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.tool_id = tool_id
        self.added_at = added_at
        self.added_by = added_by


@cloudevent("group.tool.removed.v1")
@dataclass
class ExplicitToolRemovedDomainEvent(DomainEvent):
    """Event raised when an admin removes a specific tool from a group."""

    aggregate_id: str
    tool_id: str
    removed_at: datetime
    removed_by: str | None

    def __init__(
        self,
        aggregate_id: str,
        tool_id: str,
        removed_at: datetime,
        removed_by: str | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.tool_id = tool_id
        self.removed_at = removed_at
        self.removed_by = removed_by


@cloudevent("group.tool.excluded.v1")
@dataclass
class ToolExcludedDomainEvent(DomainEvent):
    """Event raised when a tool is explicitly excluded from a group.

    Excluded tools are not included even if they match a selector.
    """

    aggregate_id: str
    tool_id: str
    excluded_at: datetime
    excluded_by: str | None
    reason: str | None

    def __init__(
        self,
        aggregate_id: str,
        tool_id: str,
        excluded_at: datetime,
        excluded_by: str | None = None,
        reason: str | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.tool_id = tool_id
        self.excluded_at = excluded_at
        self.excluded_by = excluded_by
        self.reason = reason


@cloudevent("group.tool.included.v1")
@dataclass
class ToolIncludedDomainEvent(DomainEvent):
    """Event raised when a tool is removed from the exclusion list.

    This re-enables a previously excluded tool to be matched by selectors.
    """

    aggregate_id: str
    tool_id: str
    included_at: datetime
    included_by: str | None

    def __init__(
        self,
        aggregate_id: str,
        tool_id: str,
        included_at: datetime,
        included_by: str | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.tool_id = tool_id
        self.included_at = included_at
        self.included_by = included_by


@cloudevent("group.activated.v1")
@dataclass
class ToolGroupActivatedDomainEvent(DomainEvent):
    """Event raised when a tool group is activated."""

    aggregate_id: str
    activated_at: datetime
    activated_by: str | None

    def __init__(
        self,
        aggregate_id: str,
        activated_at: datetime,
        activated_by: str | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.activated_at = activated_at
        self.activated_by = activated_by


@cloudevent("group.deactivated.v1")
@dataclass
class ToolGroupDeactivatedDomainEvent(DomainEvent):
    """Event raised when a tool group is deactivated."""

    aggregate_id: str
    deactivated_at: datetime
    deactivated_by: str | None
    reason: str | None

    def __init__(
        self,
        aggregate_id: str,
        deactivated_at: datetime,
        deactivated_by: str | None = None,
        reason: str | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.deactivated_at = deactivated_at
        self.deactivated_by = deactivated_by
        self.reason = reason


@cloudevent("group.deleted.v1")
@dataclass
class ToolGroupDeletedDomainEvent(DomainEvent):
    """Event raised when a tool group is deleted."""

    aggregate_id: str
    deleted_at: datetime
    deleted_by: str | None

    def __init__(
        self,
        aggregate_id: str,
        deleted_at: datetime,
        deleted_by: str | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.deleted_at = deleted_at
        self.deleted_by = deleted_by
