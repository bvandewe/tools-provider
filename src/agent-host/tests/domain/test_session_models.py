"""Unit tests for Session domain models and value objects."""

from datetime import UTC, datetime

import pytest

from domain.models.session_models import (
    ClientAction,
    ClientResponse,
    ControlMode,
    SessionConfig,
    SessionItem,
    SessionStatus,
    SessionType,
    UiState,
    ValidationStatus,
    get_control_mode_for_session_type,
    get_default_config_for_session_type,
)


class TestSessionTypeEnum:
    """Tests for SessionType enum."""

    def test_session_types_exist(self):
        """All expected session types should exist."""
        assert SessionType.THOUGHT == "thought"
        assert SessionType.LEARNING == "learning"
        assert SessionType.VALIDATION == "validation"
        assert SessionType.SURVEY == "survey"
        assert SessionType.WORKFLOW == "workflow"
        assert SessionType.APPROVAL == "approval"

    def test_session_type_values(self):
        """Session types should have correct string values."""
        assert SessionType.THOUGHT.value == "thought"
        assert SessionType.LEARNING.value == "learning"


class TestControlModeEnum:
    """Tests for ControlMode enum."""

    def test_control_modes_exist(self):
        """Both control modes should exist."""
        assert ControlMode.REACTIVE == "reactive"
        assert ControlMode.PROACTIVE == "proactive"


class TestSessionStatusEnum:
    """Tests for SessionStatus enum."""

    def test_all_statuses_exist(self):
        """All session statuses should exist."""
        assert SessionStatus.PENDING == "pending"
        assert SessionStatus.ACTIVE == "active"
        assert SessionStatus.AWAITING_CLIENT_ACTION == "awaiting_client_action"
        assert SessionStatus.COMPLETED == "completed"
        assert SessionStatus.EXPIRED == "expired"
        assert SessionStatus.TERMINATED == "terminated"


class TestValidationStatusEnum:
    """Tests for ValidationStatus enum."""

    def test_all_statuses_exist(self):
        """All validation statuses should exist."""
        assert ValidationStatus.VALID == "valid"
        assert ValidationStatus.INVALID == "invalid"
        assert ValidationStatus.SKIPPED == "skipped"


class TestSessionConfig:
    """Tests for SessionConfig value object."""

    def test_default_values(self):
        """Config should have sensible defaults."""
        config = SessionConfig()
        assert config.time_limit_seconds is None
        assert config.item_time_limit_seconds is None
        assert config.max_items is None
        assert config.allow_skip is False
        assert config.allow_back is False
        assert config.allow_concurrent_sessions is True

    def test_custom_values(self):
        """Config should accept custom values."""
        config = SessionConfig(
            time_limit_seconds=1800,
            max_items=20,
            allow_skip=True,
        )
        assert config.time_limit_seconds == 1800
        assert config.max_items == 20
        assert config.allow_skip is True

    def test_to_dict(self):
        """Config should serialize to dict."""
        config = SessionConfig(time_limit_seconds=600)
        data = config.to_dict()
        assert data["time_limit_seconds"] == 600
        assert data["allow_skip"] is False

    def test_from_dict(self):
        """Config should deserialize from dict."""
        data = {"time_limit_seconds": 900, "allow_back": True}
        config = SessionConfig.from_dict(data)
        assert config.time_limit_seconds == 900
        assert config.allow_back is True

    def test_immutable(self):
        """Config should be immutable (frozen dataclass)."""
        config = SessionConfig()
        with pytest.raises(Exception):  # FrozenInstanceError
            config.time_limit_seconds = 100


class TestClientAction:
    """Tests for ClientAction value object."""

    def test_creation(self):
        """ClientAction should be creatable with required fields."""
        action = ClientAction(
            tool_call_id="call_123",
            tool_name="present_choices",
            widget_type="multiple_choice",
            props={"question": "What is 2+2?", "options": ["3", "4", "5"]},
        )
        assert action.tool_call_id == "call_123"
        assert action.tool_name == "present_choices"
        assert action.widget_type == "multiple_choice"
        assert action.lock_input is True  # Default

    def test_to_sse_payload(self):
        """ClientAction should convert to SSE payload format."""
        action = ClientAction(
            tool_call_id="call_123",
            tool_name="present_choices",
            widget_type="multiple_choice",
            props={"question": "Test?"},
            lock_input=False,
        )
        payload = action.to_sse_payload()
        assert payload["tool_call_id"] == "call_123"
        assert payload["component"] == "multiple_choice"
        assert payload["props"]["question"] == "Test?"
        assert payload["lock_input"] is False

    def test_to_dict_and_from_dict(self):
        """ClientAction should round-trip through dict."""
        original = ClientAction(
            tool_call_id="call_456",
            tool_name="request_free_text",
            widget_type="free_text",
            props={"prompt": "Enter your answer"},
            lock_input=False,
        )
        data = original.to_dict()
        restored = ClientAction.from_dict(data)
        assert restored.tool_call_id == original.tool_call_id
        assert restored.tool_name == original.tool_name
        assert restored.widget_type == original.widget_type
        assert restored.lock_input == original.lock_input


class TestClientResponse:
    """Tests for ClientResponse value object."""

    def test_creation(self):
        """ClientResponse should be creatable with required fields."""
        now = datetime.now(UTC)
        response = ClientResponse(
            tool_call_id="call_123",
            response={"selection": "4", "index": 1},
            timestamp=now,
        )
        assert response.tool_call_id == "call_123"
        assert response.response["selection"] == "4"
        assert response.validation_status == ValidationStatus.VALID

    def test_invalid_response(self):
        """ClientResponse should support invalid status."""
        response = ClientResponse(
            tool_call_id="call_123",
            response=None,
            timestamp=datetime.now(UTC),
            validation_status=ValidationStatus.INVALID,
            validation_errors=["Selection required"],
        )
        assert response.validation_status == ValidationStatus.INVALID
        assert "Selection required" in response.validation_errors

    def test_to_dict_and_from_dict(self):
        """ClientResponse should round-trip through dict."""
        now = datetime.now(UTC)
        original = ClientResponse(
            tool_call_id="call_789",
            response="Test answer",
            timestamp=now,
        )
        data = original.to_dict()
        restored = ClientResponse.from_dict(data)
        assert restored.tool_call_id == original.tool_call_id
        assert restored.response == original.response


class TestSessionItem:
    """Tests for SessionItem value object."""

    def test_create_factory(self):
        """SessionItem.create should generate ID and timestamp."""
        item = SessionItem.create(
            sequence=1,
            agent_prompt="What is the capital of France?",
        )
        assert item.id is not None
        assert len(item.id) == 36  # UUID format
        assert item.sequence == 1
        assert item.agent_prompt == "What is the capital of France?"
        assert item.started_at is not None
        assert item.completed_at is None

    def test_complete(self):
        """SessionItem.complete should set response and times."""
        item = SessionItem.create(sequence=1, agent_prompt="Test")
        response = ClientResponse(
            tool_call_id="call_123",
            response="Answer",
            timestamp=datetime.now(UTC),
        )
        item.complete(response, evaluation={"correct": True})

        assert item.completed_at is not None
        assert item.user_response == response
        assert item.response_time_ms is not None
        assert item.response_time_ms >= 0
        assert item.evaluation["correct"] is True

    def test_to_dict_and_from_dict(self):
        """SessionItem should round-trip through dict."""
        item = SessionItem.create(
            sequence=2,
            agent_prompt="Test prompt",
            client_action=ClientAction(
                tool_call_id="call_abc",
                tool_name="present_choices",
                widget_type="multiple_choice",
                props={},
            ),
        )
        data = item.to_dict()
        restored = SessionItem.from_dict(data)
        assert restored.id == item.id
        assert restored.sequence == item.sequence
        assert restored.client_action.tool_call_id == "call_abc"


class TestUiState:
    """Tests for UiState value object."""

    def test_default_values(self):
        """UiState should have sensible defaults."""
        state = UiState()
        assert state.chat_input_locked is False
        assert state.active_widget is None
        assert state.widget_partial_state is None

    def test_with_active_widget(self):
        """UiState should support active widget."""
        widget = ClientAction(
            tool_call_id="call_123",
            tool_name="present_choices",
            widget_type="multiple_choice",
            props={},
        )
        state = UiState(chat_input_locked=True, active_widget=widget)
        assert state.chat_input_locked is True
        assert state.active_widget is not None

    def test_to_dict_and_from_dict(self):
        """UiState should round-trip through dict."""
        widget = ClientAction(
            tool_call_id="call_123",
            tool_name="test",
            widget_type="test",
            props={},
        )
        original = UiState(
            chat_input_locked=True,
            active_widget=widget,
            widget_partial_state={"partial": "data"},
        )
        data = original.to_dict()
        restored = UiState.from_dict(data)
        assert restored.chat_input_locked is True
        assert restored.active_widget.tool_call_id == "call_123"
        assert restored.widget_partial_state["partial"] == "data"


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_control_mode_for_session_type(self):
        """THOUGHT should be reactive, others proactive."""
        assert get_control_mode_for_session_type(SessionType.THOUGHT) == ControlMode.REACTIVE
        assert get_control_mode_for_session_type(SessionType.LEARNING) == ControlMode.PROACTIVE
        assert get_control_mode_for_session_type(SessionType.VALIDATION) == ControlMode.PROACTIVE
        assert get_control_mode_for_session_type(SessionType.SURVEY) == ControlMode.PROACTIVE

    def test_get_default_config_for_validation(self):
        """VALIDATION should have strict config."""
        config = get_default_config_for_session_type(SessionType.VALIDATION)
        assert config.time_limit_seconds == 1800
        assert config.allow_skip is False
        assert config.allow_back is False
        assert config.allow_concurrent_sessions is False

    def test_get_default_config_for_thought(self):
        """THOUGHT should have relaxed config."""
        config = get_default_config_for_session_type(SessionType.THOUGHT)
        assert config.time_limit_seconds is None
        assert config.allow_skip is True
        assert config.allow_back is True
