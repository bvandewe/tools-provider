"""Skill Template model.

SkillTemplate defines how the LLM should generate assessment items.
It's referenced by ItemTemplate.skill_template_id and contains
the prompt template and evaluation criteria.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class SkillTemplate:
    """Skill definition used by LLM to generate assessment items.

    This is stored in MongoDB and referenced by ItemTemplates.
    The LLM uses the prompt_template to generate questions
    with the specified answer_format.

    Attributes:
        id: Unique identifier
        name: Display name (e.g., "Two-digit Addition")
        domain: Knowledge domain (e.g., "mathematics")
        subdomain: More specific area (e.g., "arithmetic")
        difficulty_range: Range of difficulty values (min, max)
        prompt_template: Template for LLM to generate items
        answer_format: Expected answer format
        evaluation_criteria: Rubric for grading responses
        examples: Example questions for few-shot learning
        created_by: User who created it
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    id: str
    name: str
    domain: str
    subdomain: str | None = None

    # Generation parameters
    difficulty_min: float = 0.0
    difficulty_max: float = 1.0
    prompt_template: str = ""
    answer_format: str = "free_text"  # single_choice, numeric, text, code

    # Evaluation
    evaluation_criteria: dict[str, Any] = field(default_factory=dict)

    # Examples for few-shot learning
    examples: list[dict[str, Any]] = field(default_factory=list)

    # Audit
    created_by: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for MongoDB storage."""
        return {
            "id": self.id,
            "name": self.name,
            "domain": self.domain,
            "subdomain": self.subdomain,
            "difficulty_min": self.difficulty_min,
            "difficulty_max": self.difficulty_max,
            "prompt_template": self.prompt_template,
            "answer_format": self.answer_format,
            "evaluation_criteria": self.evaluation_criteria,
            "examples": self.examples,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SkillTemplate":
        """Create from dictionary (MongoDB document)."""
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
            domain=data.get("domain", ""),
            subdomain=data.get("subdomain"),
            difficulty_min=data.get("difficulty_min", 0.0),
            difficulty_max=data.get("difficulty_max", 1.0),
            prompt_template=data.get("prompt_template", ""),
            answer_format=data.get("answer_format", "free_text"),
            evaluation_criteria=data.get("evaluation_criteria", {}),
            examples=data.get("examples", []),
            created_by=data.get("created_by", ""),
            created_at=created_at or datetime.now(UTC),
            updated_at=updated_at or datetime.now(UTC),
        )

    @property
    def difficulty_range(self) -> tuple[float, float]:
        """Get the difficulty range as a tuple."""
        return (self.difficulty_min, self.difficulty_max)

    def build_generation_prompt(
        self,
        difficulty: float | None = None,
        additional_context: str | None = None,
    ) -> str:
        """Build the full prompt for LLM item generation.

        Args:
            difficulty: Target difficulty (0.0-1.0), defaults to middle of range
            additional_context: Extra context from ItemTemplate.generation_prompt

        Returns:
            Complete prompt for LLM
        """
        if difficulty is None:
            difficulty = (self.difficulty_min + self.difficulty_max) / 2

        # Clamp difficulty to range
        difficulty = max(self.difficulty_min, min(self.difficulty_max, difficulty))

        prompt_parts = [
            f"# Skill: {self.name}",
            f"Domain: {self.domain}",
        ]

        if self.subdomain:
            prompt_parts.append(f"Subdomain: {self.subdomain}")

        prompt_parts.append(f"Difficulty: {difficulty:.2f}")
        prompt_parts.append(f"Answer Format: {self.answer_format}")
        prompt_parts.append("")
        prompt_parts.append("## Generation Instructions")
        prompt_parts.append(self.prompt_template)

        if additional_context:
            prompt_parts.append("")
            prompt_parts.append("## Additional Context")
            prompt_parts.append(additional_context)

        if self.examples:
            prompt_parts.append("")
            prompt_parts.append("## Examples")
            for i, example in enumerate(self.examples, 1):
                prompt_parts.append(f"Example {i}:")
                prompt_parts.append(f"  Question: {example.get('question', 'N/A')}")
                prompt_parts.append(f"  Answer: {example.get('answer', 'N/A')}")

        return "\n".join(prompt_parts)
