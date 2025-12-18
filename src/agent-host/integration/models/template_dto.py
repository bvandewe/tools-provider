"""ConversationTemplate DTOs for read model projections.

These DTOs are the queryable read model representations for:
- ConversationTemplate
- ConversationItem
- ItemContent

Used by MotorRepository for LINQ-style queries via query_async().
"""

import datetime
from dataclasses import dataclass, field
from typing import Any

from neuroglia.data.abstractions import Identifiable, queryable


@queryable
@dataclass
class ItemContentDto:
    """Read model DTO for ItemContent.

    Represents a single piece of content within a ConversationItem.
    Can be static (stem, options defined inline) or templated (source_id references a SkillTemplate).

    Attributes:
        id: Unique identifier within the parent ConversationItem
        order: Position in rendering sequence (0-indexed)
        is_templated: If True, content is generated from a SkillTemplate
        source_id: SkillTemplate ID if templated
        widget_type: Type of UI widget to render
        widget_config: Widget-specific configuration
        skippable: Whether user can skip this content
        required: Whether this content must be answered
        max_score: Maximum score for this content
        stem: Static question/prompt text (if not templated)
        options: Static answer options (if not templated)
        correct_answer: Static correct answer (NEVER sent to client)
        explanation: Explanation shown after answering
        initial_value: Initial value for the widget
    """

    id: str
    order: int = 0

    # Source
    is_templated: bool = False
    source_id: str | None = None

    # Widget Configuration
    widget_type: str = "message"
    widget_config: dict[str, Any] = field(default_factory=dict)

    # Interaction
    skippable: bool = False
    required: bool = True
    show_user_response: bool = True  # Show user's response as a chat bubble

    # Scoring
    max_score: float = 1.0

    # Static Content
    stem: str | None = None
    options: list[str] | None = None
    correct_answer: str | None = None
    explanation: str | None = None

    # Initial State
    initial_value: Any = None

    @property
    def is_static(self) -> bool:
        """Check if this content is statically defined."""
        return not self.is_templated

    @property
    def is_multiple_choice(self) -> bool:
        """Check if this is a multiple choice widget."""
        return self.widget_type == "multiple_choice"


@queryable
@dataclass
class ConversationItemDto:
    """Read model DTO for ConversationItem.

    Represents a UX step in the conversation flow, containing one or more ItemContents.

    Attributes:
        id: Unique identifier within the parent ConversationTemplate
        order: Position in sequence (0-indexed)
        title: Optional display title for this step
        enable_chat_input: Whether user can type in chat during this step
        show_expiration_warning: Whether to show warning before time expires
        expiration_warning_seconds: Seconds before time_limit to show warning
        warning_message: Custom warning message
        provide_feedback: Whether to give feedback after response
        reveal_correct_answer: Whether to show correct answer after response
        time_limit_seconds: Time limit for this step
        contents: List of ItemContentDto
    """

    id: str
    order: int = 0
    title: str | None = None

    # Interaction Configuration
    enable_chat_input: bool = True
    show_expiration_warning: bool = False
    expiration_warning_seconds: int | None = None
    warning_message: str | None = None
    provide_feedback: bool = True
    reveal_correct_answer: bool = False

    # Timing
    time_limit_seconds: int | None = None

    # Content
    contents: list[ItemContentDto] = field(default_factory=list)

    @property
    def content_count(self) -> int:
        """Get the number of content items."""
        return len(self.contents)

    @property
    def has_time_limit(self) -> bool:
        """Check if this item has a time limit."""
        return self.time_limit_seconds is not None and self.time_limit_seconds > 0


@queryable
@dataclass
class ConversationTemplateDto(Identifiable[str]):
    """Read model DTO for ConversationTemplate.

    This DTO is used for:
    - MongoDB read operations via MotorRepository
    - API responses (list/detail views)
    - Query projections in CQRS queries

    Attributes:
        id: Unique identifier (slug or UUID)
        name: Display name for admin UI
        description: Longer description for admin UI
        agent_starts_first: If True, agent sends first message
        allow_agent_switching: If True, user can switch agents
        allow_navigation: If True, user can jump between items
        allow_backward_navigation: If True, user can go back
        enable_chat_input_initially: If True, chat input enabled at start
        min_duration_seconds: Minimum time before completion
        max_duration_seconds: Maximum time for conversation
        shuffle_items: If True, randomize item order
        display_progress_indicator: If True, show progress bar
        display_item_score: If True, show score per item
        display_item_title: If True, show item titles
        display_final_score_report: If True, show final score
        include_feedback: If True, provide feedback
        append_items_to_view: If True, keep previous items visible
        introduction_message: Message at start
        completion_message: Message on completion
        items: List of ConversationItemDto
        passing_score_percent: Score needed to pass
        created_by: User who created this
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

    # Content
    items: list[ConversationItemDto] = field(default_factory=list)

    # Scoring
    passing_score_percent: float | None = None

    # Audit
    created_by: str = ""
    created_at: datetime.datetime | None = None
    updated_at: datetime.datetime | None = None
    version: int = 1

    @property
    def item_count(self) -> int:
        """Get the number of items."""
        return len(self.items)

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
        """Check if this template is an assessment."""
        return self.passing_score_percent is not None

    @property
    def has_time_limit(self) -> bool:
        """Check if this template has a time limit."""
        return self.max_duration_seconds is not None and self.max_duration_seconds > 0
