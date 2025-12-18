"""ItemContent model.

ItemContent represents a single piece of content within a ConversationItem.
It can be either static (stem, options, correct_answer defined inline) or
templated (source_id references a SkillTemplate for LLM generation).

ItemContents are rendered top-to-bottom within their parent ConversationItem.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ItemContent:
    """Content within a ConversationItem.

    Each ItemContent represents a UI widget (message, multiple_choice, free_text, etc.)
    that can be either static or dynamically generated from a skill template.

    Attributes:
        id: Unique identifier within the parent ConversationItem
        order: Position in rendering sequence (0-indexed, rendered top-to-bottom)
        is_templated: If True, content is generated from a SkillTemplate via LLM
        source_id: SkillTemplate ID if templated, None otherwise
        widget_type: Type of UI widget to render
        widget_config: Widget-specific configuration (e.g., shuffle_options for MC)
        skippable: Whether user can skip this content
        required: Whether this content must be answered to proceed
        max_score: Maximum score for this content (for assessments)
        stem: Static question/prompt text (if not templated)
        options: Static answer options (if not templated, for multiple_choice)
        correct_answer: Static correct answer (if not templated, never sent to client)
        explanation: Explanation shown after answering (if feedback enabled)
        initial_value: Initial value for the widget (if applicable)
    """

    # Identity
    id: str
    order: int

    # Source
    is_templated: bool = False
    source_id: str | None = None  # Skill ID if templated

    # Widget Configuration
    widget_type: str = "message"  # message, multiple_choice, free_text, slider, code_editor
    widget_config: dict[str, Any] = field(default_factory=dict)

    # Interaction
    skippable: bool = False
    required: bool = True
    show_user_response: bool = True  # Show user's response as a chat bubble after widget submission

    # Scoring
    max_score: float = 1.0

    # Static Content (if not templated)
    stem: str | None = None
    options: list[str] | None = None
    correct_answer: str | None = None  # Never sent to client
    explanation: str | None = None

    # Initial State
    initial_value: Any = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage.

        Note: correct_answer IS included for storage.
        Use to_client_dict() for client-safe representation.
        """
        return {
            "id": self.id,
            "order": self.order,
            "is_templated": self.is_templated,
            "source_id": self.source_id,
            "widget_type": self.widget_type,
            "widget_config": self.widget_config,
            "skippable": self.skippable,
            "required": self.required,
            "show_user_response": self.show_user_response,
            "max_score": self.max_score,
            "stem": self.stem,
            "options": self.options,
            "correct_answer": self.correct_answer,
            "explanation": self.explanation,
            "initial_value": self.initial_value,
        }

    def to_client_dict(self) -> dict[str, Any]:
        """Convert to dictionary safe for client.

        Excludes correct_answer to prevent cheating.
        """
        result = self.to_dict()
        del result["correct_answer"]
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ItemContent":
        """Create from dictionary."""
        return cls(
            id=data.get("id", ""),
            order=data.get("order", 0),
            is_templated=data.get("is_templated", False),
            source_id=data.get("source_id"),
            widget_type=data.get("widget_type", "message"),
            widget_config=data.get("widget_config", {}),
            skippable=data.get("skippable", False),
            required=data.get("required", True),
            show_user_response=data.get("show_user_response", True),
            max_score=data.get("max_score", 1.0),
            stem=data.get("stem"),
            options=data.get("options"),
            correct_answer=data.get("correct_answer"),
            explanation=data.get("explanation"),
            initial_value=data.get("initial_value"),
        )

    @property
    def is_static(self) -> bool:
        """Check if this content is statically defined (not templated)."""
        return not self.is_templated

    @property
    def has_scoring(self) -> bool:
        """Check if this content contributes to scoring."""
        return self.max_score > 0 and self.required

    @property
    def is_multiple_choice(self) -> bool:
        """Check if this is a multiple choice widget."""
        return self.widget_type == "multiple_choice"

    @property
    def is_free_text(self) -> bool:
        """Check if this is a free text widget."""
        return self.widget_type == "free_text"

    @property
    def is_message(self) -> bool:
        """Check if this is a display-only message widget."""
        return self.widget_type == "message"
