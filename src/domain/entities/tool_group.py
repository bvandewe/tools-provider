"""ToolGroup aggregate definition using the AggregateState pattern.

This aggregate curates tools into logical groups using both:
1. Pattern-based selectors (dynamic matching)
2. Explicit tool references (direct membership)
3. Exclusion lists (override selector matches)

Tool Resolution Order:
1. Start with empty set
2. Add all ENABLED tools matching selectors
3. Add all explicit_tool_ids
4. Remove all excluded_tool_ids

Following the UpstreamSource aggregate pattern:
- DomainEvents are registered via register_event()
- State is updated via @dispatch handlers
- Repository publishes events after persistence
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from multipledispatch import dispatch
from neuroglia.data.abstractions import AggregateRoot, AggregateState

from domain.events.tool_group import (ExplicitToolAddedDomainEvent, ExplicitToolRemovedDomainEvent, SelectorAddedDomainEvent, SelectorRemovedDomainEvent, ToolExcludedDomainEvent,
                                      ToolGroupActivatedDomainEvent, ToolGroupCreatedDomainEvent, ToolGroupDeactivatedDomainEvent, ToolGroupDeletedDomainEvent, ToolGroupUpdatedDomainEvent,
                                      ToolIncludedDomainEvent)
from domain.models import ToolSelector
from domain.models.tool_group_membership import ToolExclusion, ToolGroupMembership

# Forward reference for DTO mapping (will be in integration layer)
# from integration.models.tool_group_dto import ToolGroupDto


# @map_to(ToolGroupDto)  # Uncomment when ToolGroupDto is created
class ToolGroupState(AggregateState[str]):
    """Encapsulates the persisted state for the ToolGroup aggregate.

    Attributes:
        id: Unique identifier for this group
        name: Human-readable name for the group
        description: Detailed description of the group's purpose

        selectors: Pattern-based rules for including tools
        explicit_tool_ids: Tools explicitly added to the group
        excluded_tool_ids: Tools excluded even if matched by selectors

        is_active: Whether this group is active and can be assigned to policies
        created_at: When the group was created
        updated_at: Last state change timestamp
        created_by: User who created the group
    """

    # Identity
    id: str
    name: str
    description: str

    # Pattern-based selection
    selectors: List[ToolSelector]

    # Explicit tool management
    explicit_tool_ids: List[ToolGroupMembership]
    excluded_tool_ids: List[ToolExclusion]

    # Lifecycle
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]

    def __init__(self) -> None:
        super().__init__()
        # Initialize ALL fields with defaults (required by Neuroglia)
        self.id = ""
        self.name = ""
        self.description = ""

        self.selectors = []
        self.explicit_tool_ids = []
        self.excluded_tool_ids = []

        self.is_active = True
        now = datetime.now(timezone.utc)
        self.created_at = now
        self.updated_at = now
        self.created_by = None

    # =========================================================================
    # Event Handlers - Apply events to state
    # =========================================================================

    @dispatch(ToolGroupCreatedDomainEvent)
    def on(self, event: ToolGroupCreatedDomainEvent) -> None:  # type: ignore[override]
        """Apply the creation event to the state."""
        self.id = event.aggregate_id
        self.name = event.name
        self.description = event.description
        self.created_at = event.created_at
        self.updated_at = event.created_at
        self.created_by = event.created_by
        self.is_active = True
        self.selectors = []
        self.explicit_tool_ids = []
        self.excluded_tool_ids = []

    @dispatch(ToolGroupUpdatedDomainEvent)
    def on(self, event: ToolGroupUpdatedDomainEvent) -> None:  # type: ignore[override]
        """Apply the update event to the state."""
        if event.name is not None:
            self.name = event.name
        if event.description is not None:
            self.description = event.description
        self.updated_at = event.updated_at

    @dispatch(SelectorAddedDomainEvent)
    def on(self, event: SelectorAddedDomainEvent) -> None:  # type: ignore[override]
        """Apply the selector added event to the state."""
        selector = ToolSelector.from_dict(event.selector)
        self.selectors.append(selector)
        self.updated_at = event.added_at

    @dispatch(SelectorRemovedDomainEvent)
    def on(self, event: SelectorRemovedDomainEvent) -> None:  # type: ignore[override]
        """Apply the selector removed event to the state."""
        self.selectors = [s for s in self.selectors if s.id != event.selector_id]
        self.updated_at = event.removed_at

    @dispatch(ExplicitToolAddedDomainEvent)
    def on(self, event: ExplicitToolAddedDomainEvent) -> None:  # type: ignore[override]
        """Apply the explicit tool added event to the state."""
        membership = ToolGroupMembership(
            tool_id=event.tool_id,
            added_at=event.added_at,
            added_by=event.added_by,
        )
        self.explicit_tool_ids.append(membership)
        self.updated_at = event.added_at

    @dispatch(ExplicitToolRemovedDomainEvent)
    def on(self, event: ExplicitToolRemovedDomainEvent) -> None:  # type: ignore[override]
        """Apply the explicit tool removed event to the state."""
        self.explicit_tool_ids = [m for m in self.explicit_tool_ids if m.tool_id != event.tool_id]
        self.updated_at = event.removed_at

    @dispatch(ToolExcludedDomainEvent)
    def on(self, event: ToolExcludedDomainEvent) -> None:  # type: ignore[override]
        """Apply the tool excluded event to the state."""
        exclusion = ToolExclusion(
            tool_id=event.tool_id,
            excluded_at=event.excluded_at,
            excluded_by=event.excluded_by,
            reason=event.reason,
        )
        self.excluded_tool_ids.append(exclusion)
        self.updated_at = event.excluded_at

    @dispatch(ToolIncludedDomainEvent)
    def on(self, event: ToolIncludedDomainEvent) -> None:  # type: ignore[override]
        """Apply the tool included event to the state."""
        self.excluded_tool_ids = [e for e in self.excluded_tool_ids if e.tool_id != event.tool_id]
        self.updated_at = event.included_at

    @dispatch(ToolGroupActivatedDomainEvent)
    def on(self, event: ToolGroupActivatedDomainEvent) -> None:  # type: ignore[override]
        """Apply the activation event to the state."""
        self.is_active = True
        self.updated_at = event.activated_at

    @dispatch(ToolGroupDeactivatedDomainEvent)
    def on(self, event: ToolGroupDeactivatedDomainEvent) -> None:  # type: ignore[override]
        """Apply the deactivation event to the state."""
        self.is_active = False
        self.updated_at = event.deactivated_at

    @dispatch(ToolGroupDeletedDomainEvent)
    def on(self, event: ToolGroupDeletedDomainEvent) -> None:  # type: ignore[override]
        """Apply the deleted event to the state."""
        self.is_active = False
        self.updated_at = event.deleted_at


class ToolGroup(AggregateRoot[ToolGroupState, str]):
    """ToolGroup aggregate root following the AggregateState pattern.

    Curates tools into logical groups for access policy assignment.
    Supports both pattern-based selection and explicit tool management.

    Tool Resolution Order:
    1. Start with empty set
    2. Add all ENABLED tools matching selectors (OR logic between selectors)
    3. Add all explicit_tool_ids
    4. Remove all excluded_tool_ids

    Lifecycle:
    1. __init__() - Creates the group
    2. add_selector()/remove_selector() - Manage patterns
    3. add_tool()/remove_tool() - Manage explicit memberships
    4. exclude_tool()/include_tool() - Manage exclusions
    5. activate()/deactivate() - Toggle availability
    6. mark_as_deleted() - Soft delete

    Invariants:
    - Selector IDs must be unique within a group
    - Cannot add the same tool twice explicitly
    - Cannot exclude an already excluded tool
    - Deactivated groups are excluded from access policy resolution
    """

    def __init__(
        self,
        name: str,
        description: str,
        created_at: Optional[datetime] = None,
        created_by: Optional[str] = None,
        group_id: Optional[str] = None,
    ) -> None:
        """Create a new ToolGroup aggregate.

        Args:
            name: Human-readable name for this group
            description: Detailed description of the group's purpose
            created_at: Optional creation timestamp (defaults to now)
            created_by: Optional user ID who created this group
            group_id: Optional specific ID (defaults to UUID)
        """
        super().__init__()
        aggregate_id = group_id or str(uuid4())
        timestamp = created_at or datetime.now(timezone.utc)

        # Register creation event
        self.state.on(
            self.register_event(  # type: ignore
                ToolGroupCreatedDomainEvent(
                    aggregate_id=aggregate_id,
                    name=name,
                    description=description,
                    created_at=timestamp,
                    created_by=created_by,
                )
            )
        )

    # =========================================================================
    # Name and Description Management
    # =========================================================================

    def update(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        updated_by: Optional[str] = None,
    ) -> bool:
        """Update the group's name and/or description.

        Args:
            name: New name (None to keep current)
            description: New description (None to keep current)
            updated_by: User making the update

        Returns:
            True if any changes were made, False otherwise
        """
        # Check if any actual changes
        if name is None and description is None:
            return False

        if name == self.state.name and description == self.state.description:
            return False

        self.state.on(
            self.register_event(  # type: ignore
                ToolGroupUpdatedDomainEvent(
                    aggregate_id=self.id(),
                    name=name if name != self.state.name else None,
                    description=description if description != self.state.description else None,
                    updated_at=datetime.now(timezone.utc),
                    updated_by=updated_by,
                )
            )
        )
        return True

    # =========================================================================
    # Selector Management (Pattern-Based)
    # =========================================================================

    def add_selector(
        self,
        selector: ToolSelector,
        added_by: Optional[str] = None,
    ) -> bool:
        """Add a pattern-based selector to the group.

        Args:
            selector: The ToolSelector to add
            added_by: User adding the selector

        Returns:
            True if added, False if selector ID already exists
        """
        # Check for duplicate selector ID
        if any(s.id == selector.id for s in self.state.selectors):
            return False

        self.state.on(
            self.register_event(  # type: ignore
                SelectorAddedDomainEvent(
                    aggregate_id=self.id(),
                    selector=selector.to_dict(),
                    added_at=datetime.now(timezone.utc),
                    added_by=added_by,
                )
            )
        )
        return True

    def remove_selector(
        self,
        selector_id: str,
        removed_by: Optional[str] = None,
    ) -> bool:
        """Remove a selector from the group.

        Args:
            selector_id: ID of the selector to remove
            removed_by: User removing the selector

        Returns:
            True if removed, False if selector not found
        """
        # Check if selector exists
        if not any(s.id == selector_id for s in self.state.selectors):
            return False

        self.state.on(
            self.register_event(  # type: ignore
                SelectorRemovedDomainEvent(
                    aggregate_id=self.id(),
                    selector_id=selector_id,
                    removed_at=datetime.now(timezone.utc),
                    removed_by=removed_by,
                )
            )
        )
        return True

    # =========================================================================
    # Explicit Tool Management
    # =========================================================================

    def add_tool(
        self,
        tool_id: str,
        added_by: Optional[str] = None,
    ) -> bool:
        """Explicitly add a tool to the group.

        Args:
            tool_id: ID of the tool to add
            added_by: User adding the tool

        Returns:
            True if added, False if already exists
        """
        # Check if tool already added
        if any(m.tool_id == tool_id for m in self.state.explicit_tool_ids):
            return False

        self.state.on(
            self.register_event(  # type: ignore
                ExplicitToolAddedDomainEvent(
                    aggregate_id=self.id(),
                    tool_id=tool_id,
                    added_at=datetime.now(timezone.utc),
                    added_by=added_by,
                )
            )
        )
        return True

    def remove_tool(
        self,
        tool_id: str,
        removed_by: Optional[str] = None,
    ) -> bool:
        """Remove an explicitly added tool from the group.

        Args:
            tool_id: ID of the tool to remove
            removed_by: User removing the tool

        Returns:
            True if removed, False if not found
        """
        # Check if tool exists in explicit list
        if not any(m.tool_id == tool_id for m in self.state.explicit_tool_ids):
            return False

        self.state.on(
            self.register_event(  # type: ignore
                ExplicitToolRemovedDomainEvent(
                    aggregate_id=self.id(),
                    tool_id=tool_id,
                    removed_at=datetime.now(timezone.utc),
                    removed_by=removed_by,
                )
            )
        )
        return True

    # =========================================================================
    # Exclusion Management
    # =========================================================================

    def exclude_tool(
        self,
        tool_id: str,
        excluded_by: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> bool:
        """Exclude a tool from the group.

        Excluded tools are never included even if they match a selector.

        Args:
            tool_id: ID of the tool to exclude
            excluded_by: User excluding the tool
            reason: Reason for exclusion

        Returns:
            True if excluded, False if already excluded
        """
        # Check if already excluded
        if any(e.tool_id == tool_id for e in self.state.excluded_tool_ids):
            return False

        self.state.on(
            self.register_event(  # type: ignore
                ToolExcludedDomainEvent(
                    aggregate_id=self.id(),
                    tool_id=tool_id,
                    excluded_at=datetime.now(timezone.utc),
                    excluded_by=excluded_by,
                    reason=reason,
                )
            )
        )
        return True

    def include_tool(
        self,
        tool_id: str,
        included_by: Optional[str] = None,
    ) -> bool:
        """Remove a tool from the exclusion list.

        This re-enables a previously excluded tool to be matched by selectors.

        Args:
            tool_id: ID of the tool to include
            included_by: User including the tool

        Returns:
            True if removed from exclusions, False if not excluded
        """
        # Check if tool is excluded
        if not any(e.tool_id == tool_id for e in self.state.excluded_tool_ids):
            return False

        self.state.on(
            self.register_event(  # type: ignore
                ToolIncludedDomainEvent(
                    aggregate_id=self.id(),
                    tool_id=tool_id,
                    included_at=datetime.now(timezone.utc),
                    included_by=included_by,
                )
            )
        )
        return True

    # =========================================================================
    # Lifecycle Management
    # =========================================================================

    def activate(self, activated_by: Optional[str] = None) -> bool:
        """Activate the group.

        Args:
            activated_by: User activating the group

        Returns:
            True if activated, False if already active
        """
        if self.state.is_active:
            return False

        self.state.on(
            self.register_event(  # type: ignore
                ToolGroupActivatedDomainEvent(
                    aggregate_id=self.id(),
                    activated_at=datetime.now(timezone.utc),
                    activated_by=activated_by,
                )
            )
        )
        return True

    def deactivate(
        self,
        deactivated_by: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> bool:
        """Deactivate the group.

        Deactivated groups are not included in access policy resolution.

        Args:
            deactivated_by: User deactivating the group
            reason: Reason for deactivation

        Returns:
            True if deactivated, False if already inactive
        """
        if not self.state.is_active:
            return False

        self.state.on(
            self.register_event(  # type: ignore
                ToolGroupDeactivatedDomainEvent(
                    aggregate_id=self.id(),
                    deactivated_at=datetime.now(timezone.utc),
                    deactivated_by=deactivated_by,
                    reason=reason,
                )
            )
        )
        return True

    def mark_as_deleted(self, deleted_by: Optional[str] = None) -> None:
        """Mark the group for deletion.

        Args:
            deleted_by: User deleting the group
        """
        self.state.on(
            self.register_event(  # type: ignore
                ToolGroupDeletedDomainEvent(
                    aggregate_id=self.id(),
                    deleted_at=datetime.now(timezone.utc),
                    deleted_by=deleted_by,
                )
            )
        )

    # =========================================================================
    # Query Methods (Read from State)
    # =========================================================================

    def has_selector(self, selector_id: str) -> bool:
        """Check if a selector exists in this group."""
        return any(s.id == selector_id for s in self.state.selectors)

    def has_explicit_tool(self, tool_id: str) -> bool:
        """Check if a tool is explicitly added to this group."""
        return any(m.tool_id == tool_id for m in self.state.explicit_tool_ids)

    def is_tool_excluded(self, tool_id: str) -> bool:
        """Check if a tool is excluded from this group."""
        return any(e.tool_id == tool_id for e in self.state.excluded_tool_ids)

    def get_selector_count(self) -> int:
        """Get the number of selectors in this group."""
        return len(self.state.selectors)

    def get_explicit_tool_count(self) -> int:
        """Get the number of explicitly added tools."""
        return len(self.state.explicit_tool_ids)

    def get_excluded_tool_count(self) -> int:
        """Get the number of excluded tools."""
        return len(self.state.excluded_tool_ids)
