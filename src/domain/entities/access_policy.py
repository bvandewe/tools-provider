"""AccessPolicy aggregate definition using the AggregateState pattern.

This aggregate maps JWT claims to allowed tool groups, enabling
fine-grained access control for AI agents.

Key Design Decisions:
1. Multiple ClaimMatchers are evaluated with AND logic (all must match)
2. Multiple AccessPolicies are evaluated with OR logic (any can grant access)
3. Priority determines evaluation order (higher = earlier)
4. Only active policies participate in access resolution

Following the UpstreamSource/ToolGroup aggregate pattern:
- DomainEvents are registered via register_event()
- State is updated via @dispatch handlers
- Repository publishes events after persistence
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from multipledispatch import dispatch
from neuroglia.data.abstractions import AggregateRoot, AggregateState

from domain.events.access_policy import (
    AccessPolicyActivatedDomainEvent,
    AccessPolicyDeactivatedDomainEvent,
    AccessPolicyDefinedDomainEvent,
    AccessPolicyDeletedDomainEvent,
    AccessPolicyGroupsUpdatedDomainEvent,
    AccessPolicyMatchersUpdatedDomainEvent,
    AccessPolicyPriorityUpdatedDomainEvent,
    AccessPolicyUpdatedDomainEvent,
)
from domain.models import ClaimMatcher


class AccessPolicyState(AggregateState[str]):
    """Encapsulates the persisted state for the AccessPolicy aggregate.

    Attributes:
        id: Unique identifier for this policy
        name: Human-readable name for the policy
        description: Detailed description of the policy's purpose

        claim_matchers: List of ClaimMatcher rules (evaluated with AND logic)
        allowed_group_ids: Tool group IDs this policy grants access to

        priority: Higher values = evaluated first (default: 0)
        is_active: Only active policies participate in access resolution

        created_at: When the policy was created
        updated_at: Last state change timestamp
        created_by: User who created the policy
    """

    # Identity
    id: str
    name: str
    description: Optional[str]

    # Access rules
    claim_matchers: List[ClaimMatcher]
    allowed_group_ids: List[str]

    # Evaluation control
    priority: int
    is_active: bool

    # Audit trail
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]

    def __init__(self) -> None:
        super().__init__()
        # Initialize ALL fields with defaults (required by Neuroglia)
        self.id = ""
        self.name = ""
        self.description = None

        self.claim_matchers = []
        self.allowed_group_ids = []

        self.priority = 0
        self.is_active = True

        now = datetime.now(timezone.utc)
        self.created_at = now
        self.updated_at = now
        self.created_by = None

    # =========================================================================
    # Event Handlers - Apply events to state
    # =========================================================================

    @dispatch(AccessPolicyDefinedDomainEvent)
    def on(self, event: AccessPolicyDefinedDomainEvent) -> None:  # type: ignore[override]
        """Apply the defined event to the state."""
        self.id = event.aggregate_id
        self.name = event.name
        self.description = event.description
        self.priority = event.priority
        self.created_at = event.defined_at
        self.updated_at = event.defined_at
        self.created_by = event.defined_by
        self.is_active = True

        # Deserialize claim matchers from dict list
        self.claim_matchers = [ClaimMatcher.from_dict(m) for m in event.claim_matchers]
        self.allowed_group_ids = list(event.allowed_group_ids)

    @dispatch(AccessPolicyUpdatedDomainEvent)
    def on(self, event: AccessPolicyUpdatedDomainEvent) -> None:  # type: ignore[override]
        """Apply the update event to the state."""
        if event.name is not None:
            self.name = event.name
        if event.description is not None:
            self.description = event.description
        self.updated_at = event.updated_at

    @dispatch(AccessPolicyMatchersUpdatedDomainEvent)
    def on(self, event: AccessPolicyMatchersUpdatedDomainEvent) -> None:  # type: ignore[override]
        """Apply the matchers updated event to the state."""
        self.claim_matchers = [ClaimMatcher.from_dict(m) for m in event.claim_matchers]
        self.updated_at = event.updated_at

    @dispatch(AccessPolicyGroupsUpdatedDomainEvent)
    def on(self, event: AccessPolicyGroupsUpdatedDomainEvent) -> None:  # type: ignore[override]
        """Apply the groups updated event to the state."""
        self.allowed_group_ids = list(event.allowed_group_ids)
        self.updated_at = event.updated_at

    @dispatch(AccessPolicyPriorityUpdatedDomainEvent)
    def on(self, event: AccessPolicyPriorityUpdatedDomainEvent) -> None:  # type: ignore[override]
        """Apply the priority updated event to the state."""
        self.priority = event.new_priority
        self.updated_at = event.updated_at

    @dispatch(AccessPolicyActivatedDomainEvent)
    def on(self, event: AccessPolicyActivatedDomainEvent) -> None:  # type: ignore[override]
        """Apply the activation event to the state."""
        self.is_active = True
        self.updated_at = event.activated_at

    @dispatch(AccessPolicyDeactivatedDomainEvent)
    def on(self, event: AccessPolicyDeactivatedDomainEvent) -> None:  # type: ignore[override]
        """Apply the deactivation event to the state."""
        self.is_active = False
        self.updated_at = event.deactivated_at

    @dispatch(AccessPolicyDeletedDomainEvent)
    def on(self, event: AccessPolicyDeletedDomainEvent) -> None:  # type: ignore[override]
        """Apply the deleted event to the state."""
        self.is_active = False
        self.updated_at = event.deleted_at


class AccessPolicy(AggregateRoot[AccessPolicyState, str]):
    """AccessPolicy aggregate root following the AggregateState pattern.

    Maps JWT claims to allowed tool groups for access control.

    Evaluation Logic:
    1. All ClaimMatchers in a policy are evaluated with AND logic
    2. Multiple policies are evaluated with OR logic (any grants access)
    3. Higher priority policies are evaluated first (for short-circuit optimization)
    4. Only active policies participate in evaluation

    Lifecycle:
    1. __init__() - Creates the policy with matchers and groups
    2. update()/update_matchers()/update_groups() - Modify configuration
    3. set_priority() - Change evaluation order
    4. activate()/deactivate() - Toggle participation
    5. mark_as_deleted() - Soft delete

    Note: Neuroglia's Aggregator.aggregate() uses object.__new__() which doesn't
    initialize _pending_events. However, register_event() lazily initializes it,
    so methods that emit events work correctly.
    """

    def __init__(
        self,
        name: str,
        claim_matchers: List[ClaimMatcher],
        allowed_group_ids: List[str],
        description: Optional[str] = None,
        priority: int = 0,
        defined_at: Optional[datetime] = None,
        defined_by: Optional[str] = None,
        policy_id: Optional[str] = None,
    ) -> None:
        """Create a new AccessPolicy aggregate.

        Args:
            name: Human-readable name for this policy
            claim_matchers: List of ClaimMatcher rules (AND logic)
            allowed_group_ids: Tool group IDs this policy grants access to
            description: Optional detailed description
            priority: Evaluation order (higher = earlier, default: 0)
            defined_at: Optional creation timestamp (defaults to now)
            defined_by: Optional user ID who defined this policy
            policy_id: Optional specific ID (defaults to UUID)
        """
        super().__init__()
        aggregate_id = policy_id or str(uuid4())
        created_time = defined_at or datetime.now(timezone.utc)

        # Validate inputs
        if not name or not name.strip():
            raise ValueError("Policy name cannot be empty")
        if not claim_matchers:
            raise ValueError("At least one claim matcher is required")
        if not allowed_group_ids:
            raise ValueError("At least one allowed group ID is required")

        # Serialize matchers for the event
        matchers_dicts = [m.to_dict() for m in claim_matchers]

        self.state.on(
            self.register_event(  # type: ignore
                AccessPolicyDefinedDomainEvent(
                    aggregate_id=aggregate_id,
                    name=name.strip(),
                    description=description.strip() if description else None,
                    claim_matchers=matchers_dicts,
                    allowed_group_ids=list(allowed_group_ids),
                    priority=priority,
                    defined_at=created_time,
                    defined_by=defined_by,
                )
            )
        )

    # =========================================================================
    # Command Methods - Emit events and apply to state
    # =========================================================================

    def update(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        updated_by: Optional[str] = None,
    ) -> bool:
        """Update the policy's basic information.

        Args:
            name: New name (optional)
            description: New description (optional)
            updated_by: User making the change

        Returns:
            True if any changes were made, False otherwise
        """
        # Check if there are actual changes
        name_changed = name is not None and name.strip() != self.state.name
        desc_changed = description is not None and (description.strip() if description else None) != self.state.description

        if not name_changed and not desc_changed:
            return False

        self.state.on(
            self.register_event(  # type: ignore
                AccessPolicyUpdatedDomainEvent(
                    aggregate_id=self.id(),
                    name=name.strip() if name_changed and name else None,
                    description=description.strip() if desc_changed and description else None,
                    updated_at=datetime.now(timezone.utc),
                    updated_by=updated_by,
                )
            )
        )
        return True

    def update_matchers(
        self,
        claim_matchers: List[ClaimMatcher],
        updated_by: Optional[str] = None,
    ) -> bool:
        """Replace all claim matchers with a new list.

        Args:
            claim_matchers: New list of ClaimMatcher rules
            updated_by: User making the change

        Returns:
            True if changes were made, False otherwise
        """
        if not claim_matchers:
            raise ValueError("At least one claim matcher is required")

        # Check if matchers actually changed
        new_dicts = [m.to_dict() for m in claim_matchers]
        old_dicts = [m.to_dict() for m in self.state.claim_matchers]

        if new_dicts == old_dicts:
            return False

        self.state.on(
            self.register_event(  # type: ignore
                AccessPolicyMatchersUpdatedDomainEvent(
                    aggregate_id=self.id(),
                    claim_matchers=new_dicts,
                    updated_at=datetime.now(timezone.utc),
                    updated_by=updated_by,
                )
            )
        )
        return True

    def update_groups(
        self,
        allowed_group_ids: List[str],
        updated_by: Optional[str] = None,
    ) -> bool:
        """Replace all allowed group IDs with a new list.

        Args:
            allowed_group_ids: New list of tool group IDs
            updated_by: User making the change

        Returns:
            True if changes were made, False otherwise
        """
        if not allowed_group_ids:
            raise ValueError("At least one allowed group ID is required")

        # Check if groups actually changed
        if set(allowed_group_ids) == set(self.state.allowed_group_ids):
            return False

        self.state.on(
            self.register_event(  # type: ignore
                AccessPolicyGroupsUpdatedDomainEvent(
                    aggregate_id=self.id(),
                    allowed_group_ids=list(allowed_group_ids),
                    updated_at=datetime.now(timezone.utc),
                    updated_by=updated_by,
                )
            )
        )
        return True

    def set_priority(
        self,
        priority: int,
        updated_by: Optional[str] = None,
    ) -> bool:
        """Change the policy's evaluation priority.

        Args:
            priority: New priority value (higher = earlier evaluation)
            updated_by: User making the change

        Returns:
            True if priority changed, False otherwise
        """
        if priority == self.state.priority:
            return False

        old_priority = self.state.priority

        self.state.on(
            self.register_event(  # type: ignore
                AccessPolicyPriorityUpdatedDomainEvent(
                    aggregate_id=self.id(),
                    old_priority=old_priority,
                    new_priority=priority,
                    updated_at=datetime.now(timezone.utc),
                    updated_by=updated_by,
                )
            )
        )
        return True

    def activate(self, activated_by: Optional[str] = None) -> bool:
        """Activate the policy for access evaluation.

        Args:
            activated_by: User activating the policy

        Returns:
            True if state changed, False if already active
        """
        if self.state.is_active:
            return False

        self.state.on(
            self.register_event(  # type: ignore
                AccessPolicyActivatedDomainEvent(
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
        """Deactivate the policy (exclude from access evaluation).

        Args:
            deactivated_by: User deactivating the policy
            reason: Optional reason for deactivation

        Returns:
            True if state changed, False if already inactive
        """
        if not self.state.is_active:
            return False

        self.state.on(
            self.register_event(  # type: ignore
                AccessPolicyDeactivatedDomainEvent(
                    aggregate_id=self.id(),
                    deactivated_at=datetime.now(timezone.utc),
                    deactivated_by=deactivated_by,
                    reason=reason,
                )
            )
        )
        return True

    def mark_as_deleted(self, deleted_by: Optional[str] = None) -> None:
        """Mark the policy for deletion.

        Args:
            deleted_by: User deleting the policy
        """
        self.state.on(
            self.register_event(  # type: ignore
                AccessPolicyDeletedDomainEvent(
                    aggregate_id=self.id(),
                    deleted_at=datetime.now(timezone.utc),
                    deleted_by=deleted_by,
                )
            )
        )

    # =========================================================================
    # Query Methods - Read-only operations on state
    # =========================================================================

    def matches_claims(self, claims: Dict[str, Any]) -> bool:
        """Check if the given JWT claims match this policy's matchers.

        All matchers must match (AND logic) for the policy to grant access.

        Args:
            claims: JWT claims dictionary

        Returns:
            True if all matchers match, False otherwise
        """
        if not self.state.is_active:
            return False

        if not self.state.claim_matchers:
            return False

        # AND logic: all matchers must match
        return all(matcher.matches(claims) for matcher in self.state.claim_matchers)

    def get_allowed_groups(self) -> List[str]:
        """Get the list of allowed group IDs.

        Returns:
            Copy of the allowed_group_ids list
        """
        return list(self.state.allowed_group_ids)

    def get_matchers(self) -> List[ClaimMatcher]:
        """Get the list of claim matchers.

        Returns:
            Copy of the claim_matchers list
        """
        return list(self.state.claim_matchers)
