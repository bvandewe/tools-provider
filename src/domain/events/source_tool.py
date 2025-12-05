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
from typing import Optional

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
    enabled_by: Optional[str]
    enabled_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        enabled_at: datetime,
        enabled_by: Optional[str] = None,
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
    disabled_by: Optional[str]
    reason: Optional[str]
    disabled_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        disabled_at: datetime,
        disabled_by: Optional[str] = None,
        reason: Optional[str] = None,
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
    last_seen_at: Optional[datetime]

    def __init__(
        self,
        aggregate_id: str,
        deprecated_at: datetime,
        last_seen_at: Optional[datetime] = None,
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
    deleted_by: Optional[str]
    reason: Optional[str]

    def __init__(
        self,
        aggregate_id: str,
        deleted_at: datetime,
        deleted_by: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.deleted_at = deleted_at
        self.deleted_by = deleted_by
        self.reason = reason
