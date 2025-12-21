"""Unit tests for ItemExecutionState dataclass.

Tests cover:
- Widget response tracking
- Completion detection with and without confirmation
- Serialization/deserialization
- Progress calculation
"""

from datetime import UTC, datetime, timedelta

from application.orchestrator.context import ItemExecutionState


class TestItemExecutionStateCreation:
    """Test ItemExecutionState initialization."""

    def test_minimal_creation(self):
        """Test creation with minimal required fields."""
        state = ItemExecutionState(item_id="item-1", item_index=0)

        assert state.item_id == "item-1"
        assert state.item_index == 0
        assert state.started_at is not None
        assert state.completed_at is None
        assert state.widget_responses == {}
        assert state.required_widget_ids == set()
        assert state.answered_widget_ids == set()
        assert state.require_user_confirmation is False
        assert state.confirmation_button_text == "Submit"
        assert state.user_confirmed is False

    def test_creation_with_confirmation_required(self):
        """Test creation with user confirmation enabled."""
        state = ItemExecutionState(
            item_id="item-2",
            item_index=1,
            require_user_confirmation=True,
            confirmation_button_text="Confirm Selection",
        )

        assert state.require_user_confirmation is True
        assert state.confirmation_button_text == "Confirm Selection"
        assert state.user_confirmed is False

    def test_creation_with_required_widgets(self):
        """Test creation with pre-defined required widgets."""
        state = ItemExecutionState(
            item_id="item-3",
            item_index=2,
            required_widget_ids={"widget-a", "widget-b", "widget-c"},
        )

        assert state.required_widget_ids == {"widget-a", "widget-b", "widget-c"}
        assert len(state.pending_widget_ids) == 3


class TestItemExecutionStateCompletion:
    """Test completion detection logic."""

    def test_is_complete_no_requirements(self):
        """Item with no requirements should be complete."""
        state = ItemExecutionState(item_id="item-1", item_index=0)
        assert state.is_complete is True

    def test_is_complete_widgets_only_incomplete(self):
        """Item with unanswered required widgets is not complete."""
        state = ItemExecutionState(
            item_id="item-1",
            item_index=0,
            required_widget_ids={"widget-1", "widget-2"},
        )
        assert state.is_complete is False

    def test_is_complete_widgets_only_complete(self):
        """Item with all widgets answered is complete."""
        state = ItemExecutionState(
            item_id="item-1",
            item_index=0,
            required_widget_ids={"widget-1", "widget-2"},
            answered_widget_ids={"widget-1", "widget-2"},
        )
        assert state.is_complete is True

    def test_is_complete_with_confirmation_widgets_done_not_confirmed(self):
        """Widgets done but confirmation pending means not complete."""
        state = ItemExecutionState(
            item_id="item-1",
            item_index=0,
            required_widget_ids={"widget-1"},
            answered_widget_ids={"widget-1"},
            require_user_confirmation=True,
            user_confirmed=False,
        )
        assert state.is_complete is False

    def test_is_complete_with_confirmation_all_done(self):
        """Widgets done and confirmed means complete."""
        state = ItemExecutionState(
            item_id="item-1",
            item_index=0,
            required_widget_ids={"widget-1"},
            answered_widget_ids={"widget-1"},
            require_user_confirmation=True,
            user_confirmed=True,
        )
        assert state.is_complete is True

    def test_is_complete_confirmation_only_not_confirmed(self):
        """No widgets but confirmation required and not given."""
        state = ItemExecutionState(
            item_id="item-1",
            item_index=0,
            require_user_confirmation=True,
            user_confirmed=False,
        )
        assert state.is_complete is False

    def test_is_complete_confirmation_only_confirmed(self):
        """No widgets, confirmation required and given."""
        state = ItemExecutionState(
            item_id="item-1",
            item_index=0,
            require_user_confirmation=True,
            user_confirmed=True,
        )
        assert state.is_complete is True


class TestItemExecutionStatePendingWidgets:
    """Test pending widget calculation."""

    def test_pending_widget_ids_all_pending(self):
        """All required widgets are pending when none answered."""
        state = ItemExecutionState(
            item_id="item-1",
            item_index=0,
            required_widget_ids={"a", "b", "c"},
        )
        assert state.pending_widget_ids == {"a", "b", "c"}

    def test_pending_widget_ids_some_answered(self):
        """Only unanswered widgets are pending."""
        state = ItemExecutionState(
            item_id="item-1",
            item_index=0,
            required_widget_ids={"a", "b", "c"},
            answered_widget_ids={"a"},
        )
        assert state.pending_widget_ids == {"b", "c"}

    def test_pending_widget_ids_all_answered(self):
        """No pending widgets when all answered."""
        state = ItemExecutionState(
            item_id="item-1",
            item_index=0,
            required_widget_ids={"a", "b"},
            answered_widget_ids={"a", "b"},
        )
        assert state.pending_widget_ids == set()


class TestItemExecutionStateProgressCalculation:
    """Test completion percentage calculation."""

    def test_progress_no_requirements(self):
        """No requirements = 100% complete."""
        state = ItemExecutionState(item_id="item-1", item_index=0)
        assert state.completion_percentage == 100.0

    def test_progress_confirmation_only_not_done(self):
        """Confirmation only, not confirmed = 0%."""
        state = ItemExecutionState(
            item_id="item-1",
            item_index=0,
            require_user_confirmation=True,
        )
        assert state.completion_percentage == 0.0

    def test_progress_confirmation_only_done(self):
        """Confirmation only, confirmed = 100%."""
        state = ItemExecutionState(
            item_id="item-1",
            item_index=0,
            require_user_confirmation=True,
            user_confirmed=True,
        )
        assert state.completion_percentage == 100.0

    def test_progress_widgets_partial(self):
        """Half widgets answered = 50%."""
        state = ItemExecutionState(
            item_id="item-1",
            item_index=0,
            required_widget_ids={"a", "b"},
            answered_widget_ids={"a"},
        )
        assert state.completion_percentage == 50.0

    def test_progress_widgets_complete(self):
        """All widgets answered = 100%."""
        state = ItemExecutionState(
            item_id="item-1",
            item_index=0,
            required_widget_ids={"a", "b"},
            answered_widget_ids={"a", "b"},
        )
        assert state.completion_percentage == 100.0

    def test_progress_widgets_with_confirmation_widgets_done(self):
        """Widgets done, confirmation pending = 90%."""
        state = ItemExecutionState(
            item_id="item-1",
            item_index=0,
            required_widget_ids={"a", "b"},
            answered_widget_ids={"a", "b"},
            require_user_confirmation=True,
        )
        assert state.completion_percentage == 90.0

    def test_progress_widgets_with_confirmation_all_done(self):
        """Widgets + confirmation done = 100%."""
        state = ItemExecutionState(
            item_id="item-1",
            item_index=0,
            required_widget_ids={"a", "b"},
            answered_widget_ids={"a", "b"},
            require_user_confirmation=True,
            user_confirmed=True,
        )
        assert state.completion_percentage == 100.0


class TestItemExecutionStateMethods:
    """Test state mutation methods."""

    def test_record_response(self):
        """Test recording a widget response."""
        state = ItemExecutionState(
            item_id="item-1",
            item_index=0,
            required_widget_ids={"widget-1", "widget-2"},
        )

        state.record_response("widget-1", "user answer")

        assert state.widget_responses == {"widget-1": "user answer"}
        assert "widget-1" in state.answered_widget_ids
        assert "widget-2" in state.pending_widget_ids

    def test_record_response_multiple(self):
        """Test recording multiple responses."""
        state = ItemExecutionState(
            item_id="item-1",
            item_index=0,
            required_widget_ids={"w1", "w2", "w3"},
        )

        state.record_response("w1", 42)
        state.record_response("w2", ["a", "b", "c"])
        state.record_response("w3", {"nested": True})

        assert len(state.widget_responses) == 3
        assert state.widget_responses["w1"] == 42
        assert state.widget_responses["w2"] == ["a", "b", "c"]
        assert state.widget_responses["w3"] == {"nested": True}
        assert state.is_complete is True

    def test_confirm_sets_completed_at_when_complete(self):
        """Confirming when widgets done should set completed_at."""
        state = ItemExecutionState(
            item_id="item-1",
            item_index=0,
            required_widget_ids={"w1"},
            answered_widget_ids={"w1"},
            require_user_confirmation=True,
        )

        assert state.completed_at is None
        state.confirm()

        assert state.user_confirmed is True
        assert state.completed_at is not None
        assert state.is_complete is True

    def test_confirm_does_not_complete_without_widgets(self):
        """Confirming with pending widgets should not set completed_at."""
        state = ItemExecutionState(
            item_id="item-1",
            item_index=0,
            required_widget_ids={"w1", "w2"},
            answered_widget_ids={"w1"},
            require_user_confirmation=True,
        )

        state.confirm()

        assert state.user_confirmed is True
        assert state.completed_at is None
        assert state.is_complete is False

    def test_mark_complete(self):
        """Test explicit completion marking."""
        state = ItemExecutionState(item_id="item-1", item_index=0)

        assert state.completed_at is None
        state.mark_complete()

        assert state.completed_at is not None


class TestItemExecutionStateSerialization:
    """Test serialization and deserialization."""

    def test_to_dict_minimal(self):
        """Test serialization of minimal state."""
        state = ItemExecutionState(item_id="item-1", item_index=0)
        data = state.to_dict()

        assert data["item_id"] == "item-1"
        assert data["item_index"] == 0
        assert data["started_at"] is not None
        assert data["completed_at"] is None
        assert data["widget_responses"] == {}
        assert data["required_widget_ids"] == []
        assert data["answered_widget_ids"] == []
        assert data["require_user_confirmation"] is False
        assert data["confirmation_button_text"] == "Submit"
        assert data["user_confirmed"] is False

    def test_to_dict_full(self):
        """Test serialization of fully populated state."""
        now = datetime.now(UTC)
        state = ItemExecutionState(
            item_id="item-42",
            item_index=5,
            started_at=now,
            completed_at=now + timedelta(minutes=5),
            widget_responses={"w1": "answer1", "w2": 123},
            required_widget_ids={"w1", "w2"},
            answered_widget_ids={"w1", "w2"},
            require_user_confirmation=True,
            confirmation_button_text="Proceed",
            user_confirmed=True,
        )
        data = state.to_dict()

        assert data["item_id"] == "item-42"
        assert data["item_index"] == 5
        assert "w1" in data["required_widget_ids"]
        assert "w2" in data["required_widget_ids"]
        assert data["require_user_confirmation"] is True
        assert data["confirmation_button_text"] == "Proceed"
        assert data["user_confirmed"] is True

    def test_from_dict_minimal(self):
        """Test deserialization of minimal data."""
        data = {"item_id": "restored-item", "item_index": 3}
        state = ItemExecutionState.from_dict(data)

        assert state.item_id == "restored-item"
        assert state.item_index == 3
        assert state.completed_at is None
        assert state.require_user_confirmation is False

    def test_from_dict_full(self):
        """Test deserialization of fully populated data."""
        now = datetime.now(UTC)
        data = {
            "item_id": "full-item",
            "item_index": 7,
            "started_at": now.isoformat(),
            "completed_at": (now + timedelta(minutes=10)).isoformat(),
            "widget_responses": {"w1": "val1"},
            "required_widget_ids": ["w1", "w2"],
            "answered_widget_ids": ["w1"],
            "require_user_confirmation": True,
            "confirmation_button_text": "Confirm Now",
            "user_confirmed": False,
        }
        state = ItemExecutionState.from_dict(data)

        assert state.item_id == "full-item"
        assert state.item_index == 7
        assert state.completed_at is not None
        assert state.required_widget_ids == {"w1", "w2"}
        assert state.answered_widget_ids == {"w1"}
        assert state.require_user_confirmation is True
        assert state.confirmation_button_text == "Confirm Now"
        assert state.user_confirmed is False

    def test_round_trip_serialization(self):
        """Test that to_dict → from_dict preserves data."""
        original = ItemExecutionState(
            item_id="round-trip",
            item_index=99,
            required_widget_ids={"a", "b", "c"},
            answered_widget_ids={"a"},
            widget_responses={"a": {"complex": [1, 2, 3]}},
            require_user_confirmation=True,
            confirmation_button_text="Finish",
        )

        data = original.to_dict()
        restored = ItemExecutionState.from_dict(data)

        assert restored.item_id == original.item_id
        assert restored.item_index == original.item_index
        assert restored.required_widget_ids == original.required_widget_ids
        assert restored.answered_widget_ids == original.answered_widget_ids
        assert restored.widget_responses == original.widget_responses
        assert restored.require_user_confirmation == original.require_user_confirmation
        assert restored.confirmation_button_text == original.confirmation_button_text
