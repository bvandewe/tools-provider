"""Blueprint domain models for evaluation system.

This module defines the core value objects for the blueprint-driven evaluation system:
- Skill: A single skill blueprint defining how to generate assessment items
- ExamDomain: A group of related skills within an exam (e.g., "Addition", "Subnetting")
- ExamBlueprint: A complete exam definition with multiple domains

The LLM generates items from Skill blueprints. The backend stores and verifies answers.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ItemType(str, Enum):
    """Types of assessment items that can be generated."""

    MULTIPLE_CHOICE = "multiple_choice"
    FREE_TEXT = "free_text"
    CODE = "code"


class DifficultyLevel(str, Enum):
    """Difficulty levels for skill items."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class EvaluationMethod(str, Enum):
    """Methods for evaluating user responses."""

    EXACT_MATCH = "exact_match"
    NUMERIC_TOLERANCE = "numeric_tolerance"
    CASE_INSENSITIVE = "case_insensitive"
    REGEX_MATCH = "regex_match"


@dataclass(frozen=True)
class DifficultyConfig:
    """Configuration for a specific difficulty level.

    Attributes:
        value: Numeric difficulty value (0.0 to 1.0)
        constraints: List of constraint descriptions for LLM generation
        weight: Relative weight for random selection (default: 1.0)
    """

    value: float
    constraints: list[str] = field(default_factory=list)
    weight: float = 1.0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DifficultyConfig":
        """Create from dictionary."""
        return cls(
            value=data.get("value", 0.5),
            constraints=data.get("constraints", []),
            weight=data.get("weight", 1.0),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "value": self.value,
            "constraints": self.constraints,
            "weight": self.weight,
        }


@dataclass(frozen=True)
class DistractorStrategy:
    """Strategy for generating plausible incorrect options.

    Attributes:
        type: Strategy identifier (e.g., "off_by_10", "wrong_operation")
        description: Human-readable description for LLM
        formula: Optional formula hint for generating distractor
    """

    type: str
    description: str = ""
    formula: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DistractorStrategy":
        """Create from dictionary."""
        return cls(
            type=data.get("type", "generic"),
            description=data.get("description", ""),
            formula=data.get("formula"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {"type": self.type}
        if self.description:
            result["description"] = self.description
        if self.formula:
            result["formula"] = self.formula
        return result


@dataclass(frozen=True)
class Skill:
    """A skill blueprint defining how to generate assessment items.

    This is the core unit for item generation. The LLM uses the skill
    definition to generate both the question content AND the correct answer.

    Attributes:
        skill_id: Unique identifier (e.g., "MATH.ARITH.ADD.2DIGIT")
        name: Human-readable name
        description: Detailed description of what the skill assesses
        domain: Top-level domain (e.g., "Mathematics", "Networking")
        topic: Specific topic within domain (e.g., "Addition", "Subnetting")
        item_type: Type of item to generate
        option_count: Number of options for multiple choice (default: 4)
        stem_templates: Example question templates for LLM guidance
        difficulty_levels: Configuration per difficulty level
        distractor_strategies: Strategies for generating wrong options
        evaluation_method: How to evaluate responses
        time_limit_seconds: Optional per-item time limit
        version: Blueprint version for tracking changes
    """

    skill_id: str
    name: str
    description: str
    domain: str
    topic: str
    item_type: ItemType = ItemType.MULTIPLE_CHOICE
    option_count: int = 4
    stem_templates: list[str] = field(default_factory=list)
    difficulty_levels: dict[DifficultyLevel, DifficultyConfig] = field(default_factory=dict)
    distractor_strategies: list[DistractorStrategy] = field(default_factory=list)
    evaluation_method: EvaluationMethod = EvaluationMethod.EXACT_MATCH
    time_limit_seconds: int | None = None
    version: str = "1.0"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Skill":
        """Create from dictionary (parsed YAML)."""
        # Parse difficulty levels
        difficulty_levels: dict[DifficultyLevel, DifficultyConfig] = {}
        for level_name, level_data in data.get("difficulty_levels", {}).items():
            try:
                level = DifficultyLevel(level_name)
                difficulty_levels[level] = DifficultyConfig.from_dict(level_data)
            except ValueError:
                pass  # Skip unknown difficulty levels

        # Parse distractor strategies
        distractor_strategies = [DistractorStrategy.from_dict(s) for s in data.get("distractor_strategies", [])]

        # Parse item type
        item_type_str = data.get("item_type", "multiple_choice")
        try:
            item_type = ItemType(item_type_str)
        except ValueError:
            item_type = ItemType.MULTIPLE_CHOICE

        # Parse evaluation method
        eval_method_str = data.get("evaluation_method", "exact_match")
        try:
            evaluation_method = EvaluationMethod(eval_method_str)
        except ValueError:
            evaluation_method = EvaluationMethod.EXACT_MATCH

        return cls(
            skill_id=data["skill_id"],
            name=data.get("name", data["skill_id"]),
            description=data.get("description", ""),
            domain=data.get("domain", "General"),
            topic=data.get("topic", "General"),
            item_type=item_type,
            option_count=data.get("option_count", 4),
            stem_templates=data.get("stem_templates", []),
            difficulty_levels=difficulty_levels,
            distractor_strategies=distractor_strategies,
            evaluation_method=evaluation_method,
            time_limit_seconds=data.get("time_limit_seconds"),
            version=data.get("version", "1.0"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "domain": self.domain,
            "topic": self.topic,
            "item_type": self.item_type.value,
            "option_count": self.option_count,
            "stem_templates": self.stem_templates,
            "difficulty_levels": {level.value: config.to_dict() for level, config in self.difficulty_levels.items()},
            "distractor_strategies": [s.to_dict() for s in self.distractor_strategies],
            "evaluation_method": self.evaluation_method.value,
            "time_limit_seconds": self.time_limit_seconds,
            "version": self.version,
        }

    def get_difficulty_config(self, level: DifficultyLevel) -> DifficultyConfig:
        """Get configuration for a difficulty level, with fallback to medium."""
        return self.difficulty_levels.get(level, self.difficulty_levels.get(DifficultyLevel.MEDIUM, DifficultyConfig(value=0.5)))


@dataclass(frozen=True)
class ExamDomainSkillRef:
    """Reference to a skill within an exam domain.

    Attributes:
        skill_id: The skill ID to include
        weight: Relative weight for item selection (default: 1.0)
        item_count: Optional specific number of items from this skill
    """

    skill_id: str
    weight: float = 1.0
    item_count: int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExamDomainSkillRef":
        """Create from dictionary."""
        # Handle both string shorthand and dict format
        if isinstance(data, str):
            return cls(skill_id=data)
        return cls(
            skill_id=data["skill_id"],
            weight=data.get("weight", 1.0),
            item_count=data.get("item_count"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {"skill_id": self.skill_id}
        if self.weight != 1.0:
            result["weight"] = self.weight
        if self.item_count is not None:
            result["item_count"] = self.item_count
        return result


@dataclass(frozen=True)
class ExamDomain:
    """A domain/section within an exam containing related skills.

    Attributes:
        domain_id: Unique identifier for this domain
        name: Display name (e.g., "Addition", "Subnetting")
        description: Optional description
        skills: List of skill references in this domain
        item_count: Total items to generate from this domain
        difficulty_distribution: How many items per difficulty level
        weight: Relative weight when computing final score
    """

    domain_id: str
    name: str
    description: str = ""
    skills: list[ExamDomainSkillRef] = field(default_factory=list)
    item_count: int = 5
    difficulty_distribution: dict[DifficultyLevel, int] = field(default_factory=dict)
    weight: float = 1.0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExamDomain":
        """Create from dictionary."""
        # Parse skills
        skills = []
        for skill_data in data.get("skills", []):
            skills.append(ExamDomainSkillRef.from_dict(skill_data))

        # Parse difficulty distribution
        difficulty_distribution: dict[DifficultyLevel, int] = {}
        for level_name, count in data.get("difficulty_distribution", {}).items():
            try:
                level = DifficultyLevel(level_name)
                difficulty_distribution[level] = count
            except ValueError:
                pass

        return cls(
            domain_id=data["domain_id"],
            name=data.get("name", data["domain_id"]),
            description=data.get("description", ""),
            skills=skills,
            item_count=data.get("item_count", 5),
            difficulty_distribution=difficulty_distribution,
            weight=data.get("weight", 1.0),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "domain_id": self.domain_id,
            "name": self.name,
            "description": self.description,
            "skills": [s.to_dict() for s in self.skills],
            "item_count": self.item_count,
            "difficulty_distribution": {level.value: count for level, count in self.difficulty_distribution.items()},
            "weight": self.weight,
        }


@dataclass(frozen=True)
class ExamBlueprint:
    """A complete exam definition with multiple domains.

    This is the top-level blueprint that defines an entire assessment.
    Domain experts create these to specify what skills to assess.

    Attributes:
        exam_id: Unique identifier (e.g., "MATH-FUNDAMENTALS-L1")
        name: Display name
        description: Detailed description of the exam
        version: Blueprint version
        domains: List of exam domains
        total_items: Total number of items in the exam
        time_limit_minutes: Overall time limit
        passing_score_percent: Minimum score to pass
        shuffle_items: Whether to shuffle item order
        shuffle_options: Whether to shuffle multiple choice options
        show_progress: Whether to show progress indicator
        allow_review: Whether users can review answers
        allow_skip: Whether users can skip items
    """

    exam_id: str
    name: str
    description: str = ""
    version: str = "1.0"
    domains: list[ExamDomain] = field(default_factory=list)
    total_items: int = 20
    time_limit_minutes: int | None = 30
    passing_score_percent: float = 70.0
    shuffle_items: bool = True
    shuffle_options: bool = True
    show_progress: bool = True
    allow_review: bool = False
    allow_skip: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExamBlueprint":
        """Create from dictionary (parsed YAML)."""
        domains = [ExamDomain.from_dict(d) for d in data.get("domains", [])]

        return cls(
            exam_id=data["exam_id"],
            name=data.get("name", data["exam_id"]),
            description=data.get("description", ""),
            version=data.get("version", "1.0"),
            domains=domains,
            total_items=data.get("total_items", 20),
            time_limit_minutes=data.get("time_limit_minutes", 30),
            passing_score_percent=data.get("passing_score_percent", 70.0),
            shuffle_items=data.get("shuffle_items", True),
            shuffle_options=data.get("shuffle_options", True),
            show_progress=data.get("show_progress", True),
            allow_review=data.get("allow_review", False),
            allow_skip=data.get("allow_skip", False),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "exam_id": self.exam_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "domains": [d.to_dict() for d in self.domains],
            "total_items": self.total_items,
            "time_limit_minutes": self.time_limit_minutes,
            "passing_score_percent": self.passing_score_percent,
            "shuffle_items": self.shuffle_items,
            "shuffle_options": self.shuffle_options,
            "show_progress": self.show_progress,
            "allow_review": self.allow_review,
            "allow_skip": self.allow_skip,
        }

    def get_all_skill_ids(self) -> list[str]:
        """Get all unique skill IDs referenced in this exam."""
        skill_ids: set[str] = set()
        for domain in self.domains:
            for skill_ref in domain.skills:
                skill_ids.add(skill_ref.skill_id)
        return list(skill_ids)

    def compute_total_items_from_domains(self) -> int:
        """Calculate total items by summing domain item counts."""
        return sum(domain.item_count for domain in self.domains)
