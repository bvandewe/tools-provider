"""Domain events for AccessPolicy aggregate operations.

These events track the lifecycle and changes to access policies that
map JWT claims to allowed tool groups.

Following the Task event pattern:
- @cloudevent decorator for CloudEvent type registration
- @dataclass for serialization
- DomainEvent base class for aggregate correlation
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from neuroglia.data.abstractions import DomainEvent
from neuroglia.eventing.cloud_events.decorators import cloudevent


@cloudevent("accesspolicy.defined.v1")
@dataclass
class AccessPolicyDefinedDomainEvent(DomainEvent):
    """Event raised when a new access policy is defined.

    This event captures the initial creation of an access policy,
    including its claim matchers and allowed group mappings.
    """

    aggregate_id: str
    name: str
    description: str | None
    claim_matchers: list[dict[str, Any]]  # Serialized ClaimMatcher list
    allowed_group_ids: list[str]
    priority: int
    defined_at: datetime
    defined_by: str | None

    def __init__(
        self,
        aggregate_id: str,
        name: str,
        description: str | None,
        claim_matchers: list[dict[str, Any]],
        allowed_group_ids: list[str],
        priority: int,
        defined_at: datetime,
        defined_by: str | None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.name = name
        self.description = description
        self.claim_matchers = claim_matchers
        self.allowed_group_ids = allowed_group_ids
        self.priority = priority
        self.defined_at = defined_at
        self.defined_by = defined_by


@cloudevent("accesspolicy.updated.v1")
@dataclass
class AccessPolicyUpdatedDomainEvent(DomainEvent):
    """Event raised when an access policy's basic info is updated.

    Tracks changes to name and description fields.
    """

    aggregate_id: str
    name: str | None
    description: str | None
    updated_at: datetime
    updated_by: str | None

    def __init__(
        self,
        aggregate_id: str,
        name: str | None,
        description: str | None,
        updated_at: datetime,
        updated_by: str | None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.name = name
        self.description = description
        self.updated_at = updated_at
        self.updated_by = updated_by


@cloudevent("accesspolicy.matchers.updated.v1")
@dataclass
class AccessPolicyMatchersUpdatedDomainEvent(DomainEvent):
    """Event raised when claim matchers are updated.

    This event replaces all existing matchers with the new list.
    For granular matcher changes, use add/remove matcher events.
    """

    aggregate_id: str
    claim_matchers: list[dict[str, Any]]  # Serialized ClaimMatcher list
    updated_at: datetime
    updated_by: str | None

    def __init__(
        self,
        aggregate_id: str,
        claim_matchers: list[dict[str, Any]],
        updated_at: datetime,
        updated_by: str | None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.claim_matchers = claim_matchers
        self.updated_at = updated_at
        self.updated_by = updated_by


@cloudevent("accesspolicy.groups.updated.v1")
@dataclass
class AccessPolicyGroupsUpdatedDomainEvent(DomainEvent):
    """Event raised when allowed group IDs are updated.

    This event replaces all existing group mappings with the new list.
    """

    aggregate_id: str
    allowed_group_ids: list[str]
    updated_at: datetime
    updated_by: str | None

    def __init__(
        self,
        aggregate_id: str,
        allowed_group_ids: list[str],
        updated_at: datetime,
        updated_by: str | None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.allowed_group_ids = allowed_group_ids
        self.updated_at = updated_at
        self.updated_by = updated_by


@cloudevent("accesspolicy.priority.updated.v1")
@dataclass
class AccessPolicyPriorityUpdatedDomainEvent(DomainEvent):
    """Event raised when policy priority is changed.

    Higher priority policies are evaluated first during access resolution.
    """

    aggregate_id: str
    old_priority: int
    new_priority: int
    updated_at: datetime
    updated_by: str | None

    def __init__(
        self,
        aggregate_id: str,
        old_priority: int,
        new_priority: int,
        updated_at: datetime,
        updated_by: str | None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.old_priority = old_priority
        self.new_priority = new_priority
        self.updated_at = updated_at
        self.updated_by = updated_by


@cloudevent("accesspolicy.activated.v1")
@dataclass
class AccessPolicyActivatedDomainEvent(DomainEvent):
    """Event raised when a policy is activated.

    Only active policies are evaluated during access resolution.
    """

    aggregate_id: str
    activated_at: datetime
    activated_by: str | None

    def __init__(
        self,
        aggregate_id: str,
        activated_at: datetime,
        activated_by: str | None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.activated_at = activated_at
        self.activated_by = activated_by


@cloudevent("accesspolicy.deactivated.v1")
@dataclass
class AccessPolicyDeactivatedDomainEvent(DomainEvent):
    """Event raised when a policy is deactivated.

    Deactivated policies are not evaluated during access resolution.
    """

    aggregate_id: str
    deactivated_at: datetime
    deactivated_by: str | None
    reason: str | None

    def __init__(
        self,
        aggregate_id: str,
        deactivated_at: datetime,
        deactivated_by: str | None,
        reason: str | None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.deactivated_at = deactivated_at
        self.deactivated_by = deactivated_by
        self.reason = reason


@cloudevent("accesspolicy.deleted.v1")
@dataclass
class AccessPolicyDeletedDomainEvent(DomainEvent):
    """Event raised when a policy is deleted.

    This marks the policy for removal. The actual deletion from the
    repository happens after this event is processed.
    """

    aggregate_id: str
    deleted_at: datetime
    deleted_by: str | None

    def __init__(
        self,
        aggregate_id: str,
        deleted_at: datetime,
        deleted_by: str | None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.deleted_at = deleted_at
        self.deleted_by = deleted_by
