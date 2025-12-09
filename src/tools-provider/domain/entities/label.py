"""Label aggregate definition using the AggregateState pattern.

Labels are user-defined categorizations for tools that:
- Persist across tool inventory refreshes (unlike OpenAPI tags)
- Can be assigned/removed by administrators
- Support filtering and organization in the UI
- Have visual styling (color) for better UX

This aggregate manages the lifecycle of labels themselves.
The association between labels and tools is managed via:
- SourceTool.label_ids (the tool aggregate)
- label_tools_command.py (for adding/removing)
"""

from datetime import UTC, datetime
from uuid import uuid4

from multipledispatch import dispatch
from neuroglia.data.abstractions import AggregateRoot, AggregateState

from domain.events.label import LabelCreatedDomainEvent, LabelDeletedDomainEvent, LabelUpdatedDomainEvent


class LabelState(AggregateState[str]):
    """Encapsulates the persisted state for the Label aggregate.

    Attributes:
        id: Unique identifier for this label
        name: Display name for the label
        description: Optional description of what tools should have this label
        color: CSS color for visual styling (e.g., "#6366f1", "blue", etc.)
        created_at: When the label was created
        updated_at: Last modification timestamp
        created_by: User who created the label
        is_deleted: Tombstone flag for soft deletion
    """

    # Identity
    id: str
    name: str
    description: str
    color: str

    # Lifecycle
    created_at: datetime
    updated_at: datetime
    created_by: str | None
    is_deleted: bool

    def __init__(self) -> None:
        super().__init__()
        # Initialize ALL fields with defaults (required by Neuroglia)
        self.id = ""
        self.name = ""
        self.description = ""
        self.color = "#6b7280"  # Default gray color

        now = datetime.now(UTC)
        self.created_at = now
        self.updated_at = now
        self.created_by = None
        self.is_deleted = False

    # =========================================================================
    # Event Handlers - Apply events to state
    # =========================================================================

    @dispatch(LabelCreatedDomainEvent)
    def on(self, event: LabelCreatedDomainEvent) -> None:  # type: ignore[override]
        """Apply the creation event to the state."""
        self.id = event.aggregate_id
        self.name = event.name
        self.description = event.description
        self.color = event.color
        self.created_at = event.created_at
        self.updated_at = event.created_at
        self.created_by = event.created_by
        self.is_deleted = False

    @dispatch(LabelUpdatedDomainEvent)
    def on(self, event: LabelUpdatedDomainEvent) -> None:  # type: ignore[override]
        """Apply the update event to the state."""
        if event.name is not None:
            self.name = event.name
        if event.description is not None:
            self.description = event.description
        if event.color is not None:
            self.color = event.color
        self.updated_at = event.updated_at

    @dispatch(LabelDeletedDomainEvent)
    def on(self, event: LabelDeletedDomainEvent) -> None:  # type: ignore[override]
        """Apply the deletion event to the state."""
        self.is_deleted = True
        self.updated_at = event.deleted_at


class Label(AggregateRoot[LabelState, str]):
    """Label aggregate root.

    Manages the lifecycle of a label entity through commands and events.
    """

    def __init__(self) -> None:
        super().__init__()

    # =========================================================================
    # Factory Methods
    # =========================================================================

    @classmethod
    def create(
        cls,
        name: str,
        description: str = "",
        color: str = "#6b7280",
        label_id: str | None = None,
        created_by: str | None = None,
    ) -> "Label":
        """Factory method to create a new Label.

        Args:
            name: Display name for the label
            description: Optional description
            color: CSS color for visual styling
            label_id: Optional explicit ID (auto-generated if not provided)
            created_by: User who created the label

        Returns:
            A new Label instance with the creation event registered
        """
        label = cls()
        label_id = label_id or str(uuid4())

        event = LabelCreatedDomainEvent(
            aggregate_id=label_id,
            name=name,
            description=description,
            color=color,
            created_at=datetime.now(UTC),
            created_by=created_by,
        )

        label.state.on(label.register_event(event))  # type: ignore

        return label

    # =========================================================================
    # Command Methods
    # =========================================================================

    def update(
        self,
        name: str | None = None,
        description: str | None = None,
        color: str | None = None,
        updated_by: str | None = None,
    ) -> None:
        """Update the label's properties.

        Args:
            name: New name (if provided)
            description: New description (if provided)
            color: New color (if provided)
            updated_by: User making the change
        """
        if self.state.is_deleted:
            raise ValueError("Cannot update a deleted label")

        # Only emit event if something changed
        if name is None and description is None and color is None:
            return

        event = LabelUpdatedDomainEvent(
            aggregate_id=self.id(),
            name=name,
            description=description,
            color=color,
            updated_at=datetime.now(UTC),
            updated_by=updated_by,
        )

        self.state.on(self.register_event(event))  # type: ignore

    def delete(self, deleted_by: str | None = None) -> None:
        """Mark this label as deleted.

        This is a soft delete - the label remains in the event store
        but is marked as deleted. A separate process should handle
        removing this label from all tools.

        Args:
            deleted_by: User performing the deletion
        """
        if self.state.is_deleted:
            return  # Already deleted, no-op

        event = LabelDeletedDomainEvent(
            aggregate_id=self.id(),
            deleted_at=datetime.now(UTC),
            deleted_by=deleted_by,
        )

        self.state.on(self.register_event(event))  # type: ignore

    # =========================================================================
    # Property Accessors
    # =========================================================================

    def id(self) -> str:
        """Return the aggregate identifier."""
        aggregate_id = super().id()
        if aggregate_id is None:
            raise ValueError("Label aggregate identifier has not been initialized")
        return str(aggregate_id)

    @property
    def name(self) -> str:
        return self.state.name

    @property
    def description(self) -> str:
        return self.state.description

    @property
    def color(self) -> str:
        return self.state.color

    @property
    def is_deleted(self) -> bool:
        return self.state.is_deleted
