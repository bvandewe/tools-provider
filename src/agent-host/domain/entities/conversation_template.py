"""ConversationTemplate aggregate definition using the AggregateState pattern.

DomainEvents are appended/aggregated in the ConversationTemplate and the
repository publishes them via Mediator after the ConversationTemplate was persisted.

ConversationTemplate is a first-class AggregateRoot that defines:
- Conversation flow behavior (who speaks first, navigation rules)
- Timing constraints (min/max duration)
- Display options (progress indicator, scoring display)
- Content structure (ordered ConversationItems)

This replaces the previous state-based dataclass in domain/models/.
"""

from datetime import UTC, datetime
from typing import Any, cast
from uuid import uuid4

from multipledispatch import dispatch
from neuroglia.data.abstractions import AggregateRoot, AggregateState
from neuroglia.mapping.mapper import map_to

from domain.events.conversation_template import (
    ConversationTemplateCreatedDomainEvent,
    ConversationTemplateDeletedDomainEvent,
    ConversationTemplateDisplayUpdatedDomainEvent,
    ConversationTemplateFlowUpdatedDomainEvent,
    ConversationTemplateItemAddedDomainEvent,
    ConversationTemplateItemRemovedDomainEvent,
    ConversationTemplateItemsReorderedDomainEvent,
    ConversationTemplateItemUpdatedDomainEvent,
    ConversationTemplateMessagesUpdatedDomainEvent,
    ConversationTemplateScoringUpdatedDomainEvent,
    ConversationTemplateTimingUpdatedDomainEvent,
    ConversationTemplateUpdatedDomainEvent,
)
from domain.models.conversation_item import ConversationItem
from integration.models.template_dto import ConversationTemplateDto


@map_to(ConversationTemplateDto)
class ConversationTemplateState(AggregateState[str]):
    """Encapsulates the persisted state for the ConversationTemplate aggregate.

    This state is rebuilt from events (event sourcing).
    """

    # Identity
    id: str
    name: str
    description: str | None

    # Flow Configuration
    agent_starts_first: bool
    allow_agent_switching: bool
    allow_navigation: bool
    allow_backward_navigation: bool
    enable_chat_input_initially: bool
    continue_after_completion: bool

    # Timing
    min_duration_seconds: int | None
    max_duration_seconds: int | None

    # Display Options
    shuffle_items: bool
    display_progress_indicator: bool
    display_item_score: bool
    display_item_title: bool
    display_final_score_report: bool
    include_feedback: bool
    append_items_to_view: bool

    # Messages
    introduction_message: str | None
    completion_message: str | None

    # Content
    items: list[ConversationItem]

    # Scoring
    passing_score_percent: float | None

    # Audit
    created_by: str
    created_at: datetime
    updated_at: datetime
    version: int

    def __init__(self) -> None:
        super().__init__()
        self.id = ""
        self.name = ""
        self.description = None
        self.agent_starts_first = False
        self.allow_agent_switching = False
        self.allow_navigation = False
        self.allow_backward_navigation = False
        self.enable_chat_input_initially = True
        self.continue_after_completion = False
        self.min_duration_seconds = None
        self.max_duration_seconds = None
        self.shuffle_items = False
        self.display_progress_indicator = True
        self.display_item_score = False
        self.display_item_title = True
        self.display_final_score_report = False
        self.include_feedback = True
        self.append_items_to_view = True
        self.introduction_message = None
        self.completion_message = None
        self.items = []
        self.passing_score_percent = None
        self.created_by = ""
        now = datetime.now(UTC)
        self.created_at = now
        self.updated_at = now
        self.version = 1

    @dispatch(ConversationTemplateCreatedDomainEvent)
    def on(self, event: ConversationTemplateCreatedDomainEvent) -> None:  # type: ignore[override]
        """Apply the creation event to the state."""
        self.id = event.aggregate_id
        self.name = event.name
        self.description = event.description
        self.agent_starts_first = event.agent_starts_first
        self.allow_agent_switching = event.allow_agent_switching
        self.allow_navigation = event.allow_navigation
        self.allow_backward_navigation = event.allow_backward_navigation
        self.enable_chat_input_initially = event.enable_chat_input_initially
        self.continue_after_completion = event.continue_after_completion
        self.min_duration_seconds = event.min_duration_seconds
        self.max_duration_seconds = event.max_duration_seconds
        self.shuffle_items = event.shuffle_items
        self.display_progress_indicator = event.display_progress_indicator
        self.display_item_score = event.display_item_score
        self.display_item_title = event.display_item_title
        self.display_final_score_report = event.display_final_score_report
        self.include_feedback = event.include_feedback
        self.append_items_to_view = event.append_items_to_view
        self.introduction_message = event.introduction_message
        self.completion_message = event.completion_message
        self.items = [ConversationItem.from_dict(item) for item in event.items]
        self.passing_score_percent = event.passing_score_percent
        self.created_by = event.created_by
        self.created_at = event.created_at
        self.updated_at = event.updated_at

    @dispatch(ConversationTemplateUpdatedDomainEvent)
    def on(self, event: ConversationTemplateUpdatedDomainEvent) -> None:  # type: ignore[override]
        """Apply a general update event to the state."""
        if event.name is not None:
            self.name = event.name
        if event.description is not None:
            self.description = event.description
        if event.agent_starts_first is not None:
            self.agent_starts_first = event.agent_starts_first
        if event.allow_agent_switching is not None:
            self.allow_agent_switching = event.allow_agent_switching
        if event.allow_navigation is not None:
            self.allow_navigation = event.allow_navigation
        if event.allow_backward_navigation is not None:
            self.allow_backward_navigation = event.allow_backward_navigation
        if event.enable_chat_input_initially is not None:
            self.enable_chat_input_initially = event.enable_chat_input_initially
        if event.continue_after_completion is not None:
            self.continue_after_completion = event.continue_after_completion
        if event.min_duration_seconds is not None:
            self.min_duration_seconds = event.min_duration_seconds
        if event.max_duration_seconds is not None:
            self.max_duration_seconds = event.max_duration_seconds
        if event.shuffle_items is not None:
            self.shuffle_items = event.shuffle_items
        if event.display_progress_indicator is not None:
            self.display_progress_indicator = event.display_progress_indicator
        if event.display_item_score is not None:
            self.display_item_score = event.display_item_score
        if event.display_item_title is not None:
            self.display_item_title = event.display_item_title
        if event.display_final_score_report is not None:
            self.display_final_score_report = event.display_final_score_report
        if event.include_feedback is not None:
            self.include_feedback = event.include_feedback
        if event.append_items_to_view is not None:
            self.append_items_to_view = event.append_items_to_view
        if event.introduction_message is not None:
            self.introduction_message = event.introduction_message
        if event.completion_message is not None:
            self.completion_message = event.completion_message
        if event.passing_score_percent is not None:
            self.passing_score_percent = event.passing_score_percent
        self.updated_at = event.updated_at
        self.version += 1

    @dispatch(ConversationTemplateFlowUpdatedDomainEvent)
    def on(self, event: ConversationTemplateFlowUpdatedDomainEvent) -> None:  # type: ignore[override]
        """Apply the flow update event to the state."""
        if event.agent_starts_first is not None:
            self.agent_starts_first = event.agent_starts_first
        if event.allow_agent_switching is not None:
            self.allow_agent_switching = event.allow_agent_switching
        if event.allow_navigation is not None:
            self.allow_navigation = event.allow_navigation
        if event.allow_backward_navigation is not None:
            self.allow_backward_navigation = event.allow_backward_navigation
        if event.enable_chat_input_initially is not None:
            self.enable_chat_input_initially = event.enable_chat_input_initially
        if event.continue_after_completion is not None:
            self.continue_after_completion = event.continue_after_completion
        self.updated_at = event.updated_at
        self.version += 1

    @dispatch(ConversationTemplateTimingUpdatedDomainEvent)
    def on(self, event: ConversationTemplateTimingUpdatedDomainEvent) -> None:  # type: ignore[override]
        """Apply the timing update event to the state."""
        if event.min_duration_seconds is not None:
            self.min_duration_seconds = event.min_duration_seconds
        if event.max_duration_seconds is not None:
            self.max_duration_seconds = event.max_duration_seconds
        self.updated_at = event.updated_at
        self.version += 1

    @dispatch(ConversationTemplateDisplayUpdatedDomainEvent)
    def on(self, event: ConversationTemplateDisplayUpdatedDomainEvent) -> None:  # type: ignore[override]
        """Apply the display update event to the state."""
        if event.shuffle_items is not None:
            self.shuffle_items = event.shuffle_items
        if event.display_progress_indicator is not None:
            self.display_progress_indicator = event.display_progress_indicator
        if event.display_item_score is not None:
            self.display_item_score = event.display_item_score
        if event.display_item_title is not None:
            self.display_item_title = event.display_item_title
        if event.display_final_score_report is not None:
            self.display_final_score_report = event.display_final_score_report
        if event.include_feedback is not None:
            self.include_feedback = event.include_feedback
        if event.append_items_to_view is not None:
            self.append_items_to_view = event.append_items_to_view
        self.updated_at = event.updated_at
        self.version += 1

    @dispatch(ConversationTemplateMessagesUpdatedDomainEvent)
    def on(self, event: ConversationTemplateMessagesUpdatedDomainEvent) -> None:  # type: ignore[override]
        """Apply the messages update event to the state."""
        if event.introduction_message is not None:
            self.introduction_message = event.introduction_message
        if event.completion_message is not None:
            self.completion_message = event.completion_message
        self.updated_at = event.updated_at
        self.version += 1

    @dispatch(ConversationTemplateScoringUpdatedDomainEvent)
    def on(self, event: ConversationTemplateScoringUpdatedDomainEvent) -> None:  # type: ignore[override]
        """Apply the scoring update event to the state."""
        if event.passing_score_percent is not None:
            self.passing_score_percent = event.passing_score_percent
        self.updated_at = event.updated_at
        self.version += 1

    @dispatch(ConversationTemplateItemAddedDomainEvent)
    def on(self, event: ConversationTemplateItemAddedDomainEvent) -> None:  # type: ignore[override]
        """Apply the item added event to the state."""
        item = ConversationItem.from_dict(event.item)
        if event.order >= len(self.items):
            self.items.append(item)
        else:
            self.items.insert(event.order, item)
        self.updated_at = event.updated_at
        self.version += 1

    @dispatch(ConversationTemplateItemUpdatedDomainEvent)
    def on(self, event: ConversationTemplateItemUpdatedDomainEvent) -> None:  # type: ignore[override]
        """Apply the item updated event to the state."""
        for i, item in enumerate(self.items):
            if item.id == event.item_id:
                self.items[i] = ConversationItem.from_dict(event.item)
                break
        self.updated_at = event.updated_at
        self.version += 1

    @dispatch(ConversationTemplateItemRemovedDomainEvent)
    def on(self, event: ConversationTemplateItemRemovedDomainEvent) -> None:  # type: ignore[override]
        """Apply the item removed event to the state."""
        self.items = [item for item in self.items if item.id != event.item_id]
        self.updated_at = event.updated_at
        self.version += 1

    @dispatch(ConversationTemplateItemsReorderedDomainEvent)
    def on(self, event: ConversationTemplateItemsReorderedDomainEvent) -> None:  # type: ignore[override]
        """Apply the items reordered event to the state."""
        # Create a lookup dictionary
        item_dict = {item.id: item for item in self.items}
        # Reorder based on the new order list
        self.items = [item_dict[item_id] for item_id in event.item_order if item_id in item_dict]
        self.updated_at = event.updated_at
        self.version += 1

    @dispatch(ConversationTemplateDeletedDomainEvent)
    def on(self, event: ConversationTemplateDeletedDomainEvent) -> None:  # type: ignore[override]
        """Apply the deleted event to the state."""
        self.updated_at = event.deleted_at
        # Note: Actual deletion handled by repository


class ConversationTemplate(AggregateRoot[ConversationTemplateState, str]):
    """ConversationTemplate aggregate root following the AggregateState pattern.

    Represents the configuration that defines conversation flow and structure.
    All state changes are captured as domain events.
    """

    def __init__(
        self,
        name: str,
        template_id: str | None = None,
        description: str | None = None,
        agent_starts_first: bool = False,
        allow_agent_switching: bool = False,
        allow_navigation: bool = False,
        allow_backward_navigation: bool = False,
        enable_chat_input_initially: bool = True,
        continue_after_completion: bool = False,
        min_duration_seconds: int | None = None,
        max_duration_seconds: int | None = None,
        shuffle_items: bool = False,
        display_progress_indicator: bool = True,
        display_item_score: bool = False,
        display_item_title: bool = True,
        display_final_score_report: bool = False,
        include_feedback: bool = True,
        append_items_to_view: bool = True,
        introduction_message: str | None = None,
        completion_message: str | None = None,
        items: list[ConversationItem] | None = None,
        passing_score_percent: float | None = None,
        created_by: str = "",
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        super().__init__()
        aggregate_id = template_id or str(uuid4())
        created_time = created_at or datetime.now(UTC)
        updated_time = updated_at or created_time

        # Serialize items to dicts for event storage
        items_dicts = [item.to_dict() for item in items] if items else []

        self.state.on(
            self.register_event(  # type: ignore
                ConversationTemplateCreatedDomainEvent(
                    aggregate_id=aggregate_id,
                    name=name,
                    description=description,
                    agent_starts_first=agent_starts_first,
                    allow_agent_switching=allow_agent_switching,
                    allow_navigation=allow_navigation,
                    allow_backward_navigation=allow_backward_navigation,
                    enable_chat_input_initially=enable_chat_input_initially,
                    continue_after_completion=continue_after_completion,
                    min_duration_seconds=min_duration_seconds,
                    max_duration_seconds=max_duration_seconds,
                    shuffle_items=shuffle_items,
                    display_progress_indicator=display_progress_indicator,
                    display_item_score=display_item_score,
                    display_item_title=display_item_title,
                    display_final_score_report=display_final_score_report,
                    include_feedback=include_feedback,
                    append_items_to_view=append_items_to_view,
                    introduction_message=introduction_message,
                    completion_message=completion_message,
                    items=items_dicts,
                    passing_score_percent=passing_score_percent,
                    created_by=created_by,
                    created_at=created_time,
                    updated_at=updated_time,
                )
            )
        )

    def id(self) -> str:
        """Return the aggregate identifier with a precise type."""
        aggregate_id = super().id()
        if aggregate_id is None:
            raise ValueError("ConversationTemplate aggregate identifier has not been initialized")
        return cast(str, aggregate_id)

    # =========================================================================
    # UPDATE METHODS
    # =========================================================================

    def update(
        self,
        name: str | None = None,
        description: str | None = None,
        agent_starts_first: bool | None = None,
        allow_agent_switching: bool | None = None,
        allow_navigation: bool | None = None,
        allow_backward_navigation: bool | None = None,
        enable_chat_input_initially: bool | None = None,
        continue_after_completion: bool | None = None,
        min_duration_seconds: int | None = None,
        max_duration_seconds: int | None = None,
        shuffle_items: bool | None = None,
        display_progress_indicator: bool | None = None,
        display_item_score: bool | None = None,
        display_item_title: bool | None = None,
        display_final_score_report: bool | None = None,
        include_feedback: bool | None = None,
        append_items_to_view: bool | None = None,
        introduction_message: str | None = None,
        completion_message: str | None = None,
        passing_score_percent: float | None = None,
    ) -> bool:
        """Apply a general update to the template."""
        # Only emit event if at least one field is provided
        all_fields = [
            name,
            description,
            agent_starts_first,
            allow_agent_switching,
            allow_navigation,
            allow_backward_navigation,
            enable_chat_input_initially,
            continue_after_completion,
            min_duration_seconds,
            max_duration_seconds,
            shuffle_items,
            display_progress_indicator,
            display_item_score,
            display_item_title,
            display_final_score_report,
            include_feedback,
            append_items_to_view,
            introduction_message,
            completion_message,
            passing_score_percent,
        ]
        if all(v is None for v in all_fields):
            return False

        self.state.on(
            self.register_event(  # type: ignore
                ConversationTemplateUpdatedDomainEvent(
                    aggregate_id=self.id(),
                    name=name,
                    description=description,
                    agent_starts_first=agent_starts_first,
                    allow_agent_switching=allow_agent_switching,
                    allow_navigation=allow_navigation,
                    allow_backward_navigation=allow_backward_navigation,
                    enable_chat_input_initially=enable_chat_input_initially,
                    continue_after_completion=continue_after_completion,
                    min_duration_seconds=min_duration_seconds,
                    max_duration_seconds=max_duration_seconds,
                    shuffle_items=shuffle_items,
                    display_progress_indicator=display_progress_indicator,
                    display_item_score=display_item_score,
                    display_item_title=display_item_title,
                    display_final_score_report=display_final_score_report,
                    include_feedback=include_feedback,
                    append_items_to_view=append_items_to_view,
                    introduction_message=introduction_message,
                    completion_message=completion_message,
                    passing_score_percent=passing_score_percent,
                )
            )
        )
        return True

    def update_flow(
        self,
        agent_starts_first: bool | None = None,
        allow_agent_switching: bool | None = None,
        allow_navigation: bool | None = None,
        allow_backward_navigation: bool | None = None,
        enable_chat_input_initially: bool | None = None,
        continue_after_completion: bool | None = None,
    ) -> bool:
        """Update flow configuration."""
        if all(v is None for v in [agent_starts_first, allow_agent_switching, allow_navigation, allow_backward_navigation, enable_chat_input_initially, continue_after_completion]):
            return False

        self.state.on(
            self.register_event(  # type: ignore
                ConversationTemplateFlowUpdatedDomainEvent(
                    aggregate_id=self.id(),
                    agent_starts_first=agent_starts_first,
                    allow_agent_switching=allow_agent_switching,
                    allow_navigation=allow_navigation,
                    allow_backward_navigation=allow_backward_navigation,
                    enable_chat_input_initially=enable_chat_input_initially,
                    continue_after_completion=continue_after_completion,
                )
            )
        )
        return True

    def update_timing(
        self,
        min_duration_seconds: int | None = None,
        max_duration_seconds: int | None = None,
    ) -> bool:
        """Update timing constraints."""
        if min_duration_seconds is None and max_duration_seconds is None:
            return False

        self.state.on(
            self.register_event(  # type: ignore
                ConversationTemplateTimingUpdatedDomainEvent(
                    aggregate_id=self.id(),
                    min_duration_seconds=min_duration_seconds,
                    max_duration_seconds=max_duration_seconds,
                )
            )
        )
        return True

    def update_display(
        self,
        shuffle_items: bool | None = None,
        display_progress_indicator: bool | None = None,
        display_item_score: bool | None = None,
        display_item_title: bool | None = None,
        display_final_score_report: bool | None = None,
        include_feedback: bool | None = None,
        append_items_to_view: bool | None = None,
    ) -> bool:
        """Update display options."""
        if all(v is None for v in [shuffle_items, display_progress_indicator, display_item_score, display_item_title, display_final_score_report, include_feedback, append_items_to_view]):
            return False

        self.state.on(
            self.register_event(  # type: ignore
                ConversationTemplateDisplayUpdatedDomainEvent(
                    aggregate_id=self.id(),
                    shuffle_items=shuffle_items,
                    display_progress_indicator=display_progress_indicator,
                    display_item_score=display_item_score,
                    display_item_title=display_item_title,
                    display_final_score_report=display_final_score_report,
                    include_feedback=include_feedback,
                    append_items_to_view=append_items_to_view,
                )
            )
        )
        return True

    def update_messages(
        self,
        introduction_message: str | None = None,
        completion_message: str | None = None,
    ) -> bool:
        """Update introduction or completion messages."""
        if introduction_message is None and completion_message is None:
            return False

        self.state.on(
            self.register_event(  # type: ignore
                ConversationTemplateMessagesUpdatedDomainEvent(
                    aggregate_id=self.id(),
                    introduction_message=introduction_message,
                    completion_message=completion_message,
                )
            )
        )
        return True

    def update_scoring(self, passing_score_percent: float | None = None) -> bool:
        """Update scoring configuration."""
        if passing_score_percent is None:
            return False

        self.state.on(
            self.register_event(  # type: ignore
                ConversationTemplateScoringUpdatedDomainEvent(
                    aggregate_id=self.id(),
                    passing_score_percent=passing_score_percent,
                )
            )
        )
        return True

    # =========================================================================
    # ITEM MANAGEMENT METHODS
    # =========================================================================

    def add_item(self, item: ConversationItem, order: int | None = None) -> bool:
        """Add an item to the template."""
        actual_order = order if order is not None else len(self.state.items)

        self.state.on(
            self.register_event(  # type: ignore
                ConversationTemplateItemAddedDomainEvent(
                    aggregate_id=self.id(),
                    item=item.to_dict(),
                    order=actual_order,
                )
            )
        )
        return True

    def update_item(self, item_id: str, updated_item: ConversationItem) -> bool:
        """Update an existing item."""
        # Verify item exists
        if not any(item.id == item_id for item in self.state.items):
            return False

        self.state.on(
            self.register_event(  # type: ignore
                ConversationTemplateItemUpdatedDomainEvent(
                    aggregate_id=self.id(),
                    item_id=item_id,
                    item=updated_item.to_dict(),
                )
            )
        )
        return True

    def remove_item(self, item_id: str) -> bool:
        """Remove an item from the template."""
        # Verify item exists
        if not any(item.id == item_id for item in self.state.items):
            return False

        self.state.on(
            self.register_event(  # type: ignore
                ConversationTemplateItemRemovedDomainEvent(
                    aggregate_id=self.id(),
                    item_id=item_id,
                )
            )
        )
        return True

    def reorder_items(self, item_order: list[str]) -> bool:
        """Reorder items by providing the new order of item IDs."""
        if not item_order:
            return False

        self.state.on(
            self.register_event(  # type: ignore
                ConversationTemplateItemsReorderedDomainEvent(
                    aggregate_id=self.id(),
                    item_order=item_order,
                )
            )
        )
        return True

    def delete(self, deleted_by: str | None = None) -> None:
        """Mark the template as deleted."""
        self.state.on(
            self.register_event(  # type: ignore
                ConversationTemplateDeletedDomainEvent(
                    aggregate_id=self.id(),
                    deleted_by=deleted_by,
                )
            )
        )

    # =========================================================================
    # QUERY PROPERTIES (delegating to state)
    # =========================================================================

    @property
    def name(self) -> str:
        """Get the template name."""
        return self.state.name

    @property
    def description(self) -> str | None:
        """Get the template description."""
        return self.state.description

    @property
    def agent_starts_first(self) -> bool:
        """Check if agent speaks first."""
        return self.state.agent_starts_first

    @property
    def continue_after_completion(self) -> bool:
        """Check if free chat continues after template completion."""
        return self.state.continue_after_completion

    @property
    def items(self) -> list[ConversationItem]:
        """Get the list of items."""
        return self.state.items.copy()

    @property
    def item_count(self) -> int:
        """Get the number of items in the template."""
        return len(self.state.items)

    @property
    def is_proactive(self) -> bool:
        """Check if this template defines a proactive conversation."""
        return self.state.agent_starts_first

    @property
    def is_reactive(self) -> bool:
        """Check if this template defines a reactive conversation."""
        return not self.state.agent_starts_first

    @property
    def is_assessment(self) -> bool:
        """Check if this template is an assessment (has passing score)."""
        return self.state.passing_score_percent is not None

    @property
    def has_time_limit(self) -> bool:
        """Check if this template has a time limit."""
        return self.state.max_duration_seconds is not None and self.state.max_duration_seconds > 0

    @property
    def max_possible_score(self) -> float:
        """Get the maximum possible score across all items."""
        return sum(item.max_possible_score for item in self.state.items)

    def get_item_at(self, index: int) -> ConversationItem | None:
        """Get item at a specific index (0-indexed)."""
        if 0 <= index < len(self.state.items):
            return self.state.items[index]
        return None

    def get_item_by_id(self, item_id: str) -> ConversationItem | None:
        """Get an item by its ID."""
        for item in self.state.items:
            if item.id == item_id:
                return item
        return None

    def get_sorted_items(self) -> list[ConversationItem]:
        """Get items sorted by order."""
        return sorted(self.state.items, key=lambda item: item.order)

    def is_complete(self, current_index: int) -> bool:
        """Check if all items have been completed based on index."""
        return current_index >= len(self.state.items)

    def get_next_item(self, current_index: int) -> ConversationItem | None:
        """Get the next item after the current index."""
        return self.get_item_at(current_index + 1)

    def get_previous_item(self, current_index: int) -> ConversationItem | None:
        """Get the previous item before the current index."""
        if current_index > 0:
            return self.get_item_at(current_index - 1)
        return None

    # =========================================================================
    # SERIALIZATION (for compatibility with existing code paths)
    # =========================================================================

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id(),
            "name": self.state.name,
            "description": self.state.description,
            "agent_starts_first": self.state.agent_starts_first,
            "allow_agent_switching": self.state.allow_agent_switching,
            "allow_navigation": self.state.allow_navigation,
            "allow_backward_navigation": self.state.allow_backward_navigation,
            "enable_chat_input_initially": self.state.enable_chat_input_initially,
            "continue_after_completion": self.state.continue_after_completion,
            "min_duration_seconds": self.state.min_duration_seconds,
            "max_duration_seconds": self.state.max_duration_seconds,
            "shuffle_items": self.state.shuffle_items,
            "display_progress_indicator": self.state.display_progress_indicator,
            "display_item_score": self.state.display_item_score,
            "display_item_title": self.state.display_item_title,
            "display_final_score_report": self.state.display_final_score_report,
            "include_feedback": self.state.include_feedback,
            "append_items_to_view": self.state.append_items_to_view,
            "introduction_message": self.state.introduction_message,
            "completion_message": self.state.completion_message,
            "items": [item.to_dict() for item in self.state.items],
            "passing_score_percent": self.state.passing_score_percent,
            "created_by": self.state.created_by,
            "created_at": self.state.created_at.isoformat() if self.state.created_at else None,
            "updated_at": self.state.updated_at.isoformat() if self.state.updated_at else None,
            "version": self.state.version,
        }

    def to_client_dict(self) -> dict[str, Any]:
        """Convert to dictionary safe for client (excludes correct_answer)."""
        return {
            "id": self.id(),
            "name": self.state.name,
            "description": self.state.description,
            "agent_starts_first": self.state.agent_starts_first,
            "allow_agent_switching": self.state.allow_agent_switching,
            "allow_navigation": self.state.allow_navigation,
            "allow_backward_navigation": self.state.allow_backward_navigation,
            "enable_chat_input_initially": self.state.enable_chat_input_initially,
            "continue_after_completion": self.state.continue_after_completion,
            "min_duration_seconds": self.state.min_duration_seconds,
            "max_duration_seconds": self.state.max_duration_seconds,
            "shuffle_items": self.state.shuffle_items,
            "display_progress_indicator": self.state.display_progress_indicator,
            "display_item_score": self.state.display_item_score,
            "display_item_title": self.state.display_item_title,
            "display_final_score_report": self.state.display_final_score_report,
            "include_feedback": self.state.include_feedback,
            "append_items_to_view": self.state.append_items_to_view,
            "introduction_message": self.state.introduction_message,
            "completion_message": self.state.completion_message,
            "items": [item.to_client_dict() for item in self.state.items],
            "passing_score_percent": self.state.passing_score_percent,
            "created_by": self.state.created_by,
            "created_at": self.state.created_at.isoformat() if self.state.created_at else None,
            "updated_at": self.state.updated_at.isoformat() if self.state.updated_at else None,
            "version": self.state.version,
        }
