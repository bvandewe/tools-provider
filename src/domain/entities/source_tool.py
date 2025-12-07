"""SourceTool aggregate definition using the AggregateState pattern.

This aggregate represents an individual endpoint/tool from an upstream source,
enabling granular admin control over which tools are available for inclusion
in ToolGroups.

Key Design Decisions:
1. Tool ID format: "{source_id}:{operation_id}" ensures uniqueness across sources
2. Tools are discovered automatically during inventory sync
3. Default state is ENABLED (discovered tools are available by default)
4. Disabled tools are excluded from ALL ToolGroups regardless of selectors
5. Deprecated tools are soft-deleted when removed from upstream spec

Following the UpstreamSource aggregate pattern:
- DomainEvents are registered via register_event()
- State is updated via @dispatch handlers
- Repository publishes events after persistence
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import List, Optional

from multipledispatch import dispatch
from neuroglia.data.abstractions import AggregateRoot, AggregateState

from domain.enums import ToolStatus
from domain.events.source_tool import (
    LabelAddedToToolDomainEvent,
    LabelRemovedFromToolDomainEvent,
    SourceToolDefinitionUpdatedDomainEvent,
    SourceToolDeletedDomainEvent,
    SourceToolDeprecatedDomainEvent,
    SourceToolDisabledDomainEvent,
    SourceToolDiscoveredDomainEvent,
    SourceToolEnabledDomainEvent,
    SourceToolRestoredDomainEvent,
)
from domain.models import ToolDefinition

# Forward reference for DTO mapping (will be in integration layer)
# from integration.models.source_tool_dto import SourceToolDto


# @map_to(SourceToolDto)  # Uncomment when SourceToolDto is created
class SourceToolState(AggregateState[str]):
    """Encapsulates the persisted state for the SourceTool aggregate.

    Attributes:
        id: Unique tool ID in format "{source_id}:{operation_id}"
        source_id: Reference to parent UpstreamSource
        tool_name: Human-readable tool name (from OpenAPI operationId or summary)
        operation_id: Original operationId from OpenAPI spec
        definition: The normalized ToolDefinition
        definition_hash: Hash for change detection
        is_enabled: Admin toggle - only enabled tools can be in groups
        status: ACTIVE or DEPRECATED
        discovered_at: When first seen in inventory
        last_seen_at: Last inventory sync that included this tool
        updated_at: Last state change timestamp
        enabled_by: User who enabled (if explicitly enabled)
        disabled_by: User who disabled (if explicitly disabled)
        disable_reason: Why the tool was disabled
    """

    # Identity
    id: str
    source_id: str
    tool_name: str
    operation_id: str

    # Definition
    definition: Optional[ToolDefinition]
    definition_hash: str

    # Admin control
    is_enabled: bool
    status: ToolStatus

    # Labels
    label_ids: List[str]

    # Audit trail
    discovered_at: datetime
    last_seen_at: datetime
    updated_at: datetime
    enabled_by: Optional[str]
    disabled_by: Optional[str]
    disable_reason: Optional[str]

    def __init__(self) -> None:
        super().__init__()
        # Initialize ALL fields with defaults (required by Neuroglia)
        self.id = ""
        self.source_id = ""
        self.tool_name = ""
        self.operation_id = ""

        self.definition = None
        self.definition_hash = ""

        self.is_enabled = True  # Tools are enabled by default
        self.status = ToolStatus.ACTIVE
        self.label_ids = []

        now = datetime.now(timezone.utc)
        self.discovered_at = now
        self.last_seen_at = now
        self.updated_at = now
        self.enabled_by = None
        self.disabled_by = None
        self.disable_reason = None

    # =========================================================================
    # Event Handlers - Apply events to state
    # =========================================================================

    @dispatch(SourceToolDiscoveredDomainEvent)
    def on(self, event: SourceToolDiscoveredDomainEvent) -> None:  # type: ignore[override]
        """Apply the discovered event to the state."""
        self.id = event.aggregate_id
        self.source_id = event.source_id
        self.tool_name = event.tool_name
        self.operation_id = event.operation_id
        self.definition_hash = event.definition_hash
        self.discovered_at = event.discovered_at
        self.last_seen_at = event.discovered_at
        self.updated_at = event.discovered_at
        self.status = ToolStatus.ACTIVE
        self.is_enabled = True

        # Deserialize definition from dict
        if event.definition:
            self.definition = ToolDefinition.from_dict(event.definition)

    @dispatch(SourceToolEnabledDomainEvent)
    def on(self, event: SourceToolEnabledDomainEvent) -> None:  # type: ignore[override]
        """Apply the enabled event to the state."""
        self.is_enabled = True
        self.enabled_by = event.enabled_by
        self.disabled_by = None
        self.disable_reason = None
        self.updated_at = event.enabled_at

    @dispatch(SourceToolDisabledDomainEvent)
    def on(self, event: SourceToolDisabledDomainEvent) -> None:  # type: ignore[override]
        """Apply the disabled event to the state."""
        self.is_enabled = False
        self.disabled_by = event.disabled_by
        self.disable_reason = event.reason
        self.updated_at = event.disabled_at

    @dispatch(SourceToolDefinitionUpdatedDomainEvent)
    def on(self, event: SourceToolDefinitionUpdatedDomainEvent) -> None:  # type: ignore[override]
        """Apply the definition updated event to the state."""
        self.definition_hash = event.new_definition_hash
        self.last_seen_at = event.updated_at
        self.updated_at = event.updated_at

        # Deserialize definition from dict
        if event.new_definition:
            self.definition = ToolDefinition.from_dict(event.new_definition)

    @dispatch(SourceToolDeprecatedDomainEvent)
    def on(self, event: SourceToolDeprecatedDomainEvent) -> None:  # type: ignore[override]
        """Apply the deprecated event to the state."""
        self.status = ToolStatus.DEPRECATED
        self.is_enabled = False  # Deprecated tools are automatically disabled
        self.updated_at = event.deprecated_at

    @dispatch(SourceToolRestoredDomainEvent)
    def on(self, event: SourceToolRestoredDomainEvent) -> None:  # type: ignore[override]
        """Apply the restored event to the state."""
        self.status = ToolStatus.ACTIVE
        self.is_enabled = True  # Restored tools are re-enabled
        self.definition_hash = event.new_definition_hash
        self.last_seen_at = event.restored_at
        self.updated_at = event.restored_at

        # Deserialize definition from dict
        if event.new_definition:
            self.definition = ToolDefinition.from_dict(event.new_definition)

    @dispatch(SourceToolDeletedDomainEvent)
    def on(self, event: SourceToolDeletedDomainEvent) -> None:  # type: ignore[override]
        """Apply the deleted event to the state.

        This marks the tool for removal. The actual deletion from the
        repository happens after this event is processed.
        """
        self.status = ToolStatus.DEPRECATED  # Mark as deprecated before removal
        self.is_enabled = False
        self.updated_at = event.deleted_at

    @dispatch(LabelAddedToToolDomainEvent)
    def on(self, event: LabelAddedToToolDomainEvent) -> None:  # type: ignore[override]
        """Apply the label added event to the state."""
        if event.label_id not in self.label_ids:
            self.label_ids.append(event.label_id)
        self.updated_at = event.added_at

    @dispatch(LabelRemovedFromToolDomainEvent)
    def on(self, event: LabelRemovedFromToolDomainEvent) -> None:  # type: ignore[override]
        """Apply the label removed event to the state."""
        if event.label_id in self.label_ids:
            self.label_ids.remove(event.label_id)
        self.updated_at = event.removed_at


class SourceTool(AggregateRoot[SourceToolState, str]):
    """SourceTool aggregate root following the AggregateState pattern.

    Represents an individual endpoint/tool from an upstream source,
    enabling granular admin control over tool availability.

    Lifecycle:
    1. discover() - Creates the tool when found in inventory
    2. enable()/disable() - Admin toggles availability
    3. update_definition() - Called when spec changes but tool exists
    4. deprecate() - Called when tool removed from upstream spec
    5. restore() - Called when deprecated tool reappears

    Invariants:
    - Only ACTIVE and ENABLED tools can be included in ToolGroups
    - Deprecated tools are automatically disabled
    - Tool ID format: "{source_id}:{operation_id}"

    Note: Neuroglia's Aggregator.aggregate() uses object.__new__() which doesn't
    initialize _pending_events. However, register_event() lazily initializes it,
    so methods that emit events work correctly. Methods like mark_seen() that
    don't emit events should not be followed by update_async() calls.
    """

    @staticmethod
    def create_tool_id(source_id: str, operation_id: str) -> str:
        """Generate a unique tool ID from source and operation.

        Args:
            source_id: The parent UpstreamSource ID
            operation_id: The operation ID from OpenAPI spec

        Returns:
            Tool ID in format "{source_id}:{operation_id}"
        """
        return f"{source_id}:{operation_id}"

    @staticmethod
    def compute_definition_hash(definition: ToolDefinition) -> str:
        """Compute a hash of the tool definition for change detection.

        Args:
            definition: The ToolDefinition to hash

        Returns:
            SHA-256 hash of the serialized definition
        """
        definition_dict = definition.to_dict()
        serialized = json.dumps(definition_dict, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()[:16]

    def __init__(
        self,
        source_id: str,
        operation_id: str,
        tool_name: str,
        definition: ToolDefinition,
        discovered_at: Optional[datetime] = None,
    ) -> None:
        """Create a new SourceTool aggregate (discovery).

        Args:
            source_id: Parent UpstreamSource ID
            operation_id: Operation ID from OpenAPI spec
            tool_name: Human-readable tool name
            definition: Normalized tool definition
            discovered_at: Optional discovery timestamp (defaults to now)
        """
        super().__init__()

        tool_id = self.create_tool_id(source_id, operation_id)
        discovered_time = discovered_at or datetime.now(timezone.utc)
        definition_hash = self.compute_definition_hash(definition)

        # Register the discovery event and apply it to state
        self.state.on(
            self.register_event(  # type: ignore
                SourceToolDiscoveredDomainEvent(
                    aggregate_id=tool_id,
                    source_id=source_id,
                    tool_name=tool_name,
                    operation_id=operation_id,
                    definition=definition.to_dict(),
                    definition_hash=definition_hash,
                    discovered_at=discovered_time,
                )
            )
        )

    # =========================================================================
    # Commands - Business operations that modify state
    # =========================================================================

    def enable(self, enabled_by: Optional[str] = None) -> bool:
        """Enable this tool for inclusion in ToolGroups.

        Args:
            enabled_by: User performing the action

        Returns:
            True if state changed, False if already enabled
        """
        if self.state.is_enabled:
            return False

        if self.state.status == ToolStatus.DEPRECATED:
            raise ValueError("Cannot enable a deprecated tool")

        self.state.on(
            self.register_event(  # type: ignore
                SourceToolEnabledDomainEvent(
                    aggregate_id=self.state.id,
                    enabled_at=datetime.now(timezone.utc),
                    enabled_by=enabled_by,
                )
            )
        )
        return True

    def disable(
        self,
        disabled_by: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> bool:
        """Disable this tool, excluding it from all ToolGroups.

        Args:
            disabled_by: User performing the action
            reason: Optional reason for disabling

        Returns:
            True if state changed, False if already disabled
        """
        if not self.state.is_enabled:
            return False

        self.state.on(
            self.register_event(  # type: ignore
                SourceToolDisabledDomainEvent(
                    aggregate_id=self.state.id,
                    disabled_at=datetime.now(timezone.utc),
                    disabled_by=disabled_by,
                    reason=reason,
                )
            )
        )
        return True

    def update_definition(self, new_definition: ToolDefinition) -> bool:
        """Update the tool definition when the upstream spec changes.

        Args:
            new_definition: The updated tool definition

        Returns:
            True if definition changed, False if unchanged
        """
        new_hash = self.compute_definition_hash(new_definition)

        if new_hash == self.state.definition_hash:
            # No actual change, just update last_seen_at
            return False

        self.state.on(
            self.register_event(  # type: ignore
                SourceToolDefinitionUpdatedDomainEvent(
                    aggregate_id=self.state.id,
                    old_definition_hash=self.state.definition_hash,
                    new_definition=new_definition.to_dict(),
                    new_definition_hash=new_hash,
                    updated_at=datetime.now(timezone.utc),
                )
            )
        )
        return True

    def deprecate(self) -> bool:
        """Mark this tool as deprecated (removed from upstream spec).

        Returns:
            True if state changed, False if already deprecated
        """
        if self.state.status == ToolStatus.DEPRECATED:
            return False

        self.state.on(
            self.register_event(  # type: ignore
                SourceToolDeprecatedDomainEvent(
                    aggregate_id=self.state.id,
                    deprecated_at=datetime.now(timezone.utc),
                    last_seen_at=self.state.last_seen_at,
                )
            )
        )
        return True

    def restore(self, new_definition: ToolDefinition) -> bool:
        """Restore a deprecated tool that has reappeared in the spec.

        Args:
            new_definition: The tool definition from current spec

        Returns:
            True if restored, False if not deprecated
        """
        if self.state.status != ToolStatus.DEPRECATED:
            return False

        new_hash = self.compute_definition_hash(new_definition)

        self.state.on(
            self.register_event(  # type: ignore
                SourceToolRestoredDomainEvent(
                    aggregate_id=self.state.id,
                    new_definition=new_definition.to_dict(),
                    new_definition_hash=new_hash,
                    restored_at=datetime.now(timezone.utc),
                )
            )
        )
        return True

    def mark_seen(self) -> None:
        """Update last_seen_at during inventory sync without emitting event.

        This is a lightweight update for tracking purposes, called when
        the tool is still present in the spec but unchanged.
        """
        self.state.last_seen_at = datetime.now(timezone.utc)

    def mark_as_deleted(self, deleted_by: Optional[str] = None, reason: Optional[str] = None) -> bool:
        """Mark this tool for deletion by an admin.

        This is a hard delete operation. The event is emitted for audit purposes,
        then the aggregate will be removed from the repository.

        Args:
            deleted_by: Username or ID of admin performing the deletion
            reason: Optional reason for deletion

        Returns:
            True (always, for consistency with other methods)
        """
        self.state.on(
            self.register_event(  # type: ignore
                SourceToolDeletedDomainEvent(
                    aggregate_id=self.state.id,
                    deleted_at=datetime.now(timezone.utc),
                    deleted_by=deleted_by,
                    reason=reason,
                )
            )
        )
        return True

    def add_label(self, label_id: str, added_by: Optional[str] = None) -> bool:
        """Add a label to this tool.

        Args:
            label_id: ID of the label to add
            added_by: User performing the action

        Returns:
            True if label was added, False if already present
        """
        if label_id in self.state.label_ids:
            return False

        self.state.on(
            self.register_event(  # type: ignore
                LabelAddedToToolDomainEvent(
                    aggregate_id=self.state.id,
                    label_id=label_id,
                    added_at=datetime.now(timezone.utc),
                    added_by=added_by,
                )
            )
        )
        return True

    def remove_label(self, label_id: str, removed_by: Optional[str] = None) -> bool:
        """Remove a label from this tool.

        Args:
            label_id: ID of the label to remove
            removed_by: User performing the action

        Returns:
            True if label was removed, False if not present
        """
        if label_id not in self.state.label_ids:
            return False

        self.state.on(
            self.register_event(  # type: ignore
                LabelRemovedFromToolDomainEvent(
                    aggregate_id=self.state.id,
                    label_id=label_id,
                    removed_at=datetime.now(timezone.utc),
                    removed_by=removed_by,
                )
            )
        )
        return True

    @property
    def label_ids(self) -> List[str]:
        """Get the list of label IDs assigned to this tool."""
        return self.state.label_ids

    # =========================================================================
    # Query methods - Read state
    # =========================================================================

    @property
    def tool_id(self) -> str:
        """Get the unique tool identifier."""
        return self.state.id

    @property
    def source_id(self) -> str:
        """Get the parent source ID."""
        return self.state.source_id

    @property
    def is_available(self) -> bool:
        """Check if this tool can be included in ToolGroups.

        A tool is available only if:
        1. It is ACTIVE (not deprecated)
        2. It is ENABLED (not disabled by admin)
        """
        return self.state.status == ToolStatus.ACTIVE and self.state.is_enabled

    @property
    def definition(self) -> Optional[ToolDefinition]:
        """Get the tool definition."""
        return self.state.definition

    @property
    def is_enabled(self) -> bool:
        """Check if admin has enabled this tool."""
        return self.state.is_enabled

    @property
    def is_deprecated(self) -> bool:
        """Check if this tool has been deprecated."""
        return self.state.status == ToolStatus.DEPRECATED
