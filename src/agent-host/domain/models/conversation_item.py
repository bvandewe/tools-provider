"""ConversationItem model.

ConversationItem represents a UX step in the conversation flow.
It groups related ItemContents and defines interaction behavior for that step.

ConversationItems are ordered within their parent ConversationTemplate
and rendered sequentially (or shuffled if template.shuffle_items is True).
"""

from dataclasses import dataclass, field
from typing import Any

from domain.models.item_content import ItemContent


@dataclass
class ConversationItem:
    """A UX step in the conversation flow.

    Each ConversationItem represents a logical step in a structured conversation,
    containing one or more ItemContents that are rendered together.

    Attributes:
        id: Unique identifier within the parent ConversationTemplate
        order: Position in sequence (0-indexed)
        title: Optional display title for this step
        enable_chat_input: Whether user can type free-form in chat during this step
        show_expiration_warning: Whether to show warning before time expires
        expiration_warning_seconds: Seconds before time_limit to show warning
        warning_message: Custom warning message (uses default if None)
        provide_feedback: Whether to give feedback after user responds
        reveal_correct_answer: Whether to show correct answer after response
        time_limit_seconds: Time limit for this step (None = no limit)
        contents: List of ItemContent to render in this step
    """

    # Identity
    id: str
    order: int
    title: str | None = None

    # Interaction Configuration
    enable_chat_input: bool = True
    show_expiration_warning: bool = False
    expiration_warning_seconds: int | None = None
    warning_message: str | None = None
    provide_feedback: bool = True
    reveal_correct_answer: bool = False

    # Context Configuration
    include_conversation_context: bool = True  # If False, LLM generates item independently

    # Timing
    time_limit_seconds: int | None = None

    # Content (rendered top-to-bottom)
    contents: list[ItemContent] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage.

        Note: Uses contents.to_dict() which includes correct_answer.
        Use to_client_dict() for client-safe representation.
        """
        return {
            "id": self.id,
            "order": self.order,
            "title": self.title,
            "enable_chat_input": self.enable_chat_input,
            "show_expiration_warning": self.show_expiration_warning,
            "expiration_warning_seconds": self.expiration_warning_seconds,
            "warning_message": self.warning_message,
            "provide_feedback": self.provide_feedback,
            "reveal_correct_answer": self.reveal_correct_answer,
            "include_conversation_context": self.include_conversation_context,
            "time_limit_seconds": self.time_limit_seconds,
            "contents": [c.to_dict() for c in self.contents],
        }

    def to_client_dict(self) -> dict[str, Any]:
        """Convert to dictionary safe for client.

        Excludes correct_answer from contents to prevent cheating.
        """
        return {
            "id": self.id,
            "order": self.order,
            "title": self.title,
            "enable_chat_input": self.enable_chat_input,
            "show_expiration_warning": self.show_expiration_warning,
            "expiration_warning_seconds": self.expiration_warning_seconds,
            "warning_message": self.warning_message,
            "provide_feedback": self.provide_feedback,
            "reveal_correct_answer": self.reveal_correct_answer,
            "include_conversation_context": self.include_conversation_context,
            "time_limit_seconds": self.time_limit_seconds,
            "contents": [c.to_client_dict() for c in self.contents],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConversationItem":
        """Create from dictionary."""
        return cls(
            id=data.get("id", ""),
            order=data.get("order", 0),
            title=data.get("title"),
            enable_chat_input=data.get("enable_chat_input", True),
            show_expiration_warning=data.get("show_expiration_warning", False),
            expiration_warning_seconds=data.get("expiration_warning_seconds"),
            warning_message=data.get("warning_message"),
            provide_feedback=data.get("provide_feedback", True),
            reveal_correct_answer=data.get("reveal_correct_answer", False),
            include_conversation_context=data.get("include_conversation_context", True),
            time_limit_seconds=data.get("time_limit_seconds"),
            contents=[ItemContent.from_dict(c) for c in data.get("contents", [])],
        )

    @property
    def content_count(self) -> int:
        """Get the number of content items in this step."""
        return len(self.contents)

    @property
    def required_content_count(self) -> int:
        """Get the number of required content items."""
        return sum(1 for c in self.contents if c.required)

    @property
    def max_possible_score(self) -> float:
        """Get the maximum possible score for this item."""
        return sum(c.max_score for c in self.contents if c.has_scoring)

    @property
    def has_time_limit(self) -> bool:
        """Check if this item has a time limit."""
        return self.time_limit_seconds is not None and self.time_limit_seconds > 0

    @property
    def has_multiple_choice(self) -> bool:
        """Check if this item contains any multiple choice content."""
        return any(c.is_multiple_choice for c in self.contents)

    @property
    def is_timed(self) -> bool:
        """Check if this item is time-limited."""
        return self.has_time_limit

    def get_content_by_id(self, content_id: str) -> ItemContent | None:
        """Get a specific content by ID."""
        for content in self.contents:
            if content.id == content_id:
                return content
        return None

    def get_sorted_contents(self) -> list[ItemContent]:
        """Get contents sorted by order."""
        return sorted(self.contents, key=lambda c: c.order)
