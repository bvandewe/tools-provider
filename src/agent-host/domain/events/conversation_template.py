"""Domain events for ConversationTemplate aggregate.

All state changes to ConversationTemplate are captured as immutable domain events.
Events are decorated with @cloudevent for CloudEvent publishing via Mediator.

Event naming convention:
- {Aggregate}{Action}DomainEvent
- e.g., ConversationTemplateCreatedDomainEvent, ConversationTemplateItemAddedDomainEvent
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from neuroglia.data.abstractions import DomainEvent
from neuroglia.eventing.cloud_events.decorators import cloudevent

# =============================================================================
# LIFECYCLE EVENTS
# =============================================================================


@cloudevent("templates.created.v1")
@dataclass(kw_only=True)
class ConversationTemplateCreatedDomainEvent(DomainEvent[str]):
    """Raised when a new ConversationTemplate is created."""

    aggregate_id: str

    # Display
    name: str
    description: str | None = None

    # Flow Configuration
    agent_starts_first: bool = False
    allow_agent_switching: bool = False
    allow_navigation: bool = False
    allow_backward_navigation: bool = False
    enable_chat_input_initially: bool = True
    continue_after_completion: bool = False

    # Timing
    min_duration_seconds: int | None = None
    max_duration_seconds: int | None = None

    # Display Options
    shuffle_items: bool = False
    display_progress_indicator: bool = True
    display_item_score: bool = False
    display_item_title: bool = True
    display_final_score_report: bool = False
    include_feedback: bool = True
    append_items_to_view: bool = True

    # Messages
    introduction_message: str | None = None
    completion_message: str | None = None

    # Content (serialized to dicts for event storage)
    items: list[dict[str, Any]] = field(default_factory=list)

    # Scoring
    passing_score_percent: float | None = None

    # Audit
    created_by: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@cloudevent("templates.updated.v1")
@dataclass(kw_only=True)
class ConversationTemplateUpdatedDomainEvent(DomainEvent[str]):
    """Raised when a ConversationTemplate is updated (general update)."""

    aggregate_id: str

    # All optional - only provided fields are updated
    name: str | None = None
    description: str | None = None
    agent_starts_first: bool | None = None
    allow_agent_switching: bool | None = None
    allow_navigation: bool | None = None
    allow_backward_navigation: bool | None = None
    enable_chat_input_initially: bool | None = None
    continue_after_completion: bool | None = None
    min_duration_seconds: int | None = None
    max_duration_seconds: int | None = None
    shuffle_items: bool | None = None
    display_progress_indicator: bool | None = None
    display_item_score: bool | None = None
    display_item_title: bool | None = None
    display_final_score_report: bool | None = None
    include_feedback: bool | None = None
    append_items_to_view: bool | None = None
    introduction_message: str | None = None
    completion_message: str | None = None
    passing_score_percent: float | None = None

    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@cloudevent("templates.deleted.v1")
@dataclass(kw_only=True)
class ConversationTemplateDeletedDomainEvent(DomainEvent[str]):
    """Raised when a ConversationTemplate is deleted."""

    aggregate_id: str
    deleted_by: str | None = None
    deleted_at: datetime = field(default_factory=lambda: datetime.now(UTC))


# =============================================================================
# ITEM MANAGEMENT EVENTS
# =============================================================================


@cloudevent("templates.item_added.v1")
@dataclass(kw_only=True)
class ConversationTemplateItemAddedDomainEvent(DomainEvent[str]):
    """Raised when a ConversationItem is added to the template."""

    aggregate_id: str
    item: dict[str, Any]  # Serialized ConversationItem
    order: int  # Position in the items list
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@cloudevent("templates.item_updated.v1")
@dataclass(kw_only=True)
class ConversationTemplateItemUpdatedDomainEvent(DomainEvent[str]):
    """Raised when a ConversationItem is updated."""

    aggregate_id: str
    item_id: str  # ID of the updated item
    item: dict[str, Any]  # Serialized updated ConversationItem
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@cloudevent("templates.item_removed.v1")
@dataclass(kw_only=True)
class ConversationTemplateItemRemovedDomainEvent(DomainEvent[str]):
    """Raised when a ConversationItem is removed from the template."""

    aggregate_id: str
    item_id: str  # ID of the removed item
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@cloudevent("templates.items_reordered.v1")
@dataclass(kw_only=True)
class ConversationTemplateItemsReorderedDomainEvent(DomainEvent[str]):
    """Raised when the order of items is changed."""

    aggregate_id: str
    item_order: list[str]  # List of item IDs in new order
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


# =============================================================================
# FLOW CONFIGURATION EVENTS
# =============================================================================


@cloudevent("templates.flow_updated.v1")
@dataclass(kw_only=True)
class ConversationTemplateFlowUpdatedDomainEvent(DomainEvent[str]):
    """Raised when flow configuration is updated."""

    aggregate_id: str

    # All optional - only provided fields are updated
    agent_starts_first: bool | None = None
    allow_agent_switching: bool | None = None
    allow_navigation: bool | None = None
    allow_backward_navigation: bool | None = None
    enable_chat_input_initially: bool | None = None
    continue_after_completion: bool | None = None

    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@cloudevent("templates.timing_updated.v1")
@dataclass(kw_only=True)
class ConversationTemplateTimingUpdatedDomainEvent(DomainEvent[str]):
    """Raised when timing constraints are updated."""

    aggregate_id: str

    min_duration_seconds: int | None = None
    max_duration_seconds: int | None = None

    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@cloudevent("templates.display_updated.v1")
@dataclass(kw_only=True)
class ConversationTemplateDisplayUpdatedDomainEvent(DomainEvent[str]):
    """Raised when display options are updated."""

    aggregate_id: str

    # All optional - only provided fields are updated
    shuffle_items: bool | None = None
    display_progress_indicator: bool | None = None
    display_item_score: bool | None = None
    display_item_title: bool | None = None
    display_final_score_report: bool | None = None
    include_feedback: bool | None = None
    append_items_to_view: bool | None = None

    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@cloudevent("templates.messages_updated.v1")
@dataclass(kw_only=True)
class ConversationTemplateMessagesUpdatedDomainEvent(DomainEvent[str]):
    """Raised when introduction or completion messages are updated."""

    aggregate_id: str

    introduction_message: str | None = None
    completion_message: str | None = None

    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@cloudevent("templates.scoring_updated.v1")
@dataclass(kw_only=True)
class ConversationTemplateScoringUpdatedDomainEvent(DomainEvent[str]):
    """Raised when scoring configuration is updated."""

    aggregate_id: str

    passing_score_percent: float | None = None

    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
