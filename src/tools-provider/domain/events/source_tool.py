"""Domain events for SourceTool aggregate.

These events represent state changes in the SourceTool lifecycle,
enabling individual endpoint management within upstream sources.

Design:
- SourceTool is discovered during inventory sync
- Admins can enable/disable individual tools
- Tools can be deprecated when removed from upstream spec
- Definition updates track spec changes
"""

from dataclasses import dataclass
from datetime import datetime

from neuroglia.data.abstractions import DomainEvent
from neuroglia.eventing.cloud_events.decorators import cloudevent


@cloudevent("tool.discovered.v1")
@dataclass
class SourceToolDiscoveredDomainEvent(DomainEvent):
    """Event raised when a tool is discovered during inventory sync.

    This creates the SourceTool aggregate for the first time.
    Tool ID format: "{source_id}:{operation_id}" or "{source_id}:{tool_name}"
    """

    aggregate_id: str  # tool_id
    source_id: str
    tool_name: str
    operation_id: str
    definition: dict  # Serialized ToolDefinition
    definition_hash: str
    discovered_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        source_id: str,
        tool_name: str,
        operation_id: str,
        definition: dict,
        definition_hash: str,
        discovered_at: datetime,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.source_id = source_id
        self.tool_name = tool_name
        self.operation_id = operation_id
        self.definition = definition
        self.definition_hash = definition_hash
        self.discovered_at = discovered_at


@cloudevent("tool.enabled.v1")
@dataclass
class SourceToolEnabledDomainEvent(DomainEvent):
    """Event raised when an admin enables a tool.

    Only enabled tools can be included in ToolGroups.
    """

    aggregate_id: str
    enabled_by: str | None
    enabled_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        enabled_at: datetime,
        enabled_by: str | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.enabled_at = enabled_at
        self.enabled_by = enabled_by


@cloudevent("tool.disabled.v1")
@dataclass
class SourceToolDisabledDomainEvent(DomainEvent):
    """Event raised when an admin disables a tool.

    Disabled tools are excluded from all ToolGroups regardless of selectors.
    """

    aggregate_id: str
    disabled_by: str | None
    reason: str | None
    disabled_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        disabled_at: datetime,
        disabled_by: str | None = None,
        reason: str | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.disabled_at = disabled_at
        self.disabled_by = disabled_by
        self.reason = reason


@cloudevent("tool.definition.updated.v1")
@dataclass
class SourceToolDefinitionUpdatedDomainEvent(DomainEvent):
    """Event raised when a tool's definition changes during inventory refresh.

    Tracks schema changes, description updates, etc.
    """

    aggregate_id: str
    old_definition_hash: str
    new_definition: dict  # Serialized ToolDefinition
    new_definition_hash: str
    updated_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        old_definition_hash: str,
        new_definition: dict,
        new_definition_hash: str,
        updated_at: datetime,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.old_definition_hash = old_definition_hash
        self.new_definition = new_definition
        self.new_definition_hash = new_definition_hash
        self.updated_at = updated_at


@cloudevent("tool.deprecated.v1")
@dataclass
class SourceToolDeprecatedDomainEvent(DomainEvent):
    """Event raised when a tool is no longer present in the source inventory.

    The tool is soft-deleted but retained for audit purposes.
    """

    aggregate_id: str
    deprecated_at: datetime
    last_seen_at: datetime | None

    def __init__(
        self,
        aggregate_id: str,
        deprecated_at: datetime,
        last_seen_at: datetime | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.deprecated_at = deprecated_at
        self.last_seen_at = last_seen_at


@cloudevent("tool.restored.v1")
@dataclass
class SourceToolRestoredDomainEvent(DomainEvent):
    """Event raised when a deprecated tool reappears in the source inventory.

    Handles the case where a tool was temporarily removed from a spec.
    """

    aggregate_id: str
    new_definition: dict
    new_definition_hash: str
    restored_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        new_definition: dict,
        new_definition_hash: str,
        restored_at: datetime,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.new_definition = new_definition
        self.new_definition_hash = new_definition_hash
        self.restored_at = restored_at


@cloudevent("tool.deleted.v1")
@dataclass
class SourceToolDeletedDomainEvent(DomainEvent):
    """Event raised when an admin permanently deletes a tool.

    This is a hard delete operation that removes the tool from the system.
    Different from deprecation (soft delete from upstream) - this is an
    intentional admin action to remove the tool completely.
    """

    aggregate_id: str
    deleted_at: datetime
    deleted_by: str | None
    reason: str | None

    def __init__(
        self,
        aggregate_id: str,
        deleted_at: datetime,
        deleted_by: str | None = None,
        reason: str | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.deleted_at = deleted_at
        self.deleted_by = deleted_by
        self.reason = reason


@cloudevent("tool.label_added.v1")
@dataclass
class LabelAddedToToolDomainEvent(DomainEvent):
    """Event raised when a label is added to a tool."""

    aggregate_id: str  # tool_id
    label_id: str
    added_by: str | None
    added_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        label_id: str,
        added_at: datetime,
        added_by: str | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.label_id = label_id
        self.added_at = added_at
        self.added_by = added_by


@cloudevent("tool.label_removed.v1")
@dataclass
class LabelRemovedFromToolDomainEvent(DomainEvent):
    """Event raised when a label is removed from a tool."""

    aggregate_id: str  # tool_id
    label_id: str
    removed_by: str | None
    removed_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        label_id: str,
        removed_at: datetime,
        removed_by: str | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.label_id = label_id
        self.removed_at = removed_at
        self.removed_by = removed_by


@cloudevent("tool.updated.v1")
@dataclass
class SourceToolUpdatedDomainEvent(DomainEvent):
    """Event raised when an admin updates a tool's display name or description.

    This allows admins to override low-quality auto-discovered values from
    upstream OpenAPI specs without modifying the source.
    """

    aggregate_id: str  # tool_id
    tool_name: str | None  # New display name (None if not changed)
    description: str | None  # New description (None if not changed)
    updated_by: str | None
    updated_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        updated_at: datetime,
        tool_name: str | None = None,
        description: str | None = None,
        updated_by: str | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.tool_name = tool_name
        self.description = description
        self.updated_by = updated_by
        self.updated_at = updated_at
