"""
Tests for QuestionBankService
"""

import json
import tempfile
from pathlib import Path

import pytest

from infrastructure.services.question_bank_service import (
    Category,
    Difficulty,
    Question,
    QuestionBankService,
    QuestionType,
    TestCase,
    get_question_bank,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_question_data():
    """Sample question bank data for testing."""
    return {
        "version": "1.0.0",
        "description": "Test questions",
        "categories": [
            {"id": "math", "name": "Mathematics", "description": "Math questions"},
            {"id": "python", "name": "Python", "description": "Python questions"},
        ],
        "questions": [
            {
                "id": "math-001",
                "category": "math",
                "difficulty": "easy",
                "type": "multiple_choice",
                "prompt": "What is 2 + 2?",
                "options": ["3", "4", "5", "6"],
                "correct_index": 1,
                "explanation": "Basic addition.",
            },
            {
                "id": "math-002",
                "category": "math",
                "difficulty": "medium",
                "type": "free_text",
                "prompt": "What is 5 * 5?",
                "expected_answer": "25",
                "explanation": "Basic multiplication.",
            },
            {
                "id": "math-003",
                "category": "math",
                "difficulty": "hard",
                "type": "multiple_choice",
                "prompt": "What is the square root of 144?",
                "options": ["10", "11", "12", "13"],
                "correct_index": 2,
            },
            {
                "id": "py-001",
                "category": "python",
                "difficulty": "easy",
                "type": "code_editor",
                "prompt": "Write a function that returns 42.",
                "language": "python",
                "initial_code": "def answer():\n    pass",
                "test_cases": [{"input": None, "expected": 42}],
            },
        ],
    }


@pytest.fixture
def temp_question_file(sample_question_data):
    """Create a temporary question bank file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(sample_question_data, f)
        temp_path = Path(f.name)
    yield temp_path
    temp_path.unlink(missing_ok=True)


@pytest.fixture
def question_bank(temp_question_file):
    """Create a QuestionBankService with test data."""
    service = QuestionBankService(data_path=temp_question_file)
    service.load()
    return service


# =============================================================================
# Category Tests
# =============================================================================


class TestCategory:
    """Tests for Category dataclass."""

    def test_category_creation(self):
        """Test creating a category."""
        cat = Category(id="test", name="Test Category", description="A test")
        assert cat.id == "test"
        assert cat.name == "Test Category"
        assert cat.description == "A test"


# =============================================================================
# Question Tests
# =============================================================================


class TestQuestion:
    """Tests for Question dataclass."""

    def test_multiple_choice_to_client_tool_props(self):
        """Test converting multiple choice question to client tool props."""
        q = Question(
            id="q1",
            category="math",
            difficulty=Difficulty.EASY,
            type=QuestionType.MULTIPLE_CHOICE,
            prompt="What is 1+1?",
            options=["1", "2", "3"],
            correct_index=1,
        )
        props = q.to_client_tool_props()
        assert props["prompt"] == "What is 1+1?"
        assert props["options"] == ["1", "2", "3"]
        assert props["allow_multiple"] is False

    def test_free_text_to_client_tool_props(self):
        """Test converting free text question to client tool props."""
        q = Question(
            id="q2",
            category="math",
            difficulty=Difficulty.MEDIUM,
            type=QuestionType.FREE_TEXT,
            prompt="Enter your answer",
            expected_answer="42",
        )
        props = q.to_client_tool_props()
        assert props["prompt"] == "Enter your answer"
        assert props["min_length"] == 1
        assert props["max_length"] == 500

    def test_code_editor_to_client_tool_props(self):
        """Test converting code editor question to client tool props."""
        q = Question(
            id="q3",
            category="python",
            difficulty=Difficulty.HARD,
            type=QuestionType.CODE_EDITOR,
            prompt="Write code",
            language="python",
            initial_code="def foo(): pass",
        )
        props = q.to_client_tool_props()
        assert props["prompt"] == "Write code"
        assert props["language"] == "python"
        assert props["initial_code"] == "def foo(): pass"

    def test_check_answer_multiple_choice_correct(self):
        """Test checking correct multiple choice answer."""
        q = Question(
            id="q1",
            category="math",
            difficulty=Difficulty.EASY,
            type=QuestionType.MULTIPLE_CHOICE,
            prompt="What is 2+2?",
            options=["3", "4", "5"],
            correct_index=1,
            explanation="Basic math.",
        )
        is_correct, feedback = q.check_answer({"index": 1})
        assert is_correct is True
        assert "Correct" in feedback

    def test_check_answer_multiple_choice_incorrect(self):
        """Test checking incorrect multiple choice answer."""
        q = Question(
            id="q1",
            category="math",
            difficulty=Difficulty.EASY,
            type=QuestionType.MULTIPLE_CHOICE,
            prompt="What is 2+2?",
            options=["3", "4", "5"],
            correct_index=1,
        )
        is_correct, feedback = q.check_answer({"index": 0})
        assert is_correct is False
        assert "Not quite" in feedback

    def test_check_answer_free_text_correct(self):
        """Test checking correct free text answer."""
        q = Question(
            id="q2",
            category="math",
            difficulty=Difficulty.MEDIUM,
            type=QuestionType.FREE_TEXT,
            prompt="What is 5*5?",
            expected_answer="25",
        )
        is_correct, feedback = q.check_answer({"text": "25"})
        assert is_correct is True

    def test_check_answer_free_text_correct_case_insensitive(self):
        """Test case insensitive free text matching."""
        q = Question(
            id="q2",
            category="math",
            difficulty=Difficulty.MEDIUM,
            type=QuestionType.FREE_TEXT,
            prompt="What color is the sky?",
            expected_answer="Blue",
        )
        is_correct, _ = q.check_answer({"text": "blue"})
        assert is_correct is True

    def test_check_answer_free_text_alternative_answers(self):
        """Test free text with alternative answers."""
        q = Question(
            id="q2",
            category="math",
            difficulty=Difficulty.MEDIUM,
            type=QuestionType.FREE_TEXT,
            prompt="Name a primary color",
            expected_answer="red",
            alternative_answers=["blue", "yellow"],
        )
        assert q.check_answer({"text": "red"})[0] is True
        assert q.check_answer({"text": "blue"})[0] is True
        assert q.check_answer({"text": "yellow"})[0] is True
        assert q.check_answer({"text": "green"})[0] is False


# =============================================================================
# QuestionBankService Tests
# =============================================================================


class TestQuestionBankService:
    """Tests for QuestionBankService."""

    def test_load_questions(self, question_bank):
        """Test loading questions from file."""
        assert len(question_bank.questions) == 4

    def test_load_categories(self, question_bank):
        """Test loading categories from file."""
        assert len(question_bank.categories) == 2
        cat_ids = [c.id for c in question_bank.categories]
        assert "math" in cat_ids
        assert "python" in cat_ids

    def test_get_question_by_id(self, question_bank):
        """Test getting question by ID."""
        q = question_bank.get_question_by_id("math-001")
        assert q is not None
        assert q.prompt == "What is 2 + 2?"

    def test_get_question_by_id_not_found(self, question_bank):
        """Test getting non-existent question."""
        q = question_bank.get_question_by_id("nonexistent")
        assert q is None

    def test_get_questions_by_category(self, question_bank):
        """Test filtering questions by category."""
        math_questions = question_bank.get_questions_by_category("math", shuffle=False)
        assert len(math_questions) == 3
        for q in math_questions:
            assert q.category == "math"

    def test_get_questions_by_category_with_difficulty(self, question_bank):
        """Test filtering by category and difficulty."""
        easy_math = question_bank.get_questions_by_category("math", difficulty=Difficulty.EASY, shuffle=False)
        assert len(easy_math) == 1
        assert easy_math[0].difficulty == Difficulty.EASY

    def test_get_questions_by_category_with_type(self, question_bank):
        """Test filtering by category and question type."""
        mc_math = question_bank.get_questions_by_category("math", question_type=QuestionType.MULTIPLE_CHOICE, shuffle=False)
        assert len(mc_math) == 2
        for q in mc_math:
            assert q.type == QuestionType.MULTIPLE_CHOICE

    def test_get_questions_by_category_with_count(self, question_bank):
        """Test limiting question count."""
        questions = question_bank.get_questions_by_category("math", count=2)
        assert len(questions) == 2

    def test_get_random_question(self, question_bank):
        """Test getting a random question."""
        q = question_bank.get_random_question()
        assert q is not None
        assert isinstance(q, Question)

    def test_get_random_question_with_category(self, question_bank):
        """Test getting random question from category."""
        q = question_bank.get_random_question(category_id="python")
        assert q is not None
        assert q.category == "python"

    def test_get_random_question_with_exclude(self, question_bank):
        """Test excluding questions."""
        # Exclude all but one
        exclude = ["math-001", "math-002", "math-003"]
        q = question_bank.get_random_question(exclude_ids=exclude)
        assert q is not None
        assert q.id == "py-001"

    def test_get_random_question_no_matches(self, question_bank):
        """Test when no questions match criteria."""
        q = question_bank.get_random_question(category_id="nonexistent")
        assert q is None

    def test_create_learning_session_questions(self, question_bank):
        """Test creating a learning session."""
        questions = question_bank.create_learning_session_questions("math", count=3)
        assert len(questions) <= 3
        for q in questions:
            assert q.category == "math"

    def test_create_learning_session_empty_category(self, question_bank):
        """Test creating session for empty category."""
        questions = question_bank.create_learning_session_questions("nonexistent", count=5)
        assert len(questions) == 0

    def test_file_not_found(self):
        """Test handling missing file."""
        service = QuestionBankService(data_path=Path("/nonexistent/path.json"))
        with pytest.raises(FileNotFoundError):
            service.load()

    def test_lazy_loading(self, temp_question_file):
        """Test that loading is lazy."""
        service = QuestionBankService(data_path=temp_question_file)
        assert service._loaded is False
        _ = service.questions
        assert service._loaded is True

    def test_double_loading_is_idempotent(self, temp_question_file):
        """Test that loading twice doesn't duplicate data."""
        service = QuestionBankService(data_path=temp_question_file)
        service.load()
        initial_count = len(service.questions)
        service.load()
        assert len(service.questions) == initial_count


# =============================================================================
# Global Instance Tests
# =============================================================================


class TestGlobalInstance:
    """Tests for global question bank instance."""

    def test_get_question_bank_returns_same_instance(self):
        """Test that get_question_bank returns singleton."""
        # Note: This test may fail if run after other tests that initialize the global
        # In a real test suite, we'd want to reset the global between tests
        bank1 = get_question_bank()
        bank2 = get_question_bank()
        assert bank1 is bank2


# =============================================================================
# TestCase Tests
# =============================================================================


class TestTestCase:
    """Tests for TestCase dataclass."""

    def test_test_case_creation(self):
        """Test creating a test case."""
        tc = TestCase(input=5, expected=10)
        assert tc.input == 5
        assert tc.expected == 10

    def test_test_case_with_none_input(self):
        """Test test case with None input."""
        tc = TestCase(input=None, expected=42)
        assert tc.input is None
        assert tc.expected == 42
