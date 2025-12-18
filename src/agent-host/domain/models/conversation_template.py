"""Conversation Template models. !!! DEPRECATED, SUPERSEDED BY CONVERSATION TEMPLATE AGGREGATE !!! TODO: remove!

ConversationTemplate defines the structure and flow of a conversation.
It contains ConversationItems, each with ItemContents that can be static
or templated (referencing SkillTemplates for LLM-generated content).

Hierarchy:
    ConversationTemplate → ConversationItem[] → ItemContent[]

Templates are stored in MongoDB and referenced by AgentDefinitions.
When an AgentDefinition has a template, it becomes a "proactive" agent
(agent_starts_first is controlled by the template, not the definition).
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from neuroglia.data.abstractions import Identifiable, queryable

from domain.models.conversation_item import ConversationItem

# Forward reference for DTO (resolved at import time)
# from integration.models.template_dto import ConversationTemplateDto


@queryable
@dataclass
class ConversationTemplate(Identifiable[str]):
    """Template defining conversation structure and flow.

    This is a configuration entity stored in MongoDB. It defines:
    - Flow behavior (who speaks first, navigation rules)
    - Timing constraints (min/max duration)
    - Display options (progress indicator, scoring display)
    - Content structure (ordered ConversationItems)

    When an AgentDefinition references a template, the template's
    agent_starts_first determines conversation behavior.

    Attributes:
        id: Unique identifier (slug or UUID). Immutable after creation.
        name: Display name for admin UI
        description: Longer description for admin UI
        agent_starts_first: If True, agent sends first message
        allow_agent_switching: If True, user can switch agents mid-conversation
        allow_navigation: If True, user can jump between items
        allow_backward_navigation: If True, user can go back to previous items
        enable_chat_input_initially: If True, chat input enabled at start
        min_duration_seconds: Minimum time before completion allowed
        max_duration_seconds: Maximum time for entire conversation
        shuffle_items: If True, randomize item order
        display_progress_indicator: If True, show progress bar
        display_item_score: If True, show score for each item
        display_item_title: If True, show item titles
        display_final_score_report: If True, show final score summary
        include_feedback: If True, provide feedback after responses
        append_items_to_view: If True, keep previous items visible
        introduction_message: Message shown at conversation start
        completion_message: Message shown on completion
        items: Ordered list of ConversationItems
        passing_score_percent: Score needed to pass (for assessments)
        created_by: User who created this template
        created_at: Creation timestamp
        updated_at: Last modification timestamp
        version: Version for optimistic concurrency
    """

    # Identity
    id: str
    name: str = ""
    description: str | None = None

    # Flow Configuration
    agent_starts_first: bool = False
    allow_agent_switching: bool = False
    allow_navigation: bool = False
    allow_backward_navigation: bool = False
    enable_chat_input_initially: bool = True
    continue_after_completion: bool = False  # If True, allow free chat after last item

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
    append_items_to_view: bool = True  # False = hide previous items

    # Messages
    introduction_message: str | None = None
    completion_message: str | None = None

    # Content
    items: list[ConversationItem] = field(default_factory=list)

    # Scoring (for assessments)
    passing_score_percent: float | None = None

    # Audit
    created_by: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    version: int = 1

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for MongoDB storage.

        Note: Uses items.to_dict() which includes correct_answer.
        Use to_client_dict() for client-safe representation.
        """
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "agent_starts_first": self.agent_starts_first,
            "allow_agent_switching": self.allow_agent_switching,
            "allow_navigation": self.allow_navigation,
            "allow_backward_navigation": self.allow_backward_navigation,
            "enable_chat_input_initially": self.enable_chat_input_initially,
            "continue_after_completion": self.continue_after_completion,
            "min_duration_seconds": self.min_duration_seconds,
            "max_duration_seconds": self.max_duration_seconds,
            "shuffle_items": self.shuffle_items,
            "display_progress_indicator": self.display_progress_indicator,
            "display_item_score": self.display_item_score,
            "display_item_title": self.display_item_title,
            "display_final_score_report": self.display_final_score_report,
            "include_feedback": self.include_feedback,
            "append_items_to_view": self.append_items_to_view,
            "introduction_message": self.introduction_message,
            "completion_message": self.completion_message,
            "items": [item.to_dict() for item in self.items],
            "passing_score_percent": self.passing_score_percent,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "version": self.version,
        }

    def to_client_dict(self) -> dict[str, Any]:
        """Convert to dictionary safe for client.

        Excludes correct_answer from items/contents to prevent cheating.
        """
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "agent_starts_first": self.agent_starts_first,
            "allow_agent_switching": self.allow_agent_switching,
            "allow_navigation": self.allow_navigation,
            "allow_backward_navigation": self.allow_backward_navigation,
            "enable_chat_input_initially": self.enable_chat_input_initially,
            "continue_after_completion": self.continue_after_completion,
            "min_duration_seconds": self.min_duration_seconds,
            "max_duration_seconds": self.max_duration_seconds,
            "shuffle_items": self.shuffle_items,
            "display_progress_indicator": self.display_progress_indicator,
            "display_item_score": self.display_item_score,
            "display_item_title": self.display_item_title,
            "display_final_score_report": self.display_final_score_report,
            "include_feedback": self.include_feedback,
            "append_items_to_view": self.append_items_to_view,
            "introduction_message": self.introduction_message,
            "completion_message": self.completion_message,
            "items": [item.to_client_dict() for item in self.items],
            "passing_score_percent": self.passing_score_percent,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConversationTemplate":
        """Create from dictionary (MongoDB document or YAML)."""
        created_at = data.get("created_at")
        updated_at = data.get("updated_at")

        # Handle datetime parsing
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))

        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description"),
            agent_starts_first=data.get("agent_starts_first", False),
            allow_agent_switching=data.get("allow_agent_switching", False),
            allow_navigation=data.get("allow_navigation", False),
            allow_backward_navigation=data.get("allow_backward_navigation", False),
            enable_chat_input_initially=data.get("enable_chat_input_initially", True),
            continue_after_completion=data.get("continue_after_completion", False),
            min_duration_seconds=data.get("min_duration_seconds"),
            max_duration_seconds=data.get("max_duration_seconds"),
            shuffle_items=data.get("shuffle_items", False),
            display_progress_indicator=data.get("display_progress_indicator", True),
            display_item_score=data.get("display_item_score", False),
            display_item_title=data.get("display_item_title", True),
            display_final_score_report=data.get("display_final_score_report", False),
            include_feedback=data.get("include_feedback", True),
            append_items_to_view=data.get("append_items_to_view", True),
            introduction_message=data.get("introduction_message"),
            completion_message=data.get("completion_message"),
            items=[ConversationItem.from_dict(item) for item in data.get("items", [])],
            passing_score_percent=data.get("passing_score_percent"),
            created_by=data.get("created_by", ""),
            created_at=created_at or datetime.now(UTC),
            updated_at=updated_at or datetime.now(UTC),
            version=data.get("version", 1),
        )

    # =========================================================================
    # Convenience Properties
    # =========================================================================

    @property
    def item_count(self) -> int:
        """Get the number of items in the template."""
        return len(self.items)

    @property
    def required_item_count(self) -> int:
        """Get the number of items with required content."""
        return sum(1 for item in self.items if item.required_content_count > 0)

    @property
    def max_possible_score(self) -> float:
        """Get the maximum possible score across all items."""
        return sum(item.max_possible_score for item in self.items)

    @property
    def is_proactive(self) -> bool:
        """Check if this template defines a proactive conversation."""
        return self.agent_starts_first

    @property
    def is_reactive(self) -> bool:
        """Check if this template defines a reactive conversation."""
        return not self.agent_starts_first

    @property
    def is_assessment(self) -> bool:
        """Check if this template is an assessment (has passing score)."""
        return self.passing_score_percent is not None

    @property
    def has_time_limit(self) -> bool:
        """Check if this template has a time limit."""
        return self.max_duration_seconds is not None and self.max_duration_seconds > 0

    @property
    def total_item_time_limit(self) -> int | None:
        """Get total time from item-level limits (None if any item has no limit)."""
        if not self.items:
            return None
        total = 0
        for item in self.items:
            if item.time_limit_seconds is None:
                return None
            total += item.time_limit_seconds
        return total

    # =========================================================================
    # Item Access Methods
    # =========================================================================

    def get_item_at(self, index: int) -> ConversationItem | None:
        """Get item at a specific index (0-indexed)."""
        if 0 <= index < len(self.items):
            return self.items[index]
        return None

    def get_item_by_id(self, item_id: str) -> ConversationItem | None:
        """Get an item by its ID."""
        for item in self.items:
            if item.id == item_id:
                return item
        return None

    def get_sorted_items(self) -> list[ConversationItem]:
        """Get items sorted by order."""
        return sorted(self.items, key=lambda item: item.order)

    def is_complete(self, current_index: int) -> bool:
        """Check if all items have been completed based on index."""
        return current_index >= len(self.items)

    def get_next_item(self, current_index: int) -> ConversationItem | None:
        """Get the next item after the current index."""
        return self.get_item_at(current_index + 1)

    def get_previous_item(self, current_index: int) -> ConversationItem | None:
        """Get the previous item before the current index."""
        if current_index > 0:
            return self.get_item_at(current_index - 1)
        return None
