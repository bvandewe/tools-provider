"""
Question Bank Service

Provides access to sample questions for proactive learning sessions.
Questions are loaded from a JSON file and can be filtered by category and difficulty.
"""

import json
import random
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class QuestionType(str, Enum):
    """Types of questions supported by the question bank."""

    MULTIPLE_CHOICE = "multiple_choice"
    FREE_TEXT = "free_text"
    CODE_EDITOR = "code_editor"


class Difficulty(str, Enum):
    """Question difficulty levels."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


@dataclass
class TestCase:
    """Test case for code editor questions."""

    input: Any
    expected: Any


@dataclass
class Question:
    """A question from the question bank."""

    id: str
    category: str
    difficulty: Difficulty
    type: QuestionType
    prompt: str

    # Multiple choice specific
    options: list[str] = field(default_factory=list)
    correct_index: int | None = None

    # Free text specific
    expected_answer: str | None = None
    alternative_answers: list[str] = field(default_factory=list)

    # Code editor specific
    language: str | None = None
    initial_code: str | None = None
    expected_output: str | None = None
    test_cases: list[TestCase] = field(default_factory=list)

    # Common
    explanation: str | None = None

    def to_client_tool_props(self) -> dict:
        """Convert question to client tool properties format."""
        if self.type == QuestionType.MULTIPLE_CHOICE:
            return {
                "prompt": self.prompt,
                "options": self.options,
                "allow_multiple": False,
            }
        elif self.type == QuestionType.FREE_TEXT:
            return {
                "prompt": self.prompt,
                "placeholder": "Enter your answer...",
                "min_length": 1,
                "max_length": 500,
                "multiline": False,
            }
        elif self.type == QuestionType.CODE_EDITOR:
            return {
                "prompt": self.prompt,
                "language": self.language or "python",
                "initial_code": self.initial_code or "",
                "min_lines": 3,
                "max_lines": 20,
            }
        else:
            return {"prompt": self.prompt}

    def check_answer(self, response: dict) -> tuple[bool, str]:
        """
        Check if the user's response is correct.

        Returns:
            Tuple of (is_correct, feedback_message)
        """
        if self.type == QuestionType.MULTIPLE_CHOICE:
            user_index = response.get("index")
            is_correct = user_index == self.correct_index
            if is_correct:
                return True, f"Correct! {self.explanation or ''}"
            else:
                correct_answer = self.options[self.correct_index] if self.correct_index is not None else "Unknown"
                return False, f"Not quite. The correct answer is: {correct_answer}. {self.explanation or ''}"

        elif self.type == QuestionType.FREE_TEXT:
            user_text = str(response.get("text", "")).strip().lower()
            expected = str(self.expected_answer).strip().lower() if self.expected_answer else ""
            alternatives = [str(a).strip().lower() for a in self.alternative_answers]

            is_correct = user_text == expected or user_text in alternatives
            if is_correct:
                return True, f"Correct! {self.explanation or ''}"
            else:
                return False, f"Not quite. The expected answer is: {self.expected_answer}. {self.explanation or ''}"

        elif self.type == QuestionType.CODE_EDITOR:
            # Code validation would require execution - return pending for now
            return True, "Code submitted for review."

        return False, "Unable to check answer."


@dataclass
class Category:
    """A category of questions."""

    id: str
    name: str
    description: str


class QuestionBankService:
    """
    Service for loading and managing sample questions.

    Usage:
        service = QuestionBankService()
        questions = service.get_questions_by_category("algebra", count=5)
        question = service.get_random_question(difficulty=Difficulty.MEDIUM)
    """

    def __init__(self, data_path: Path | None = None):
        """
        Initialize the question bank service.

        Args:
            data_path: Path to the sample_questions.json file.
                      If None, uses default location.
        """
        if data_path is None:
            data_path = Path(__file__).parent.parent / "data" / "sample_questions.json"

        self._data_path = data_path
        self._questions: list[Question] = []
        self._categories: list[Category] = []
        self._loaded = False

    def load(self) -> None:
        """Load questions from the JSON file."""
        if self._loaded:
            return

        if not self._data_path.exists():
            raise FileNotFoundError(f"Question bank not found at: {self._data_path}")

        with open(self._data_path, encoding="utf-8") as f:
            data = json.load(f)

        # Load categories
        for cat_data in data.get("categories", []):
            self._categories.append(
                Category(
                    id=cat_data["id"],
                    name=cat_data["name"],
                    description=cat_data["description"],
                )
            )

        # Load questions
        for q_data in data.get("questions", []):
            test_cases = []
            for tc in q_data.get("test_cases", []):
                test_cases.append(TestCase(input=tc["input"], expected=tc["expected"]))

            self._questions.append(
                Question(
                    id=q_data["id"],
                    category=q_data["category"],
                    difficulty=Difficulty(q_data["difficulty"]),
                    type=QuestionType(q_data["type"]),
                    prompt=q_data["prompt"],
                    options=q_data.get("options", []),
                    correct_index=q_data.get("correct_index"),
                    expected_answer=q_data.get("expected_answer"),
                    alternative_answers=q_data.get("alternative_answers", []),
                    language=q_data.get("language"),
                    initial_code=q_data.get("initial_code"),
                    expected_output=q_data.get("expected_output"),
                    test_cases=test_cases,
                    explanation=q_data.get("explanation"),
                )
            )

        self._loaded = True

    @property
    def categories(self) -> list[Category]:
        """Get all available categories."""
        self.load()
        return self._categories.copy()

    @property
    def questions(self) -> list[Question]:
        """Get all questions."""
        self.load()
        return self._questions.copy()

    def get_question_by_id(self, question_id: str) -> Question | None:
        """Get a specific question by ID."""
        self.load()
        for q in self._questions:
            if q.id == question_id:
                return q
        return None

    def get_questions_by_category(
        self,
        category_id: str,
        difficulty: Difficulty | None = None,
        question_type: QuestionType | None = None,
        count: int | None = None,
        shuffle: bool = True,
    ) -> list[Question]:
        """
        Get questions filtered by category and optional criteria.

        Args:
            category_id: Category to filter by
            difficulty: Optional difficulty filter
            question_type: Optional question type filter
            count: Maximum number of questions to return
            shuffle: Whether to randomize the order

        Returns:
            List of matching questions
        """
        self.load()

        filtered = [q for q in self._questions if q.category == category_id]

        if difficulty:
            filtered = [q for q in filtered if q.difficulty == difficulty]

        if question_type:
            filtered = [q for q in filtered if q.type == question_type]

        if shuffle:
            filtered = filtered.copy()
            random.shuffle(filtered)

        if count:
            filtered = filtered[:count]

        return filtered

    def get_random_question(
        self,
        category_id: str | None = None,
        difficulty: Difficulty | None = None,
        question_type: QuestionType | None = None,
        exclude_ids: list[str] | None = None,
    ) -> Question | None:
        """
        Get a random question matching the criteria.

        Args:
            category_id: Optional category filter
            difficulty: Optional difficulty filter
            question_type: Optional question type filter
            exclude_ids: Question IDs to exclude (e.g., already asked)

        Returns:
            A random question or None if no matches
        """
        self.load()

        filtered = self._questions.copy()

        if category_id:
            filtered = [q for q in filtered if q.category == category_id]

        if difficulty:
            filtered = [q for q in filtered if q.difficulty == difficulty]

        if question_type:
            filtered = [q for q in filtered if q.type == question_type]

        if exclude_ids:
            filtered = [q for q in filtered if q.id not in exclude_ids]

        if not filtered:
            return None

        return random.choice(filtered)

    def create_learning_session_questions(
        self,
        category_id: str,
        count: int = 5,
        mix_difficulties: bool = True,
        mix_types: bool = True,
    ) -> list[Question]:
        """
        Create a curated set of questions for a learning session.

        Args:
            category_id: Category to create session for
            count: Number of questions
            mix_difficulties: Whether to include various difficulty levels
            mix_types: Whether to include various question types

        Returns:
            Ordered list of questions for the session
        """
        self.load()

        category_questions = [q for q in self._questions if q.category == category_id]

        if not category_questions:
            return []

        if mix_difficulties:
            # Try to get a balanced mix: more easy, some medium, fewer hard
            easy = [q for q in category_questions if q.difficulty == Difficulty.EASY]
            medium = [q for q in category_questions if q.difficulty == Difficulty.MEDIUM]
            hard = [q for q in category_questions if q.difficulty == Difficulty.HARD]

            result = []
            # Start with easy questions
            random.shuffle(easy)
            result.extend(easy[: max(1, count // 2)])

            # Add medium questions
            random.shuffle(medium)
            result.extend(medium[: max(1, count // 3)])

            # Add hard questions
            random.shuffle(hard)
            result.extend(hard[: max(1, count // 4)])

            # Fill remaining with random
            remaining = count - len(result)
            if remaining > 0:
                unused = [q for q in category_questions if q not in result]
                random.shuffle(unused)
                result.extend(unused[:remaining])

            return result[:count]
        else:
            random.shuffle(category_questions)
            return category_questions[:count]


# Global instance for convenience
_question_bank: QuestionBankService | None = None


def get_question_bank() -> QuestionBankService:
    """Get the global question bank service instance."""
    global _question_bank
    if _question_bank is None:
        _question_bank = QuestionBankService()
    return _question_bank
